"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.

data/fit_text.py  –  plotviz
The text of a fit as it goes on the chart (an annotation): a title, the equation, the
parameters with their errors and a few numbers of goodness of fit. Pure: no Qt, no drawing.
"""
from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from data.scientific import CUSTOM_PREFIX, LOWESS_PREFIX, POLYNOMIAL_PREFIX, CurveFitter, normalize_expression


@dataclass
class FitTextOptions:
    """What the label of a fit shows."""
    name: bool = True            # a title line: "Quadratic fit: series"
    equation: bool = True        # y = ...
    parameters: bool = False     # one line per parameter, with its error
    r2: bool = True
    rmse: bool = False
    aic: bool = False
    n: bool = False              # the number of points fitted
    latex: bool = True           # the equation as math text ($...$), not as plain characters


def format_value_error(value: float, error: float | None) -> str:
    """'0.2134 ± 0.0087': the error to two significant digits and the value to the same
    decimals, as in a paper. Without a usable error, four significant digits of the value."""
    if error is None or not math.isfinite(error) or error <= 0 or not math.isfinite(value):
        return f'{value:.4g}'
    decimals = 1 - math.floor(math.log10(error))             # two significant digits of the error
    if decimals > 8 or abs(value) >= 1e7 or (value != 0 and abs(value) < 1e-4):
        return f'{value:.4g} ± {error:.2g}'                   # too large or too small to write out
    if decimals <= 0:
        return f'{round(value, decimals):.0f} ± {round(error, decimals):.0f}'
    return f'{value:.{decimals}f} ± {error:.{decimals}f}'


def parameter_label(name: str) -> str:
    """'b (rate)' -> 'b': the short name of a parameter."""
    return name.split(' (')[0].strip()


def model_title(model: str) -> str:
    if model.startswith(CUSTOM_PREFIX):
        return 'Custom model'
    if model.startswith(LOWESS_PREFIX):
        return 'LOWESS'
    return model


def _symbolic_equation(model: str, names: list[str], x0: float) -> str | None:
    """The equation with the parameter names instead of numbers ('y = a·x² + b·x + c'), or
    None when the model has no equation (LOWESS)."""
    try:
        spec = CurveFitter.spec(model)
    except ValueError:
        return None
    if not spec.template or not names:
        return None
    equation = re.sub(r'\{(\d+):[^}]*\}', lambda m: names[int(m.group(1))] if int(m.group(1)) < len(names) else '?',
                      spec.template)
    if x0:
        equation = (re.sub(r'\bx\b', '(x−x₀)', equation) if spec.custom else equation.replace('x', '(x−x₀)'))
    return equation


# ── The equation in LaTeX ($...$, which matplotlib draws as math text) ──────────────────

# Each model as the Python expression it computes: one converter then serves them all,
# and the custom models too.
_MODEL_EXPRESSIONS = {
    'Linear': 'a*x + b',
    'Quadratic': 'a*x**2 + b*x + c',
    'Cubic': 'a*x**3 + b*x**2 + c*x + d',
    'Exponential': 'a*exp(b*x)',
    'Exponential + offset': 'a*exp(b*x) + c',
    'Power Law': 'a*x**b',
    'Logarithmic': 'a*log(x) + b',
    'Sigmoid': 'a/(1 + exp(-(x - b)/c))',
    'Gaussian': 'a*exp(-(x - mu)**2/(2*sigma**2)) + c',
    'Sinusoid': 'a*sin(2*pi*f*x + phi) + c',
}
_GREEK = {name: '\\' + name for name in (
    'alpha', 'beta', 'gamma', 'delta', 'epsilon', 'theta', 'lambda', 'mu', 'nu', 'rho', 'sigma', 'tau', 'omega',
    'kappa', 'eta', 'zeta', 'xi')}
_GREEK.update({'phi': '\\varphi', 'pi': '\\pi', 'Delta': '\\Delta', 'Omega': '\\Omega', 'Sigma': '\\Sigma'})
_PLAIN_CALLS = {'sin': '\\sin', 'cos': '\\cos', 'tan': '\\tan', 'sinh': '\\sinh', 'cosh': '\\cosh',
                'tanh': '\\tanh', 'arcsin': '\\arcsin', 'arccos': '\\arccos', 'arctan': '\\arctan',
                'log': '\\ln', 'log10': '\\log_{10}', 'log2': '\\log_{2}'}
_ATOM, _POWER, _UNARY, _PRODUCT, _SUM = 5, 4, 3, 2, 1             # how tightly a piece binds


def _latex_number(value: float) -> str:
    """A number as it is written in a paper: 4 significant digits, 1.2\\times10^{-5} for e-notation."""
    text = f'{abs(value):.4g}'
    if 'e' in text:
        mantissa, exponent = text.split('e')
        text = f'{mantissa}\\times10^{{{int(exponent)}}}'
    return ('-' if value < 0 else '') + text


def _latex_name(name: str) -> str:
    """A parameter name: greek words become symbols, a trailing number a subscript (c2 -> c_{2})."""
    if name in _GREEK:
        return _GREEK[name]
    match = re.fullmatch(r'([A-Za-z]+)(\d+)', name)
    return f'{match.group(1)}_{{{match.group(2)}}}' if match else name


def _latex_of(node: ast.AST, values: Mapping[str, float] | None, shift: bool) -> tuple[str, int]:
    """(LaTeX, how tightly it binds) for a node of a model expression. *values* gives the
    parameters their numbers (None: their names); *shift* writes x as (x - x_0)."""
    def wrap(piece: tuple[str, int], at_least: int) -> str:
        text, level = piece
        return text if level >= at_least else f'\\left({text}\\right)'

    if isinstance(node, ast.Expression):
        return _latex_of(node.body, values, shift)
    if isinstance(node, ast.Constant):
        raw = node.value
        number = float(raw) if isinstance(raw, (int, float)) else 0.0
        text = str(int(number)) if number == int(number) and abs(number) < 1e9 else _latex_number(number)
        return text, _ATOM
    if isinstance(node, ast.Name):
        if node.id == 'x':
            return ('\\left(x - x_{0}\\right)' if shift else 'x'), _ATOM
        if node.id == 'e':
            return 'e', _ATOM
        if values is not None and node.id in values:
            text = _latex_number(values[node.id])
            return text, _UNARY if text.startswith('-') else _ATOM
        return _latex_name(node.id), _ATOM
    if isinstance(node, ast.UnaryOp):
        inner = _latex_of(node.operand, values, shift)
        if isinstance(node.op, ast.USub):
            text = inner[0][1:] if inner[0].startswith('-') else '-' + wrap(inner, _PRODUCT + 1)
            return text, _UNARY
        return inner
    if isinstance(node, ast.BinOp):
        left = _latex_of(node.left, values, shift)
        right = _latex_of(node.right, values, shift)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            minus = isinstance(node.op, ast.Sub)
            if right[0].startswith('-'):                       # a - -b  ->  a + b,  a + -b  ->  a - b
                minus, tail = not minus, right[0][1:]
            else:
                tail = wrap(right, _PRODUCT) if minus else right[0]
            return f'{left[0]} {"-" if minus else "+"} {tail}', _SUM
        if isinstance(node.op, ast.Mult):
            second = wrap(right, _PRODUCT + 1) if not right[0].startswith('-') else f'\\left({right[0]}\\right)'
            join = '\\cdot ' if second[:1].isdigit() else '\\,'      # 2·1.1², not "2 1.1²"
            return f'{wrap(left, _PRODUCT)}{join}{second}', _PRODUCT
        if isinstance(node.op, ast.Div):
            if isinstance(node.left, ast.UnaryOp) and isinstance(node.left.op, ast.USub):
                top = _latex_of(node.left.operand, values, shift)[0]       # -(x - b)/c  ->  -\\frac{x - b}{c}
                return f'-\\frac{{{top}}}{{{right[0]}}}', _UNARY
            return f'\\frac{{{left[0]}}}{{{right[0]}}}', _ATOM
        if isinstance(node.op, ast.Pow):
            base = wrap(left, _ATOM) if left[1] < _ATOM else left[0]
            return f'{base}^{{{right[0]}}}', _POWER
        if isinstance(node.op, ast.Mod):
            return f'{wrap(left, _PRODUCT)}\\ \\mathrm{{mod}}\\ {wrap(right, _PRODUCT + 1)}', _PRODUCT
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name, args = node.func.id, [_latex_of(a, values, shift) for a in node.args]
        first = args[0][0] if args else ''
        if name in _PLAIN_CALLS:
            simple = isinstance(node.args[0], (ast.Name, ast.Constant)) and args[0][1] == _ATOM
            return (f'{_PLAIN_CALLS[name]} {first}' if simple else f'{_PLAIN_CALLS[name]}\\left({first}\\right)'), _ATOM
        if name == 'exp':
            return f'e^{{{first}}}', _POWER
        if name == 'expm1':
            return f'\\left(e^{{{first}}} - 1\\right)', _ATOM
        if name == 'log1p':
            return f'\\ln\\left(1 + {first}\\right)', _ATOM
        if name == 'sqrt':
            return f'\\sqrt{{{first}}}', _ATOM
        if name == 'cbrt':
            return f'\\sqrt[3]{{{first}}}', _ATOM
        if name == 'abs':
            return f'\\left|{first}\\right|', _ATOM
        if name in ('minimum', 'maximum', 'arctan2', 'sign'):
            word = {'minimum': '\\min', 'maximum': '\\max', 'arctan2': '\\mathrm{arctan2}', 'sign': '\\mathrm{sign}'}[name]
            return f'{word}\\left({", ".join(a[0] for a in args)}\\right)', _ATOM
    raise ValueError('cannot write this expression in LaTeX')


def model_expression(model: str, names: list[str]) -> str | None:
    """The Python expression of *model* with the parameters called *names* (None: no equation)."""
    if model.startswith(LOWESS_PREFIX):
        return None
    if model.startswith(CUSTOM_PREFIX):
        return normalize_expression(model[len(CUSTOM_PREFIX):])
    if model.startswith(POLYNOMIAL_PREFIX):
        degree = len(names) - 1
        return ' + '.join(f'{name}*x**{degree - i}' if degree - i > 1 else (f'{name}*x' if degree - i == 1 else name)
                          for i, name in enumerate(names))
    return _MODEL_EXPRESSIONS.get(model)


def equation_latex(fit: Mapping[str, Any], symbolic: bool = False) -> str | None:
    """The fit's equation as LaTeX between dollar signs, ready for a paper or for matplotlib's
    math text: ``$y = 0.383\\,x^{2} - 2.31\\,x + 5.39$``. With *symbolic* the parameters keep their
    names (``$y = a\\,x^{2} + b\\,x + c$``). Returns None when the model has no equation (LOWESS).
    A shifted x (far from zero) is written ``(x - x_{0})``; the value of x0 is in the fit."""
    model = str(fit.get('model', ''))
    stats: Mapping[str, Any] = fit.get('stats') or {}
    if model.startswith(POLYNOMIAL_PREFIX) or model.startswith(CUSTOM_PREFIX):
        names = [str(n) for n in stats.get('param_names', [])] or _names_from_model(model)
    else:
        names = [parameter_label(n) for n in stats.get('param_names', [])] or list(
            CurveFitter.PARAM_NAMES.get(model, []))
        names = [{'μ': 'mu', 'σ': 'sigma', 'φ': 'phi'}.get(n, n) for n in names]
    expression = model_expression(model, names)
    if expression is None:
        return None
    values = None if symbolic else dict(zip(names, (float(v) for v in stats.get('param_values', []))))
    if values is not None and len(values) != len(names):
        return None
    try:
        body, _ = _latex_of(ast.parse(expression, mode='eval'), values, bool(fit.get('x0')))
    except (SyntaxError, ValueError):
        return None
    return f'$y = {body}$'


def _names_from_model(model: str) -> list[str]:
    """The parameters of a model that is written as text, in order of appearance."""
    if model.startswith(CUSTOM_PREFIX):
        return list(CurveFitter.spec(model).param_names)
    return list(CurveFitter.spec(model).param_names)


def fit_annotation_text(fit: Mapping[str, Any], options: FitTextOptions | None = None) -> str:
    """The lines of the label of *fit* (an entry of the fits of the window), as one string."""
    opt = options or FitTextOptions()
    model = str(fit.get('model', ''))
    stats: Mapping[str, Any] = fit.get('stats') or {}
    x0 = float(fit.get('x0') or 0.0)
    lowess = model.startswith(LOWESS_PREFIX)
    names = [parameter_label(n) for n in stats.get('param_names', [])]
    values = list(stats.get('param_values', []))
    errors = list(stats.get('param_se', []))
    lines: list[str] = []

    if opt.name:
        lines.append(f'{model_title(model)} fit: {fit.get("lbl", "")}{fit.get("tag", "")}')

    show_parameters = opt.parameters and bool(values) and not lowess
    if opt.equation:
        typeset = equation_latex(fit, symbolic=show_parameters) if opt.latex and not lowess else None
        if lowess:
            lines.append(str(fit.get('eq_str', 'LOWESS smoothing')))
        elif typeset:
            lines.append(typeset)
        elif show_parameters:
            symbolic = _symbolic_equation(model, names, x0)
            lines.append(symbolic or str(fit.get('eq_str', '')))   # the numbers follow below
        else:
            lines.append(str(fit.get('eq_str', '')))
    if show_parameters:
        for name, value, error in zip(names, values, errors):
            written = format_value_error(float(value), float(error))
            if opt.latex:                                      # a = 0.383 ± 0.014, typeset like the equation
                written = re.sub(r'(\d)e([+-]?\d+)', lambda m: f'{m.group(1)}\\times10^{{{int(m.group(2))}}}', written)
                symbol = {'μ': '\\mu', 'σ': '\\sigma', 'φ': '\\varphi'}.get(name) or _latex_name(name)
                written = written.replace(' ± ', ' \\pm ')       # (no backslash inside an f-string: Python 3.10)
                lines.append(f'${symbol} = {written}$')
            else:
                lines.append(f'{name} = {written}'.replace('-', '−'))
    if x0 and not lowess and (opt.equation or show_parameters):
        lines.append(f'$x_{{0}} = {x0:.6g}$' if opt.latex and opt.equation else f'x₀ = {x0:.6g}')

    r2 = fit.get('r2', stats.get('r2'))
    if opt.r2 and r2 is not None:
        lines.append(f'R² = {float(r2):.4g}')
    if opt.rmse and 'rmse' in stats:
        lines.append(f'RMSE = {float(stats["rmse"]):.4g}')
    if opt.aic and 'aic' in stats and math.isfinite(float(stats['aic'])):
        lines.append(f'AIC = {float(stats["aic"]):.4g}')
    if opt.n and 'n' in stats:
        lines.append(f'n = {int(stats["n"])}')
    return '\n'.join(lines)
