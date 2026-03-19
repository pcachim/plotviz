"""
Copyright (c) 2026 Paulo Cachim
This file is part of this project and is licensed under the MIT License.
You may obtain a copy of the License in the LICENSE.md file in the root
of this repository or at https://opensource.org/licenses/MIT.


data/scientific.py - Curve fitting and statistical analysis
"""
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

    @staticmethod
    def fit(x, y, model='Linear'):
        """Fit data to model.
        Returns (popt, pcov, func, equation_str, r2) or (None, None, None, '', None) on failure.
        """
        try:
            x = np.array(x, dtype=float)
            y = np.array(y, dtype=float)

            if model not in CurveFitter.MODELS:
                return None, None, None, '', None

            func = CurveFitter.MODELS[model]

            p0_map = {
                'Exponential': [1, 0.1],
                'Power Law':   [1, 1],
                'Sigmoid':     [1, float(np.mean(x)), 1],
            }
            kwargs = {'maxfev': 10000}
            if model in p0_map:
                kwargs['p0'] = p0_map[model]

            popt, pcov = optimize.curve_fit(func, x, y, **kwargs)

            # R² calculation
            y_pred = func(x, *popt)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 1.0

            # Format equation
            tmpl = CurveFitter.EQ_TEMPLATES.get(model, 'y = f(x)')
            try:
                eq_str = tmpl.format(*popt)
            except Exception:
                eq_str = f'{model} fit'

            return popt, pcov, func, eq_str, r2

        except Exception as e:
            print(f'Fitting error: {e}')
            return None, None, None, '', None

    @staticmethod
    def full_stats(x, y, popt, pcov, func, model, alpha=0.05):
        """Compute comprehensive regression statistics.

        Returns a dict with:
          n, p, dof, r2, r2_adj, rmse, sse, sst, mse, f_stat, f_pvalue,
          aic, bic, param_names, param_values, param_se, param_tstat,
          param_pvalue, param_ci_lo, param_ci_hi (all at given alpha).
        """
        x = np.array(x, dtype=float)
        y = np.array(y, dtype=float)
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

        # F-statistic (model vs intercept-only)
        try:
            f_stat = ((sst - sse) / (p - 1)) / mse if (p > 1 and mse and not np.isnan(mse)) else np.nan
            f_pvalue = float(1 - scipy_stats.f.cdf(f_stat, p - 1, dof)) if not np.isnan(f_stat) else np.nan
        except Exception:
            f_stat, f_pvalue = np.nan, np.nan

        # Information criteria
        try:
            ll = -n / 2 * np.log(2 * np.pi * mse) - sse / (2 * mse)
            aic = 2 * p - 2 * ll
            bic = p * np.log(n) - 2 * ll
        except Exception:
            aic = bic = np.nan

        # Per-parameter stats
        perr = np.sqrt(np.diag(pcov)) if pcov is not None else np.full(p, np.nan)
        t_alpha = scipy_stats.t.ppf(1 - alpha / 2, dof) if dof > 0 else np.nan
        param_names  = CurveFitter.PARAM_NAMES.get(model, [f'p{i}' for i in range(p)])
        param_tstat  = [float(popt[i] / perr[i]) if perr[i] > 0 else np.nan for i in range(p)]
        param_pvalue = [float(2 * (1 - scipy_stats.t.cdf(abs(param_tstat[i]), dof)))
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
            pp = popt.copy(); pp[i] += dp
            pm = popt.copy(); pm[i] -= dp
            J[:, i] = (func(x, *pp) - func(x, *pm)) / (2 * dp)
        return J

    @staticmethod
    def confidence_band(x, popt, pcov, func, n_sigma=1):
        """
        Compute upper and lower confidence bands using linear error propagation (delta method).
        Returns (y_upper, y_lower) arrays.
        """
        x = np.array(x, dtype=float)
        y0 = func(x, *popt)
        J = CurveFitter._jacobian(x, popt, func)
        try:
            var_y = np.einsum('ni,ij,nj->n', J, pcov, J)
            sigma_y = np.sqrt(np.abs(var_y))
        except Exception:
            sigma_y = np.zeros_like(y0)
        return y0 + n_sigma * sigma_y, y0 - n_sigma * sigma_y

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
        n = len(x)
        p = len(popt)
        dof = n - p

        y0 = func(x, *popt)
        residuals = y - y0
        mse = float(np.sum(residuals ** 2) / dof) if dof > 0 else 0.0

        J = CurveFitter._jacobian(x, popt, func)
        try:
            var_ci = np.einsum('ni,ij,nj->n', J, pcov, J)
            var_ci = np.abs(var_ci)
        except Exception:
            var_ci = np.zeros(len(x))

        var_pred = var_ci + mse   # total prediction variance
        sigma_pred = np.sqrt(var_pred)
        return y0 + n_sigma * sigma_pred, y0 - n_sigma * sigma_pred
