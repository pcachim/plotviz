"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the GNU General Public License v3.0 or later.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://www.gnu.org/licenses/gpl-3.0.html.


data/scientific.py - Curve fitting and statistical analysis
"""
import warnings

import numpy as np
from scipy import optimize, stats as scipy_stats


class CurveFitter:
    MODELS = {
        'Linear':      lambda x, a, b: a * x + b,
        'Quadratic':   lambda x, a, b, c: a * x**2 + b * x + c,
        'Cubic':       lambda x, a, b, c, d: a * x**3 + b * x**2 + c * x + d,
        'Exponential': lambda x, a, b: a * np.exp(b * x),
        'Power Law':   lambda x, a, b: a * x**b,
        'Logarithmic': lambda x, a, b: a * np.log(x) + b,
        'Sigmoid':     lambda x, a, b, c: a / (1 + np.exp(-(x - b) / c)),
    }

    PARAM_NAMES = {
        'Linear':      ['a', 'b'],
        'Quadratic':   ['a', 'b', 'c'],
        'Cubic':       ['a', 'b', 'c', 'd'],
        'Exponential': ['a', 'b'],
        'Power Law':   ['a', 'b'],
        'Logarithmic': ['a', 'b'],
        'Sigmoid':     ['a', 'b (midpoint)', 'c (scale)'],
    }

    # Human-readable equation templates (use popt values)
    EQ_TEMPLATES = {
        'Linear':      'y = {0:.4g}·x + {1:.4g}',
        'Quadratic':   'y = {0:.4g}·x² + {1:.4g}·x + {2:.4g}',
        'Cubic':       'y = {0:.4g}·x³ + {1:.4g}·x² + {2:.4g}·x + {3:.4g}',
        'Exponential': 'y = {0:.4g}·e^({1:.4g}·x)',
        'Power Law':   'y = {0:.4g}·x^{1:.4g}',
        'Logarithmic': 'y = {0:.4g}·ln(x) + {1:.4g}',
        'Sigmoid':     'y = {0:.4g} / (1 + e^(-(x−{1:.4g})/{2:.4g}))',
    }

    # Models that are linear in their parameters and have an intercept: an intercept-only
    # model is nested in them, so the overall F-test is meaningful.
    F_TEST_MODELS = ('Linear', 'Quadratic', 'Cubic', 'Logarithmic')

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

    @staticmethod
    def x_shift(model, x):
        """The x value the fit is measured from.  Far from zero (years, dates) the models are
        badly conditioned or overflow (e^(b·19800)), so the fit works on x - x0 instead.
        Logarithmic and Power Law keep the real x: their domain is x > 0."""
        if model in ('Logarithmic', 'Power Law') or len(x) == 0:
            return 0.0
        span = float(np.ptp(x))
        centre = float(np.mean(x))
        return centre if span > 0 and abs(centre) > 5 * span else 0.0

    @staticmethod
    def make_func(model, x0=0.0):
        """The model function; with a shift x0 it takes the original x and uses x - x0."""
        base = CurveFitter.MODELS[model]
        if not x0:
            return base
        return lambda x, *p: base(np.asarray(x, dtype=float) - x0, *p)

    @staticmethod
    def _check_domain(model, x, y):
        if model in ('Logarithmic', 'Power Law') and np.any(x <= 0):
            raise ValueError(f'{model} needs every x to be greater than 0 (found x <= 0)')

    @staticmethod
    def _initial_guesses(model, x, y):
        """Starting values taken from the data (x is already shifted).  The old fixed ones
        ([1, 0.1] for the exponential, [1, mean(x), 1] for the sigmoid) overflowed or got
        stuck as soon as the amplitude or the x range was not of order 1."""
        order = np.argsort(x)
        xs, ys = x[order], y[order]
        span = float(xs[-1] - xs[0]) or 1.0
        sign = 1.0 if np.median(ys) >= 0 else -1.0
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
        if model == 'Sigmoid':
            plateau = ys.max() if abs(ys.max()) >= abs(ys.min()) else ys.min()
            plateau = plateau or 1.0
            reached = (ys - plateau / 2) * np.sign(plateau) >= 0
            mid = float(xs[int(np.argmax(reached))]) if reached.any() else float(xs.mean())
            rising = 1.0 if abs(ys[-1]) >= abs(ys[0]) else -1.0
            scale = span / 10
            return [[plateau, mid, rising * scale], [plateau, mid, -rising * scale]]
        return [None]            # polynomials / logarithmic: linear in the parameters

    @staticmethod
    def fit_ex(x, y, model='Linear'):
        """Fit *model* to the points where x and y are finite.

        Returns a dict: popt, pcov, func (takes the original x), x0 (the shift the fit is
        measured from; 0 when none), eq_str, r2, n (points used) and n_dropped.
        Raises ValueError with a message the user can act on when it cannot be fitted."""
        if model not in CurveFitter.MODELS:
            raise ValueError(f'unknown model: {model}')
        x, y, n_dropped = CurveFitter.clean(x, y)
        n_par = len(CurveFitter.PARAM_NAMES[model])
        if len(x) < n_par:
            raise ValueError(f'{model} has {n_par} parameters and needs at least {n_par} points '
                             f'(only {len(x)} valid)')
        CurveFitter._check_domain(model, x, y)
        x0 = CurveFitter.x_shift(model, x)
        xs = x - x0
        base = CurveFitter.MODELS[model]
        best = None
        for p0 in CurveFitter._initial_guesses(model, xs, y):
            try:
                with np.errstate(all='ignore'), warnings.catch_warnings():
                    warnings.simplefilter('ignore', optimize.OptimizeWarning)   # a flat fit has no covariance
                    popt, pcov = optimize.curve_fit(base, xs, y, p0=p0, maxfev=10000)
            except (RuntimeError, ValueError, TypeError, ArithmeticError):
                continue
            with np.errstate(all='ignore'):
                sse = float(np.sum((y - base(xs, *popt)) ** 2))
            if np.all(np.isfinite(popt)) and np.isfinite(sse) and (best is None or sse < best[0]):
                best = (sse, popt, pcov)
        if best is None:
            raise ValueError(f'the {model} fit did not converge; check that the data follow this model')
        sse, popt, pcov = best
        sst = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1 - sse / sst if sst != 0 else 1.0
        tmpl = CurveFitter.EQ_TEMPLATES.get(model, 'y = f(x)')
        try:
            eq_str = tmpl.format(*popt)
            if x0:
                eq_str = eq_str.replace('x', '(x\u2212x\u2080)')
        except (IndexError, KeyError, ValueError, TypeError):
            eq_str = f'{model} fit'
        return dict(popt=popt, pcov=pcov, func=CurveFitter.make_func(model, x0), x0=x0,
                    eq_str=eq_str, r2=r2, n=len(x), n_dropped=n_dropped)

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
    def full_stats(x, y, popt, pcov, func, model, alpha=0.05):
        """Compute comprehensive regression statistics.

        Returns a dict with:
          n, p, dof, r2, r2_adj, rmse, sse, sst, mse, f_stat, f_pvalue,
          aic, bic, param_names, param_values, param_se, param_tstat,
          param_pvalue, param_ci_lo, param_ci_hi (all at given alpha).
        """
        x, y, _ = CurveFitter.clean(x, y)
        n = len(x)
        p = len(popt)
        dof = n - p

        y_pred = func(x, *popt)
        residuals = y - y_pred
        sse = float(np.sum(residuals ** 2))
        sst = float(np.sum((y - np.mean(y)) ** 2))
        mse = sse / dof if dof > 0 else np.nan
        rmse = np.sqrt(mse) if dof > 0 else np.nan
        r2 = 1 - sse / sst if sst != 0 else 1.0
        r2_adj = 1 - (1 - r2) * (n - 1) / dof if dof > 0 else np.nan

        # F-statistic (model vs intercept-only).  Only for the models that have an intercept-only
        # model nested in them (linear in the parameters, with a constant term); for the
        # exponential, power and sigmoid there is no such test.
        f_stat, f_pvalue = np.nan, np.nan
        if model in CurveFitter.F_TEST_MODELS:
            try:
                if p > 1 and mse and not np.isnan(mse):
                    f_stat = ((sst - sse) / (p - 1)) / mse
                    f_pvalue = float(scipy_stats.f.sf(f_stat, p - 1, dof))   # sf: no underflow to 0
            except (ArithmeticError, ValueError, TypeError):
                f_stat, f_pvalue = np.nan, np.nan

        # Information criteria, from the Gaussian log-likelihood at the maximum-likelihood
        # variance sse / n (as statsmodels and most textbooks do)
        try:
            with np.errstate(divide='ignore'):                # sse = 0: a perfect fit
                ll = -n / 2 * (np.log(2 * np.pi * sse / n) + 1)
            aic = 2 * p - 2 * ll
            bic = p * np.log(n) - 2 * ll
        except (ArithmeticError, ValueError):
            aic = bic = np.nan

        # Per-parameter stats
        perr = np.sqrt(np.diag(pcov)) if pcov is not None else np.full(p, np.nan)
        t_alpha = scipy_stats.t.ppf(1 - alpha / 2, dof) if dof > 0 else np.nan
        param_names  = CurveFitter.PARAM_NAMES.get(model, [f'p{i}' for i in range(p)])
        param_tstat  = [float(popt[i] / perr[i]) if perr[i] > 0 else np.nan for i in range(p)]
        param_pvalue = [float(2 * scipy_stats.t.sf(abs(param_tstat[i]), dof))
                        if not np.isnan(param_tstat[i]) else np.nan for i in range(p)]
        param_ci_lo  = [float(popt[i] - t_alpha * perr[i]) if not np.isnan(t_alpha) else np.nan for i in range(p)]
        param_ci_hi  = [float(popt[i] + t_alpha * perr[i]) if not np.isnan(t_alpha) else np.nan for i in range(p)]

        return dict(
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
    def prediction_band(x, y, popt, pcov, func, n_sigma=1):
        """
        Prediction interval: CI band + residual variance (MSE).
        A prediction interval is wider than a CI band because it accounts for
        both parameter uncertainty and new-observation scatter.
        Returns (y_upper, y_lower) arrays.
        """
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)
        ok = np.isfinite(x) & np.isfinite(y)
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
