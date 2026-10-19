# Fixtures

This directory contains the complete 8,784-hour Wasserburg am Inn energy
fixture and a compact non-energy publication proving that the generic manifest
is domain-neutral. `index.json` pins each canonical manifest digest and the raw
PVGIS snapshot byte digest.

The energy PV profile maps pinned PVGIS-ERA5 2023 hourly output onto the 2024
UTC calendar. Each synthetic February 29 value is the mean of the corresponding
February 28 and March 1 source hours. This is a deterministic reference fixture,
not observed 2024 production or a site forecast.

Rebuild from an already pinned source snapshot with:

```text
uv run --frozen python -m tools.build_fixtures path/to/pvgis-source.json
```
