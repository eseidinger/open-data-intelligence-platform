"""Deterministic energy dispatch reference implementation for contract tests."""

from __future__ import annotations

from math import sqrt
from typing import Any


ENERGY_TOLERANCE = 1e-6


def _energy(value: float) -> float:
    return round(value, 6)


def simulate_raw(
    inputs: dict[str, Any], *, include_hours: bool = True
) -> dict[str, Any]:
    """Return unrounded binary64 dispatch values for downstream calculations."""

    hours = inputs["hours"]
    pv_capacity = inputs["pvCapacityKWp"]
    inverter_efficiency = inputs["inverterEfficiencyFraction"]
    inverter_limit = inputs["inverterAcPowerKW"]
    battery = inputs.get("battery")

    if battery is None:
        capacity = charge_limit = discharge_limit = 0.0
        charge_efficiency = discharge_efficiency = 1.0
    else:
        quantity = battery.get("quantity", 1)
        capacity = battery["usableCapacityKWh"] * quantity
        charge_limit = battery["maxChargePowerKW"] * quantity
        discharge_limit = battery["maxDischargePowerKW"] * quantity
        charge_efficiency = discharge_efficiency = sqrt(
            battery["roundTripEfficiencyFraction"]
        )

    state_of_charge = 0.0
    net_grid_cost = 0.0
    has_tariffs = all(
        "importTariffEURPerKWh" in item and "exportTariffEURPerKWh" in item
        for item in hours
    )
    result_hours: list[dict[str, Any]] = []
    totals = {
        "pvDcKWh": 0.0,
        "pvAcKWh": 0.0,
        "annualDemandKWh": 0.0,
        "gridImportKWh": 0.0,
        "gridExportKWh": 0.0,
        "onSiteSolarUseKWh": 0.0,
        "batteryChargeAcKWh": 0.0,
        "batteryDischargeAcKWh": 0.0,
        "inverterClippingKWh": 0.0,
        "unmetDemandKWh": 0.0,
    }

    for item in hours:
        pv_dc = pv_capacity * item["pvYieldPerKWp"]
        potential_ac = pv_dc * inverter_efficiency
        pv_ac = min(potential_ac, inverter_limit)
        clipping = max(0.0, potential_ac - inverter_limit)
        load = item["loadKWh"]
        direct_solar = min(pv_ac, load)
        surplus = pv_ac - direct_solar
        deficit = load - direct_solar

        charge = min(
            surplus,
            charge_limit,
            max(0.0, capacity - state_of_charge) / charge_efficiency,
        )
        state_of_charge += charge * charge_efficiency
        export = surplus - charge

        discharge = min(
            deficit,
            discharge_limit,
            state_of_charge * discharge_efficiency,
        )
        state_of_charge -= discharge / discharge_efficiency
        grid_import = deficit - discharge
        if has_tariffs:
            net_grid_cost += (
                grid_import * item["importTariffEURPerKWh"]
                - export * item["exportTariffEURPerKWh"]
            )

        balance_error = abs(pv_ac + grid_import + discharge - load - charge - export)
        if balance_error > ENERGY_TOLERANCE:
            raise ValueError(f"hourly energy balance error: {balance_error}")
        if state_of_charge < -ENERGY_TOLERANCE or state_of_charge > capacity + ENERGY_TOLERANCE:
            raise ValueError(f"battery state of charge out of bounds: {state_of_charge}")

        if include_hours:
            result_hours.append(
                {
                    "start": item["start"],
                    "pvDcKWh": pv_dc,
                    "pvAcKWh": pv_ac,
                    "loadKWh": load,
                    "directSolarKWh": direct_solar,
                    "batteryChargeAcKWh": charge,
                    "batteryDischargeAcKWh": discharge,
                    "stateOfChargeKWh": state_of_charge,
                    "gridImportKWh": grid_import,
                    "gridExportKWh": export,
                    "inverterClippingKWh": clipping,
                }
            )

        totals["pvDcKWh"] += pv_dc
        totals["pvAcKWh"] += pv_ac
        totals["annualDemandKWh"] += load
        totals["gridImportKWh"] += grid_import
        totals["gridExportKWh"] += export
        totals["onSiteSolarUseKWh"] += direct_solar + discharge
        totals["batteryChargeAcKWh"] += charge
        totals["batteryDischargeAcKWh"] += discharge
        totals["inverterClippingKWh"] += clipping

    demand = totals["annualDemandKWh"]
    self_sufficiency = 1.0 - totals["gridImportKWh"] / demand
    totals["terminalDiscardedEnergyKWh"] = state_of_charge
    totals["selfSufficiency"] = self_sufficiency
    if has_tariffs:
        totals["netGridCostEUR"] = net_grid_cost
    return {"hours": result_hours, "totals": totals}


def simulate(inputs: dict[str, Any]) -> dict[str, Any]:
    """Return the contract representation rounded only after simulation."""

    raw = simulate_raw(inputs)
    hours = [
        {
            key: value if key == "start" else _energy(value)
            for key, value in item.items()
        }
        for item in raw["hours"]
    ]
    totals = {key: _energy(value) for key, value in raw["totals"].items()}
    return {"hours": hours, "totals": totals}
