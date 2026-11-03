"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.


data/scientific.py - Curve fitting and statistical analysis
"""
import ast
import re
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import optimize, stats as scipy_stats


# ── Models given as text: "Polynomial deg N" and "Custom: <expression>" ─────────

_SUPERSCRIPT = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
POLYNOMIAL_PREFIX = 'Polynomial deg '
CUSTOM_PREFIX = 'Custom: '
MAX_DEGREE = 10
LOWESS_PREFIX = 'LOWESS span '
LOWESS_CHOICE = 'Smoothing (LOWESS)'
POLYNOMIAL_CHOICE = 'Polynomial (degree n)'      # the entries of the model list that need options
CUSTOM_CHOICE = 'Custom expression'

# What a custom expression may use: x, the parameters (any other name), numbers and these.
_EXPR_FUNCTIONS = {
    'sin': np.sin, 'cos': np.cos, 'tan': np.tan, 'arcsin': np.arcsin, 'arccos': np.arccos,
    'arctan': np.arctan, 'arctan2': np.arctan2, 'sinh': np.sinh, 'cosh': np.cosh, 'tanh': np.tanh,
    'exp': np.exp, 'expm1': np.expm1, 'log': np.log, 'log10': np.log10, 'log2': np.log2,
    'log1p': np.log1p, 'sqrt': np.sqrt, 'cbrt': np.cbrt, 'abs': np.abs, 'sign': np.sign,
    'minimum': np.minimum, 'maximum': np.maximum,
}
_EXPR_CONSTANTS = {'pi': np.pi, 'e': np.e}
_ALLOWED_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Constant, ast.Load,
                  ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd)


class _IntsToFloats(ast.NodeTransformer):
    """10**10**10 with integers would never finish; with floats it overflows at once."""
    def visit_Constant(self, node):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return ast.copy_location(ast.Constant(float(node.value)), node)
        return node


def normalize_expression(expr):
    return ' '.join(str(expr).split())


def parse_expression(expr):
    """Check a custom model expression and return (compiled code, parameter names in order of
    appearance).  Raises ValueError with a message for anything that is not a plain formula."""
    expr = normalize_expression(expr)
    if not expr:
        raise ValueError('the expression is empty')
    if len(expr) > 300:
        raise ValueError('the expression is too long (300 characters at most)')
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as err:
        raise ValueError(f'the expression is not valid: {err.msg}') from None
    params = []
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f'"{type(node).__name__}" is not allowed in a model '
                             '(numbers, x, parameters, + - * / ** % and functions only)')
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _EXPR_FUNCTIONS or node.keywords:
                raise ValueError('only these functions can be called: ' + ', '.join(_EXPR_FUNCTIONS))
        if isinstance(node, ast.Constant) and not isinstance(node.value, (int, float)):
            raise ValueError('only numbers are allowed as constants')
    for node in sorted((n for n in ast.walk(tree) if isinstance(n, ast.Name)),
                       key=lambda n: (n.lineno, n.col_offset)):
        name = node.id
        if name == 'x' or name in _EXPR_CONSTANTS or name in _EXPR_FUNCTIONS:
            continue
        if name not in params:
            params.append(name)
    if not params:
        raise ValueError('the expression has no parameter to fit (use letters other than x, '
                         'for example a*exp(-x/b) + c)')
    tree = ast.fix_missing_locations(_IntsToFloats().visit(tree))
    return compile(tree, '<model>', 'eval'), params


def _expression_function(expr):
    code, params = parse_expression(expr)

    def func(x, *p):
        env: dict[str, Any] = {**_EXPR_FUNCTIONS, **_EXPR_CONSTANTS}
        env.update(zip(params, p))
        env['x'] = np.asarray(x, dtype=float)
        with np.errstate(all='ignore'):
            out = eval(code, {'__builtins__': {}}, env)       # noqa: S307 - checked by parse_expression
        return out + np.zeros_like(env['x'])                  # a constant expression: one value per x
    return func, params


def parse_start_values(text):
    """'a=1, b=0.5' -> {'a': 1.0, 'b': 0.5} (empty text: no start values)."""
    out = {}
    for part in re.split(r'[,;\s]+', re.sub(r'\s*=\s*', '=', text.strip())):
        if not part:
            continue
        name, sep, value = part.partition('=')
        try:
            if not sep or not name.isidentifier():
                raise ValueError
            out[name] = float(value)
        except ValueError:
            raise ValueError(f'start values are written like  a=1, b=0.5  (not "{part}")') from None
    return out


def _superscript(n):
    return str(n).translate(_SUPERSCRIPT)


@dataclass
class ModelSpec:
    """Everything the fitter needs to know about one model."""
    name: str
    func: Callable
    param_names: list
    template: str                     # 'y = {0:.4g}·x + {1:.4g}'
    f_test: bool = False              # an intercept-only model is nested in it
    shifts_x: bool = True             # fitted on x - x0 when x is far from 0
    custom: bool = False


class CurveFitter:
    MODELS = {
        'Linear':      lambda x, a, b: a * x + b,
        'Quadratic':   lambda x, a, b, c: a * x**2 + b * x + c,
        'Cubic':       lambda x, a, b, c, d: a * x**3 + b * x**2 + c * x + d,
        'Exponential': lambda x, a, b: a * np.exp(b * x),
        'Exponential + offset': lambda x, a, b, c: a * np.exp(b * x) + c,
        'Power Law':   lambda x, a, b: a * x**b,
        'Logarithmic': lambda x, a, b: a * np.log(x) + b,
        'Sigmoid':     lambda x, a, b, c: a / (1 + np.exp(-(x - b) / c)),
        'Gaussian':    lambda x, a, mu, s, c: a * np.exp(-(x - mu)**2 / (2 * s**2)) + c,
        'Sinusoid':    lambda x, a, f, phi, c: a * np.sin(2 * np.pi * f * x + phi) + c,
    }

    PARAM_NAMES = {
        'Linear':      ['a', 'b'],
        'Quadratic':   ['a', 'b', 'c'],
        'Cubic':       ['a', 'b', 'c', 'd'],
        'Exponential': ['a', 'b'],
        'Exponential + offset': ['a', 'b (rate)', 'c (offset)'],
        'Power Law':   ['a', 'b'],
        'Logarithmic': ['a', 'b'],
        'Sigmoid':     ['a', 'b (midpoint)', 'c (scale)'],
        'Gaussian':    ['a (amplitude)', 'μ (centre)', 'σ (width)', 'c (offset)'],
        'Sinusoid':    ['a (amplitude)', 'f (frequency)', 'φ (phase, rad)', 'c (offset)'],
    }

    # Human-readable equation templates (use popt values)
    EQ_TEMPLATES = {
        'Linear':      'y = {0:.4g}·x + {1:.4g}',
        'Quadratic':   'y = {0:.4g}·x² + {1:.4g}·x + {2:.4g}',
        'Cubic':       'y = {0:.4g}·x³ + {1:.4g}·x² + {2:.4g}·x + {3:.4g}',
        'Exponential': 'y = {0:.4g}·e^({1:.4g}·x)',
        'Exponential + offset': 'y = {0:.4g}·e^({1:.4g}·x) + {2:.4g}',
        'Power Law':   'y = {0:.4g}·x^{1:.4g}',
        'Logarithmic': 'y = {0:.4g}·ln(x) + {1:.4g}',
        'Sigmoid':     'y = {0:.4g} / (1 + e^(-(x−{1:.4g})/{2:.4g}))',
        'Gaussian':    'y = {0:.4g}·e^(−(x−{1:.4g})²/(2·{2:.4g}²)) + {3:.4g}',
        'Sinusoid':    'y = {0:.4g}·sin(2π·{1:.4g}·x + {2:.4g}) + {3:.4g}',
    }

    # Models that are linear in their parameters and have an intercept: an intercept-only
    # model is nested in them, so the overall F-test is meaningful.
    F_TEST_MODELS = ('Linear', 'Quadratic', 'Cubic', 'Logarithmic')   # plus every Polynomial deg N

    # ── Data preparation ─────────────────────────────────────────────────────

    @staticmethod
    def clean(x, y):
        """Float arrays without the points where x or y is NaN/inf.  Returns (x, y, n_dropped)."""
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if x.shape != y.shape:
            raise ValueError(f'x has {x.size} points but y has {y.size}')
        ok = np.isfinite(x) & np.isfinite(y)
        return x[ok], y[ok], int((~ok).sum())

    # ── Model resolution: a model is a name; two kinds are made from text ───────────

    @staticmethod
    def polynomial_key(degree):
        return f'{POLYNOMIAL_PREFIX}{int(degree)}'

    @staticmethod
    def custom_key(expression):
        return CUSTOM_PREFIX + normalize_expression(expression)

    @staticmethod
    def spec(model):
        """The ModelSpec of *model*: a name from MODELS, 'Polynomial deg N' or 'Custom: <expr>'.
        Raises ValueError if it is none of them or the expression is not valid."""
        if model.startswith(POLYNOMIAL_PREFIX):
            try:
                n = int(model[len(POLYNOMIAL_PREFIX):])
            except ValueError:
                raise ValueError(f'unknown model: {model}') from None
            if not 1 <= n <= MAX_DEGREE:
                raise ValueError(f'the polynomial degree must be between 1 and {MAX_DEGREE}')
            powers = range(n, -1, -1)
            terms = []
            for i, k in enumerate(powers):
                term = '{%d:.4g}' % i
                if k >= 2:
                    term += '·x' + _superscript(k)
                elif k == 1:
                    term += '·x'
                terms.append(term)
            return ModelSpec(model, lambda x, *p: np.polyval(p, x), [f'c{k}' for k in powers],
                             'y = ' + ' + '.join(terms), f_test=True)
        if model.startswith(LOWESS_PREFIX):
            return ModelSpec(model, lambda x, *p: np.full(np.shape(x), np.nan), [], '', shifts_x=False)
        if model.startswith(CUSTOM_PREFIX):
            expr = normalize_expression(model[len(CUSTOM_PREFIX):])
            func, params = _expression_function(expr)
            template = expr
            for i, name in enumerate(params):
                template = re.sub(rf'\b{re.escape(name)}\b', '{%d:.4g}' % i, template)
            return ModelSpec(model, func, params, 'y = ' + template, custom=True)
        if model in CurveFitter.MODELS:
            return ModelSpec(
                model, CurveFitter.MODELS[model],
                list(CurveFitter.PARAM_NAMES.get(model, [])),
                CurveFitter.EQ_TEMPLATES.get(model, 'y = f(x)'),
                f_test=model in CurveFitter.F_TEST_MODELS,
                shifts_x=model not in ('Logarithmic', 'Power Law'))
        raise ValueError(f'unknown model: {model}')

    @staticmethod
    def x_shift(model, x):
        """The x value the fit is measured from.  Far from zero (years, dates) the models are
        badly conditioned or overflow (e^(b·19800)), so the fit works on x - x0 instead.
        Logarithmic and Power Law keep the real x: their domain is x > 0."""
        if len(x) == 0 or not CurveFitter.spec(model).shifts_x:
            return 0.0
        span = float(np.ptp(x))
        centre = float(np.mean(x))
        return centre if span > 0 and abs(centre) > 5 * span else 0.0

    @staticmethod
    def make_func(model, x0=0.0):
        """The model function; with a shift x0 it takes the original x and uses x - x0."""
        base = CurveFitter.spec(model).func
        if not x0:
            return base
        return lambda x, *p: base(np.asarray(x, dtype=float) - x0, *p)

    @staticmethod
    def has_f_test(model):
        try:
            return CurveFitter.spec(model).f_test
        except ValueError:
            return False

    @staticmethod
    def param_names(model, n_params):
        try:
            names = CurveFitter.spec(model).param_names
        except ValueError:
            names = []
        return names if len(names) == n_params else [f'p{i}' for i in range(n_params)]

    @staticmethod
    def _check_domain(model, x, y):
        if model in ('Logarithmic', 'Power Law') and np.any(x <= 0):
            raise ValueError(f'{model} needs every x to be greater than 0 (found x <= 0)')

    # ── Starting values ─────────────────────────────────────────────────────────

    @staticmethod
    def _offset_exponential_guesses(xs, ys):
        """a·e^(b·x) + c: for each plausible offset c (the tail, the head, just under the minimum,
        just over the maximum) a straight-line fit of ln|y - c| gives a and b."""
        span = float(np.ptp(ys)) or 1.0
        k = max(3, len(ys) // 10)
        guesses = []
        for c0 in (float(np.mean(ys[-k:])), float(np.mean(ys[:k])),
                   float(ys.min() - 0.05 * span), float(ys.max() + 0.05 * span)):
            d = ys - c0
            sign = 1.0 if np.median(d) >= 0 else -1.0
            use = sign * d > 0
            if use.sum() >= 3 and np.ptp(xs[use]) > 0:
                slope, intercept = np.polyfit(xs[use], np.log(sign * d[use]), 1)
                guesses.append([sign * float(np.exp(intercept)), float(slope), c0])
        return guesses or [[span, -1.0 / (float(np.ptp(xs)) or 1.0), float(np.mean(ys))]]

    @staticmethod
    def _gaussian_guesses(xs, ys):
        """a·e^(−(x−μ)²/2σ²) + c: the offset from the lower decile, the peak (or the dip) from the
        point farthest from it, the width from where the curve is above half its height."""
        span = float(xs[-1] - xs[0]) or 1.0
        guesses = []
        for c0 in (float(np.percentile(ys, 10)), float(np.median(ys)), 0.0):
            d = ys - c0
            i = int(np.argmax(np.abs(d)))
            a0 = float(d[i])
            if a0 == 0:
                continue
            above = xs[np.abs(d) >= abs(a0) / 2]
            fwhm = float(above.max() - above.min()) if len(above) > 1 else span / 5
            sigma = max(fwhm / 2.355, span / 200)
            guesses.append([a0, float(xs[i]), sigma, c0])
        return guesses or [[1.0, float(xs.mean()), span / 10, 0.0]]

    @staticmethod
    def _sinusoid_guesses(xs, ys):
        """a·sin(2π·f·x + φ) + c: the strongest frequencies of the spectrum of the (uniformly
        resampled) data; for each, amplitude, phase and offset by linear least squares."""
        n = len(xs)
        span = float(xs[-1] - xs[0]) or 1.0
        grid = np.linspace(xs[0], xs[-1], max(n, 64))
        resampled = np.interp(grid, xs, ys)
        spectrum = np.abs(np.fft.rfft(resampled - resampled.mean()))
        freqs = np.fft.rfftfreq(len(grid), grid[1] - grid[0])
        order = [i for i in np.argsort(spectrum)[::-1] if freqs[i] > 0][:3]
        guesses = []
        for i in order or [1]:
            f0 = float(freqs[i]) if i < len(freqs) else 1.0 / span
            design = np.column_stack([np.sin(2 * np.pi * f0 * xs), np.cos(2 * np.pi * f0 * xs),
                                      np.ones(n)])
            (s_, c_, off), *_ = np.linalg.lstsq(design, ys, rcond=None)
            guesses.append([float(np.hypot(s_, c_)), f0, float(np.arctan2(c_, s_)), float(off)])
        return guesses

    @staticmethod
    def _initial_guesses(model, x, y, start=None):
        """Starting values taken from the data (x is already shifted).  The old fixed ones
        ([1, 0.1] for the exponential, [1, mean(x), 1] for the sigmoid) overflowed or got
        stuck as soon as the amplitude or the x range was not of order 1."""
        order = np.argsort(x)
        xs, ys = x[order], y[order]
        span = float(xs[-1] - xs[0]) or 1.0
        sign = 1.0 if np.median(ys) >= 0 else -1.0
        if model.startswith(POLYNOMIAL_PREFIX):
            degree = int(model[len(POLYNOMIAL_PREFIX):])
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')                  # RankWarning: ill-conditioned
                return [[float(c) for c in np.polyfit(xs, ys, degree)]]
        if model.startswith(CUSTOM_PREFIX):
            _, params = parse_expression(model[len(CUSTOM_PREFIX):])
            given = dict(start or {})
            unknown = [k for k in given if k not in params]
            if unknown:
                raise ValueError(f'start value for {", ".join(unknown)}: the parameters are '
                                 f'{", ".join(params)}')
            guesses = [[given.get(p, v) for p in params] for v in (1.0, 0.1, 10.0)]
            return guesses[:1] if len(given) == len(params) else guesses
        if model in ('Exponential', 'Power Law'):
            use = sign * ys > 0
            if model == 'Power Law':
                use &= xs > 0
            if use.sum() >= 3:
                xv = np.log(xs[use]) if model == 'Power Law' else xs[use]
                if np.ptp(xv) > 0:
                    slope, intercept = np.polyfit(xv, np.log(sign * ys[use]), 1)
                    return [[sign * float(np.exp(intercept)), float(slope)]]
            return [[sign, 1.0 / span if model == 'Exponential' else 1.0]]
        if model == 'Exponential + offset':
            return CurveFitter._offset_exponential_guesses(xs, ys)
        if model == 'Gaussian':
            return CurveFitter._gaussian_guesses(xs, ys)
        if model == 'Sinusoid':
            return CurveFitter._sinusoid_guesses(xs, ys)
        if model == 'Sigmoid':
            plateau = ys.max() if abs(ys.max()) >= abs(ys.min()) else ys.min()
            plateau = plateau or 1.0
            reached = (ys - plateau / 2) * np.sign(plateau) >= 0
            mid = float(xs[int(np.argmax(reached))]) if reached.any() else float(xs.mean())
            rising = 1.0 if abs(ys[-1]) >= abs(ys[0]) else -1.0
            scale = span / 10
            return [[plateau, mid, rising * scale], [plateau, mid, -rising * scale]]
        return [None]            # Linear, Quadratic, Cubic, Logarithmic: linear in the parameters

    @staticmethod
    def _normalize(model, popt, pcov):
        """Several parameter sets describe the same curve (a negative width, a negative amplitude
        with the phase turned half a cycle...): return the usual one, with pcov transformed."""
        popt = np.array(popt, dtype=float)
        pcov = np.array(pcov, dtype=float)
        sign = np.ones(len(popt))
        if model == 'Gaussian' and popt[2] < 0:
            popt[2] = -popt[2]
            sign[2] = -1
        elif model == 'Sinusoid':
            if popt[1] < 0:                                    # f < 0: f -> -f, a -> -a, phi -> -phi
                popt[0], popt[1], popt[2] = -popt[0], -popt[1], -popt[2]
                sign[0:3] = -1
            if popt[0] < 0:                                    # a < 0: a -> -a, phi -> phi + pi
                popt[0] = -popt[0]
                popt[2] += np.pi
                sign[0] *= -1
            popt[2] = (popt[2] + np.pi) % (2 * np.pi) - np.pi  # phase in (-pi, pi]
        if np.any(sign < 0):
            pcov = pcov * np.outer(sign, sign)
        return popt, pcov

    @staticmethod
    def lowess_key(span):
        return f'{LOWESS_PREFIX}{float(span):g}'

    @staticmethod
    def lowess_func(xs, ys):
        """The smoothed curve as a function of x (linear between its points, NaN outside them)."""
        xs, ys = np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)
        return lambda x, *p: np.interp(np.asarray(x, dtype=float), xs, ys, left=np.nan, right=np.nan)

    @staticmethod
    def _lowess(x, y, model):
        """Locally weighted regression: a smooth trend through the points, with no equation."""
        from statsmodels.nonparametric.smoothers_lowess import lowess
        try:
            span = float(model[len(LOWESS_PREFIX):])
        except ValueError:
            raise ValueError(f'unknown model: {model}') from None
        if not 0 < span <= 1:
            raise ValueError('the LOWESS span must be between 0 and 1 (the share of the points used '
                             'around each point)')
        if len(x) < 3:
            raise ValueError(f'LOWESS needs at least 3 points (only {len(x)} valid)')
        with np.errstate(all='ignore'):
            curve = lowess(y, x, frac=span, it=3, return_sorted=True)
        xs, ys = curve[:, 0], curve[:, 1]
        if not np.all(np.isfinite(ys)):
            raise ValueError('LOWESS could not smooth these data; try a larger span')
        func = CurveFitter.lowess_func(xs, ys)
        resid = y - func(x)
        sse = float(np.sum(resid ** 2))
        sst = float(np.sum((y - np.mean(y)) ** 2))
        return dict(popt=np.array([]), pcov=np.zeros((0, 0)), func=func, x0=0.0,
                    eq_str=f'LOWESS smoothing, span {span:g} (no equation)',
                    r2=1 - sse / sst if sst != 0 else 1.0, curve=(xs, ys))

    @staticmethod
    def fit_ex(x, y, model='Linear', start=None, x_range=None, sigma=None, robust=False):
        """Fit *model* to the points where x and y are finite.

        *model* is a name from MODELS, CurveFitter.polynomial_key(n), CurveFitter.custom_key(expr)
        or CurveFitter.lowess_key(span).  *start* ({parameter: value}) gives starting values to a
        custom model.  *x_range* = (lo, hi) (either may be None) fits only the points inside it.
        *sigma* gives the uncertainty of each y (a weighted fit: points with a large sigma count
        less, and the parameter errors are absolute).  *robust* reduces the influence of outliers
        (soft-L1 loss, scaled by the robust spread of the residuals).

        Returns a dict: popt, pcov, func (takes the original x), x0 (the shift the fit is
        measured from; 0 when none), eq_str, r2, n (points used), n_dropped (NaN or invalid),
        n_excluded (outside x_range), used (which input points were fitted), weighted, robust,
        outliers (robust fits: which input points were flagged) and n_outliers.
        Raises ValueError with a message the user can act on when it cannot be fitted."""
        spec = CurveFitter.spec(model)
        x_in = np.asarray(x, dtype=float)
        y_in = np.asarray(y, dtype=float)
        if x_in.shape != y_in.shape:
            raise ValueError(f'x has {x_in.size} points but y has {y_in.size}')
        ok = np.isfinite(x_in) & np.isfinite(y_in)
        sig_in = None
        if sigma is not None:
            sig_in = np.asarray(sigma, dtype=float)
            if sig_in.shape != y_in.shape:
                raise ValueError(f'the error column has {sig_in.size} points but y has {y_in.size}')
            ok &= np.isfinite(sig_in) & (sig_in > 0)
        n_dropped = int((~ok).sum())
        used = ok.copy()
        lo, hi = x_range if x_range else (None, None)
        if lo is not None:
            used &= x_in >= lo
        if hi is not None:
            used &= x_in <= hi
        n_excluded = int((ok & ~used).sum())
        x, y = x_in[used], y_in[used]
        s = None if sig_in is None else sig_in[used]
        common = dict(n=len(x), n_dropped=n_dropped, n_excluded=n_excluded, used=used,
                      weighted=s is not None, robust=False, outliers=None, n_outliers=0)
        where = f' in the chosen x range ({n_excluded} point(s) left out)' if n_excluded else ''
        if model.startswith(LOWESS_PREFIX):
            if len(x) == 0:
                raise ValueError('there are no valid points' + where)
            return {**CurveFitter._lowess(x, y, model), **common, 'weighted': False}
        n_par = len(spec.param_names)
        if len(x) == 0 and n_excluded:
            raise ValueError(f'there is no point in the chosen x range ({n_excluded} point(s) are outside it)')
        if len(x) < n_par:
            raise ValueError(f'{model} has {n_par} parameters and needs at least {n_par} points '
                             f'(only {len(x)} valid{where})')
        CurveFitter._check_domain(model, x, y)
        x0 = CurveFitter.x_shift(model, x)
        xs = x - x0
        base = spec.func

        def cost(popt):
            with np.errstate(all='ignore'):
                r = y - base(xs, *popt)
                return float(np.sum((r / s) ** 2 if s is not None else r ** 2))

        def run(p0, **kw):
            with np.errstate(all='ignore'), warnings.catch_warnings():
                warnings.simplefilter('ignore', optimize.OptimizeWarning)       # a flat fit has no covariance
                return optimize.curve_fit(base, xs, y, p0=p0, sigma=s, absolute_sigma=s is not None, **kw)

        best = None
        for p0 in CurveFitter._initial_guesses(model, xs, y, start):
            try:
                popt, pcov = run(p0, maxfev=10000)
            except (RuntimeError, ValueError, TypeError, ArithmeticError):
                continue
            c = cost(popt)
            if np.all(np.isfinite(popt)) and np.isfinite(c) and (best is None or c < best[0]):
                best = (c, popt, pcov)
        if best is None:
            raise ValueError(f'the {model} fit did not converge; check that the data follow this model'
                             + (' and try other start values' if spec.custom else ''))
        _, popt, pcov = best
        outliers = None
        if robust:
            r = (y - base(xs, *popt)) / (s if s is not None else 1.0)
            scale = 1.4826 * float(np.median(np.abs(r - np.median(r))))
            if scale > 0:
                try:
                    p_r, c_r = run(popt, method='trf', loss='soft_l1', f_scale=scale, max_nfev=10000)
                    if np.all(np.isfinite(p_r)):
                        popt, pcov = p_r, c_r
                except (RuntimeError, ValueError, TypeError, ArithmeticError):
                    pass                                      # keep the ordinary fit
                r = (y - base(xs, *popt)) / (s if s is not None else 1.0)
                scale = 1.4826 * float(np.median(np.abs(r - np.median(r)))) or scale
                flagged = np.abs(r - np.median(r)) > 3 * scale
                outliers = np.zeros(len(x_in), dtype=bool)
                outliers[np.flatnonzero(used)[flagged]] = True
        popt, pcov = CurveFitter._normalize(model, popt, pcov)
        pred = base(xs, *popt)
        if s is not None:
            w = 1.0 / s ** 2
            ybar = float(np.sum(w * y) / np.sum(w))
            sse = float(np.sum(w * (y - pred) ** 2))
            sst = float(np.sum(w * (y - ybar) ** 2))
        else:
            sse = float(np.sum((y - pred) ** 2))
            sst = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1 - sse / sst if sst != 0 else 1.0
        try:
            eq_str = spec.template.format(*popt)
            if not spec.custom:                       # '+ -3' reads better as '− 3'
                eq_str = eq_str.replace('+ -', '− ').replace('−-', '+')
            if x0:
                eq_str = (re.sub(r'\bx\b', '(x−x₀)', eq_str) if spec.custom
                          else eq_str.replace('x', '(x−x₀)'))
        except (IndexError, KeyError, ValueError, TypeError):
            eq_str = f'{model} fit'
        common.update(robust=bool(robust), outliers=outliers,
                      n_outliers=0 if outliers is None else int(outliers.sum()))
        return dict(popt=popt, pcov=pcov, func=CurveFitter.make_func(model, x0), x0=x0,
                    eq_str=eq_str, r2=r2, **common)

    @staticmethod
    def fit(x, y, model='Linear'):
        """Fit data to model.
        Returns (popt, pcov, func, equation_str, r2) or (None, None, None, '', None) on failure.
        (fit_ex reports why a fit failed.)
        """
        try:
            r = CurveFitter.fit_ex(x, y, model)
        except ValueError:
            return None, None, None, '', None
        return r['popt'], r['pcov'], r['func'], r['eq_str'], r['r2']

    @staticmethod
    def full_stats(x, y, popt, pcov, func, model, alpha=0.05, sigma=None):
        """Compute comprehensive regression statistics.

        Returns a dict with:
          n, p, dof, r2, r2_adj, rmse, sse, sst, mse, f_stat, f_pvalue,
          aic, bic, param_names, param_values, param_se, param_tstat,
          param_pvalue, param_ci_lo, param_ci_hi (all at given alpha).

        With *sigma* (the uncertainty of each y) the fit is weighted: r2 is the weighted R²,
        sse is chi², mse the reduced chi², rmse stays in y units, and the information criteria
        use the chi² likelihood; weighted=True, chi2 and chi2_red are added, and there is no F test.
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        sig = None
        if sigma is not None:
            sig = np.asarray(sigma, dtype=float)
            ok &= np.isfinite(sig) & (sig > 0)
            sig = sig[ok]
        x, y = x[ok], y[ok]
        n = len(x)
        p = len(popt)
        dof = n - p

        y_pred = func(x, *popt)
        residuals = y - y_pred
        raw_sse = float(np.sum(residuals ** 2))
        if sig is not None:
            w = 1.0 / sig ** 2
            ybar = float(np.sum(w * y) / np.sum(w))
            sse = float(np.sum(w * residuals ** 2))                # chi²
            sst = float(np.sum(w * (y - ybar) ** 2))
        else:
            sse = raw_sse
            sst = float(np.sum((y - np.mean(y)) ** 2))
        mse = sse / dof if dof > 0 else np.nan                     # reduced chi² when weighted
        rmse = np.sqrt(raw_sse / dof) if dof > 0 else np.nan
        r2 = 1 - sse / sst if sst != 0 else 1.0
        r2_adj = 1 - (1 - r2) * (n - 1) / dof if dof > 0 else np.nan

        # F-statistic (model vs intercept-only).  Only for the models that have an intercept-only
        # model nested in them (linear in the parameters, with a constant term); for the
        # exponential, power and sigmoid there is no such test.
        f_stat, f_pvalue = np.nan, np.nan
        if CurveFitter.has_f_test(model) and sig is None:
            try:
                if p > 1 and mse and not np.isnan(mse):
                    f_stat = ((sst - sse) / (p - 1)) / mse
                    f_pvalue = float(scipy_stats.f.sf(f_stat, p - 1, dof))   # sf: no underflow to 0
            except (ArithmeticError, ValueError, TypeError):
                f_stat, f_pvalue = np.nan, np.nan

        # Information criteria, from the Gaussian log-likelihood at the maximum-likelihood
        # variance sse / n (as statsmodels and most textbooks do)
        try:
            if p == 0:
                aic = bic = np.nan                            # a smoothing has no parameters to count
            elif sig is not None:                             # -2 ln L = chi² + sum ln(2 pi sigma²)
                minus2ll = sse + float(np.sum(np.log(2 * np.pi * sig ** 2)))
                aic = 2 * p + minus2ll
                bic = p * np.log(n) + minus2ll
            else:
                with np.errstate(divide='ignore'):            # sse = 0: a perfect fit
                    ll = -n / 2 * (np.log(2 * np.pi * sse / n) + 1)
                aic = 2 * p - 2 * ll
                bic = p * np.log(n) - 2 * ll
        except (ArithmeticError, ValueError):
            aic = bic = np.nan

        # Per-parameter stats
        perr = np.sqrt(np.abs(np.diag(pcov))) if pcov is not None else np.full(p, np.nan)
        t_alpha = scipy_stats.t.ppf(1 - alpha / 2, dof) if dof > 0 else np.nan
        param_names  = CurveFitter.param_names(model, p)
        param_tstat  = [float(popt[i] / perr[i]) if perr[i] > 0 else np.nan for i in range(p)]
        param_pvalue = [float(2 * scipy_stats.t.sf(abs(param_tstat[i]), dof))
                        if not np.isnan(param_tstat[i]) else np.nan for i in range(p)]
        param_ci_lo  = [float(popt[i] - t_alpha * perr[i]) if not np.isnan(t_alpha) else np.nan for i in range(p)]
        param_ci_hi  = [float(popt[i] + t_alpha * perr[i]) if not np.isnan(t_alpha) else np.nan for i in range(p)]

        extra = {}
        if sig is not None:
            extra = dict(weighted=True, chi2=float(sse), chi2_red=float(mse))
        return dict(
            **extra,
            n=int(n), p=int(p), dof=int(dof), alpha=float(alpha),
            r2=float(r2), r2_adj=float(r2_adj),
            rmse=float(rmse), sse=float(sse), sst=float(sst), mse=float(mse),
            f_stat=float(f_stat), f_pvalue=float(f_pvalue),
            aic=float(aic), bic=float(bic),
            param_names=[str(n_) for n_ in param_names],
            param_values=[float(v) for v in popt],
            param_se=[float(v) for v in perr],
            param_tstat=param_tstat,
            param_pvalue=param_pvalue,
            param_ci_lo=param_ci_lo,
            param_ci_hi=param_ci_hi,
        )

    @staticmethod
    def _jacobian(x, popt, func):
        """Numerical Jacobian dy/dp at each x point."""
        eps = 1e-6
        J = np.zeros((len(x), len(popt)))
        for i, p in enumerate(popt):
            dp = eps * abs(p) if abs(p) > eps else eps
            pp = popt.copy()
            pp[i] += dp
            pm = popt.copy()
            pm[i] -= dp
            J[:, i] = (func(x, *pp) - func(x, *pm)) / (2 * dp)
        return J

    @staticmethod
    def band_multiplier(n_sigma, dof=None):
        """How many standard errors a "n_sigma" band spans.  With the degrees of freedom of the
        fit it is the Student-t quantile that covers the same probability as n_sigma normal
        sigmas (68.3 %, 95.4 %, 99.7 %), so the labelled percentages hold for few points too;
        without them, n_sigma itself."""
        if not dof or dof <= 0:
            return float(n_sigma)
        coverage = float(scipy_stats.norm.cdf(n_sigma) - scipy_stats.norm.cdf(-n_sigma))
        return float(scipy_stats.t.ppf((1 + coverage) / 2, dof))

    @staticmethod
    def confidence_band(x, popt, pcov, func, n_sigma=1, dof=None):
        """
        Compute upper and lower confidence bands using linear error propagation (delta method).
        ``dof`` (n - parameters) makes the band exact in probability for few points.
        Returns (y_upper, y_lower) arrays.
        """
        x = np.array(x, dtype=float)
        y0 = func(x, *popt)
        J = CurveFitter._jacobian(x, popt, func)
        try:
            var_y = np.einsum('ni,ij,nj->n', J, pcov, J)
            sigma_y = np.sqrt(np.abs(var_y))
        except (ValueError, TypeError):
            sigma_y = np.zeros_like(y0)
        k = CurveFitter.band_multiplier(n_sigma, dof)
        return y0 + k * sigma_y, y0 - k * sigma_y

    @staticmethod
    def prediction_band(x, y, popt, pcov, func, n_sigma=1, used=None):
        """
        Prediction interval: CI band + residual variance (MSE).
        A prediction interval is wider than a CI band because it accounts for
        both parameter uncertainty and new-observation scatter.
        Returns (y_upper, y_lower) arrays.
        """
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
        if used is not None:                                  # only the points the fit used
            ok &= np.asarray(used, dtype=bool)
        n = int(ok.sum())
        p = len(popt)
        dof = n - p

        y0 = func(x, *popt)
        residuals = (y - y0)[ok]
        mse = float(np.sum(residuals ** 2) / dof) if dof > 0 else 0.0

        J = CurveFitter._jacobian(x, popt, func)
        try:
            var_ci = np.einsum('ni,ij,nj->n', J, pcov, J)
            var_ci = np.abs(var_ci)
        except (ValueError, TypeError):
            var_ci = np.zeros(len(x))

        var_pred = var_ci + mse   # total prediction variance
        sigma_pred = np.sqrt(var_pred)
        k = CurveFitter.band_multiplier(n_sigma, dof)
        return y0 + k * sigma_pred, y0 - k * sigma_pred
