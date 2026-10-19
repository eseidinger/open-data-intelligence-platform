# Expected results

`simulation-cases.json` contains independently hand-calculated hourly cases for
PV clipping, import, export, charge and discharge efficiency, battery capacity
and power limits, and terminal discarded energy. Tests compare the reference
implementation with these fixed values; the implementation does not generate
its own oracle.

The optimization fixture records the exact generated configurations, constraint
outcomes, deterministic ranking, and reference recommendation.

`optimization-reference.json` uses these reviewed generation rules:

- fit PV modules within the 35 m2 roof and the global 100-module limit;
- accept an inclusive DC/AC ratio from 0.8 through 1.5;
- use exactly one inverter;
- use no battery or one battery model with quantity 1 through 4;
- evaluate budget and minimum self-sufficiency on every generated candidate;
- rank feasible candidates by annualized cost rounded to cents, initial
  investment rounded to cents, and then configuration ID.

The fixture contains 252 generated candidates, of which 194 are feasible. The
reviewed recommendation is 18 synthetic 400 Wp modules, one synthetic 5 kW
inverter, and one synthetic 10 kWh battery.
