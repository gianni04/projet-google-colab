# Projet Google Colab 

Construction d'une courbe de taux zéro-coupon pour l'EUR à partir des données publiques de la BCE.

## Méthodologie
- Source : BCE (obligations AAA zone Euro, €STR, DFR)
- Interpolation : Splines cubiques (scipy)
- Convention : Compounding continu

## Technologies
Python · pandas · scipy · sdmx · matplotlib
