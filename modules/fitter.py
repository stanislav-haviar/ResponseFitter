# fitter.py

import numpy as np
from scipy.optimize import curve_fit, root_scalar
import pandas as pd


class Fitter:
    def single_exp_decay(self, x, y, x0):
        def func(x, y0, A1, tau1):
            return y0 + A1 * np.exp(-(x - x0) / tau1)

        if (y[0] > y[-1]):
            p0 = [y.min(), - (y.max()-y.min()), (x.max()-x.min())/100]
        else:
            p0 = [y.max(), + (y.max()-y.min()), (x.max()-x.min())/100]
        try:
            params, _ = curve_fit(func, x, y, p0=p0, maxfev=10000)
            return params
        except RuntimeError:
            return None

    def double_exp_decay(self, x, y, x0):
        def func(x, y0, A1, tau1, A2, tau2):
            return y0 + A1 * np.exp(-(x - x0) / tau1) + A2 * np.exp(-(x - x0) / tau2)

        p_single = self.single_exp_decay(x, y, x0)
        p0 = np.append(p_single,p_single[1:])

        try:
            params, _ = curve_fit(func, x, y, p0=p0, maxfev=10000)
            return params
        except RuntimeError:
            return None

    def auxiliary(self, x, y, x0):
        def func(x, y0, A1):
            return y0 + (x - x0) * A1

        p0 = [y.min(), 0.0]
        try:
            params, _ = curve_fit(func, x, y, p0=p0, maxfev=10000)
            return params
        except RuntimeError:
            return None

    def get_fit_curve(self, x, fit_type, fit_params, x0):
        if fit_type == "Single Exp. Decay":
            y0 = float(fit_params["y0"])
            A1 = float(fit_params["A1"])
            tau1 = float(fit_params["tau1"])
            return y0 + A1 * np.exp(-(x - x0) / tau1)
        elif fit_type == "Double Exp. Decay":
            y0 = float(fit_params["y0"])
            A1 = float(fit_params["A1"])
            tau1 = float(fit_params["tau1"])
            A2 = float(fit_params["A2"])
            tau2 = float(fit_params["tau2"])
            return y0 + A1 * np.exp(-(x - x0) / tau1) + A2 * np.exp(-(x - x0) / tau2)
        elif fit_type == "Aux":
            y0 = float(fit_params["y0"])
            A1 = float(fit_params["A1"])
            return y0 + (x - x0) * A1
        else:
            return np.zeros_like(x)

    def save_project(self, filepath, fits):
        df = pd.DataFrame(fits)
        df.to_csv(filepath, index=False, float_format='%.3E')

    def export_fits(self, filepath, fits):
        df = pd.DataFrame(fits)
        if filepath.endswith('.xls') or filepath.endswith('.xlsx'):
            df.to_excel(filepath, index=False, engine='openpyxl')
        else:
            df.to_csv(filepath, index=False, sep=';')

    def calculate_t90(self, section):
        """
        Calculates t90 for a fitted section.
        The starting value is prev_y0 if provided;
        for the very first section, it's the y value at x0.
        Stores the result in section['tau90'].
        """
        fit_type = section['Type']
        x0 = float(section['From'])  # Ensure x0 is a float
        y0 = float(section['y0'])
        y_start = float(section['prev_y0'])
        try:
            total_change = y_start - y0

            if total_change == 0:
                section['tau90'] = ''
                section['Comment'] = 'No change detected'
                return

            if fit_type == 'Single Exp. Decay':
                tau1 = float(section['tau1'])

                # Solve for t90
                # exp(-(t90 - x0)/tau1) = 0.1
                #t90 = x0 - tau1 * np.log(0.1)
                t90 = - tau1 * np.log(0.1)

                section['tau90'] = f"{t90:.5G}"

            elif fit_type == 'Double Exp. Decay':
                A1 = float(section['A1'])
                tau1 = float(section['tau1'])
                A2 = float(section['A2'])
                tau2 = float(section['tau2'])

                # Target value at t90 (90% approach to y0)
                target_value = y0 + 0.1 * total_change

                def func(t):
                    return y0 + A1 * np.exp(-(t - x0) / tau1) + A2 * np.exp(-(t - x0) / tau2) - target_value

                # Set reasonable bounds for t90
                t_min = x0
                t_max = x0 + 10 * max(tau1, tau2)

                # Use root-finding to solve for t90
                result = root_scalar(func, bracket=[t_min, t_max], method='brentq')

                if result.converged:
                    t90 = result.root - x0
                    section['tau90'] = f"{t90:.1f}"
                else:
                    section['tau90'] = 'err.'

            else:
                section['tau90'] = ''
                section['Comment'] = 'Unknown fit type'

        except Exception as e:
            section['tau90'] = ''
            section['Comment'] = f"Error calculating t90: {e}"