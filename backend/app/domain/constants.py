"""Constantes físicas em unidades SI.

Fontes:
- MU_EARTH, R_EARTH_EQ: IERS Conventions (2010) / WGS-84 (EGM2008 GM).
- G0: valor padrão da gravidade (CGPM 1901, ISO 80000-3).
- C_LIGHT: definição exata do SI.
"""

from typing import Final

MU_EARTH: Final[float] = 3.986004418e14  # m^3/s^2
R_EARTH_EQ: Final[float] = 6_378_137.0  # m
G0: Final[float] = 9.80665  # m/s^2
C_LIGHT: Final[float] = 299_792_458.0  # m/s
