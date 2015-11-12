# -*- coding: utf-8 -*-
# The o2sat() function needs to be verified. What's below was copied from:
# https://github.com/pyoceans/python-oceans/issues/14
# We are advised to use with caution.

import seawater.eos80 as sw
import numpy as np

from seawater.eos80 import T68conv
from seawater.constants import Kelvin

def o2sat(s, pt):
    """
    Calculate oxygen concentration at saturation.  Molar volume of oxygen
    at STP obtained from NIST website on the thermophysical properties of fluid
    systems (http://webbook.nist.gov/chemistry/fluid/).

    Parameters
    ----------
    s : array_like
        Salinity [pss-78]
    pt : array_like
         Potential Temperature [degC ITS-90]

    Returns
    -------
    osat : array_like
          Oxygen concentration at saturation [umol/kg]

    Examples
    --------
    >>> import os
    >>> from pandas import read_csv
    >>> import oceans.seawater.sw_extras as swe
    >>> path = os.path.split(os.path.realpath(swe.__file__))[0]
    # Table 9 pg. 732. Values in ml / kg
    >>> pt = np.array([-1, 0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22,
    ...                24, 26, 28, 30, 32, 34, 36, 38, 40]) / 1.00024
    >>> s = np.array([0, 10, 20, 30, 34, 35, 36, 38, 40])
    >>> s, pt = np.meshgrid(s, pt)
    >>> osat = swe.o2sat(s, pt) * 22.392 / 1000  # um/kg to ml/kg.
    >>> weiss_1979 = read_csv('%s/test/o2.csv' % path, index_col=0).values
    >>> np.testing.assert_almost_equal(osat.ravel()[2:],
    ...                                weiss_1979.ravel()[2:], decimal=3)


    References
    -----
    .. [1] The solubility of nitrogen, oxygen and argon in water and seawater -
    Weiss (1970) Deep Sea Research V17(4): 721-735.
    """

    t = T68conv(pt) + Kelvin
    # Eqn (4) of Weiss 1970 (the constants are used for units of ml O2/kg).
    a = (-177.7888, 255.5907, 146.4813, -22.2040)
    b = (-0.037362, 0.016504, -0.0020564)
    lnC = (a[0] + a[1] * (100. / t) + a[2] * np.log(t / 100.) + a[3] *
           (t / 100.) +
           s * (b[0] + b[1] * (t / 100.) + b[2] * (t / 100.) ** 2))
    osat = np.exp(lnC) * 1000. / 22.392  # Convert from ml/kg to um/kg.

    # The Apparent Oxygen Utilization (AOU) value was obtained by subtracting
    # the measured value from the saturation value computed at the potential
    # temperature of water and 1 atm total pressure using the following
    # expression based on the data of Murray and Riley (1969):

    # ln(O2 in µmol/kg) = - 173.9894 + 255.5907(100/TK) + 146.4813 ln(TK/100) -
    # 22.2040(TK/100) + Sal [-0.037362 + 0.016504(TK/100) - 0.0020564(TK/100)2],
    # where TK is temperature in °K and Sal in the Practical Salinity (SP) scale.

    return osat

def convert_to_mll(o2, s, t, p):
    '''Convert dissolved oxygen concentration from um/kg to ml/l.
    '''
    return sw.dens(s, t, p) * o2 / 44.66 / 1000.0

