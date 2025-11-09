# MIT License
"""Economic utility functions for the Paulownia dashboard.

This module defines common financial metrics such as net present value
(NPV) and internal rate of return (IRR).  The functions are deliberately
lightweight and do not depend on the rest of the model structure.
"""
from __future__ import annotations

from typing import Iterable, List
from .params import Scenario

def npv(cashflows: Iterable[float], discount_rate: float) -> float:
    """Compute the net present value of a series of cashflows.

    Parameters
    ----------
    cashflows:
        Iterable of annual cashflows where the first element is cashflow
        in year 1.
    discount_rate:
        Discount rate as a decimal (e.g. 0.08 for 8%).

    Returns
    -------
    float
        Net present value of the cashflows.
    """
    return sum(cf / ((1.0 + discount_rate) ** i) for i, cf in enumerate(cashflows, start=1))


def irr(cashflows: Iterable[float], guess: float = 0.1) -> float:
    """Approximate the internal rate of return of a series of cashflows.

    A simple bisection search is used to find the rate that yields an
    NPV close to zero.

    Parameters
    ----------
    cashflows:
        Iterable of annual cashflows where the first element is cashflow
        in year 1.
    guess:
        Initial guess for the rate.  Ignored in this implementation.

    Returns
    -------
    float
        Approximate IRR as a decimal.  Returns `float('nan')` if no
        solution is found in the interval [-0.9, 1.0].
    """
    lo, hi = -0.9, 1.0
    # define a nested NPV function for this sequence
    def f(rate: float) -> float:
        return npv(cashflows, rate)
    f_lo = f(lo)
    for _ in range(60):
        mid = (lo + hi) / 2.0
        f_mid = f(mid)
        # if mid is root or interval width is negligible, return
        if abs(f_mid) < 1e-6 or (hi - lo) < 1e-6:
            return mid
        # update bounds based on sign of function
        if (f_mid > 0 and f_lo > 0) or (f_mid < 0 and f_lo < 0):
            lo = mid
            f_lo = f_mid
        else:
            hi = mid
    return float("nan")


def payback_period(cashflows: Iterable[float]) -> float:
    """Estimate the payback period (years) for a series of cashflows.

    The payback period is the time required for the cumulative cashflow
    to become positive.  If the cashflows never become positive,
    returns NaN.

    Parameters
    ----------
    cashflows:
        Iterable of annual cashflows.

    Returns
    -------
    float
        The payback period in years, or NaN if never profitable.
    """
    cum = 0.0
    for i, cf in enumerate(cashflows, start=1):
        cum += cf
        if cum >= 0.0:
            return float(i)
    return float("nan")
