"""Bounded exhaustive reference optimizer for the shared fixture."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN
from math import floor
from typing import Any

from .canonical import sha256_hex
from .simulation import simulate_raw


def _energy(value: float) -> float:
    return round(value, 6)


def _dimensionless(value: float) -> float:
    return round(value, 9)


def _money_decimal(value: float) -> Decimal:
    return Decimal.from_float(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def _money(value: float) -> float:
    return float(_money_decimal(value))


def _configuration_id(
    pv: dict[str, Any], quantity: int, inverter: dict[str, Any], battery: dict[str, Any] | None, battery_quantity: int
) -> str:
    battery_part = "battery-none"
    if battery is not None:
        battery_part = f"{battery['componentId']}-q{battery_quantity}"
    return f"{pv['componentId']}-q{quantity}-{inverter['componentId']}-{battery_part}"


def optimize_reference(
    request: dict[str, Any], manifest: dict[str, Any], artifacts: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Enumerate the reference fixture under its explicit compatibility rules."""

    catalog = artifacts["component-catalog"]["components"]
    pv_models = sorted(
        (item for item in catalog if item["type"] == "PV_MODULE" and item["available"]),
        key=lambda item: item["componentId"],
    )
    inverters = sorted(
        (item for item in catalog if item["type"] == "INVERTER" and item["available"]),
        key=lambda item: item["componentId"],
    )
    batteries = sorted(
        (item for item in catalog if item["type"] == "BATTERY" and item["available"]),
        key=lambda item: item["componentId"],
    )

    annual_demand = request["site"]["annualDemandKWh"]
    pv_series = artifacts["pv-yield"]["values"]
    load_series = artifacts["reference-load-shape"]["values"]
    import_series = artifacts["import-tariff"]["values"]
    export_series = artifacts["export-tariff"]["values"]
    hours = [
        {
            "start": pv["start"],
            "pvYieldPerKWp": pv["value"],
            "loadKWh": annual_demand * load["value"],
            "importTariffEURPerKWh": import_tariff["value"],
            "exportTariffEURPerKWh": export_tariff["value"],
        }
        for pv, load, import_tariff, export_tariff in zip(
            pv_series, load_series, import_series, export_series, strict=True
        )
    ]

    rate = request["assumptions"]["discountRate"]
    years = request["assumptions"]["analysisYears"]
    capital_recovery_factor = (
        1 / years
        if rate == 0
        else rate * (1 + rate) ** years / ((1 + rate) ** years - 1)
    )
    roof_limit = request["site"]["usableRoofAreaM2"]
    investment_limit = request["constraints"]["maxInitialInvestmentEUR"]
    self_sufficiency_limit = request["constraints"]["minSelfSufficiency"]

    candidates: list[dict[str, Any]] = []
    for pv in pv_models:
        max_quantity = min(100, floor((roof_limit + 1e-9) / pv["areaM2"]))
        for quantity in range(1, max_quantity + 1):
            installed_capacity = pv["ratedPowerKWp"] * quantity
            for inverter in inverters:
                dc_ac_ratio = installed_capacity / inverter["acPowerKW"]
                if dc_ac_ratio < 0.8 - 1e-9 or dc_ac_ratio > 1.5 + 1e-9:
                    continue
                battery_options = [(None, 0)] + [
                    (battery, battery_quantity)
                    for battery in batteries
                    for battery_quantity in range(1, 5)
                ]
                for battery, battery_quantity in battery_options:
                    simulation_input: dict[str, Any] = {
                        "pvCapacityKWp": installed_capacity,
                        "inverterEfficiencyFraction": inverter["efficiencyFraction"],
                        "inverterAcPowerKW": inverter["acPowerKW"],
                        "hours": hours,
                    }
                    if battery is not None:
                        simulation_input["battery"] = {
                            "quantity": battery_quantity,
                            "usableCapacityKWh": battery["usableCapacityKWh"],
                            "maxChargePowerKW": battery["maxChargePowerKW"],
                            "maxDischargePowerKW": battery["maxDischargePowerKW"],
                            "roundTripEfficiencyFraction": battery[
                                "roundTripEfficiencyFraction"
                            ],
                        }
                    raw = simulate_raw(simulation_input, include_hours=False)["totals"]

                    initial_investment = (
                        pv["unitPriceEUR"] * quantity + inverter["unitPriceEUR"]
                    )
                    components = [
                        {
                            "componentId": pv["componentId"],
                            "type": "PV_MODULE",
                            "quantity": quantity,
                            "existing": False,
                        },
                        {
                            "componentId": inverter["componentId"],
                            "type": "INVERTER",
                            "quantity": 1,
                            "existing": False,
                        },
                    ]
                    if battery is not None:
                        initial_investment += battery["unitPriceEUR"] * battery_quantity
                        components.append(
                            {
                                "componentId": battery["componentId"],
                                "type": "BATTERY",
                                "quantity": battery_quantity,
                                "existing": False,
                            }
                        )
                    annualized_cost = (
                        initial_investment * capital_recovery_factor
                        + raw["netGridCostEUR"]
                    )
                    investment_passes = initial_investment <= investment_limit + 1e-9
                    sufficiency_passes = (
                        raw["selfSufficiency"] >= self_sufficiency_limit - 1e-9
                    )
                    configuration_id = _configuration_id(
                        pv, quantity, inverter, battery, battery_quantity
                    )
                    candidates.append(
                        {
                            "schemaVersion": "energy-candidate/v1",
                            "configurationId": configuration_id,
                            "components": components,
                            "feasible": investment_passes and sufficiency_passes,
                            "constraints": [
                                {
                                    "code": "roof_area",
                                    "status": "PASS",
                                    "actual": _energy(pv["areaM2"] * quantity),
                                    "limit": roof_limit,
                                    "unit": "m2",
                                },
                                {
                                    "code": "dc_ac_ratio",
                                    "status": "PASS",
                                    "actual": _dimensionless(dc_ac_ratio),
                                    "limit": "0.8..1.5",
                                },
                                {
                                    "code": "max_initial_investment",
                                    "status": "PASS" if investment_passes else "FAIL",
                                    "actual": _money(initial_investment),
                                    "limit": investment_limit,
                                    "unit": "EUR",
                                },
                                {
                                    "code": "min_self_sufficiency",
                                    "status": "PASS" if sufficiency_passes else "FAIL",
                                    "actual": _dimensionless(raw["selfSufficiency"]),
                                    "limit": self_sufficiency_limit,
                                },
                            ],
                            "metrics": {
                                "initialInvestmentEUR": _money(initial_investment),
                                "annualizedCostEUR": _money(annualized_cost),
                                "selfSufficiency": _dimensionless(raw["selfSufficiency"]),
                                "annualDemandKWh": _energy(raw["annualDemandKWh"]),
                                "gridImportKWh": _energy(raw["gridImportKWh"]),
                                "gridExportKWh": _energy(raw["gridExportKWh"]),
                                "onSiteSolarUseKWh": _energy(raw["onSiteSolarUseKWh"]),
                                "unmetDemandKWh": _energy(raw["unmetDemandKWh"]),
                                "inverterClippingKWh": _energy(
                                    raw["inverterClippingKWh"]
                                ),
                                "terminalDiscardedEnergyKWh": _energy(
                                    raw["terminalDiscardedEnergyKWh"]
                                ),
                            },
                        }
                    )

    candidates.sort(key=lambda item: item["configurationId"])
    feasible = [item for item in candidates if item["feasible"]]
    ranking = sorted(
        feasible,
        key=lambda item: (
            _money_decimal(item["metrics"]["annualizedCostEUR"]),
            _money_decimal(item["metrics"]["initialInvestmentEUR"]),
            item["configurationId"],
        ),
    )
    recommendation = ranking[0]["configurationId"] if ranking else None
    result = {
        "schemaVersion": "energy-optimization-result/v1",
        "runId": "run-reference-0001",
        "status": "SUCCEEDED" if ranking else "INFEASIBLE",
        "dataset": {
            "datasetId": manifest["datasetId"],
            "version": manifest["version"],
            "schemaRef": manifest["schemaRef"],
            "manifestSha256": sha256_hex(manifest),
        },
        "modelVersion": "energy-model/1.0.0",
        "simulationVersion": "energy-simulation/1.0.0",
        "optimizerVersion": "energy-optimizer/1.0.0",
        "optimalityStatus": "PROVEN_OPTIMAL" if ranking else "NOT_APPLICABLE",
        "evaluatedCandidateCount": len(candidates),
        "feasibleCandidateCount": len(feasible),
        "recommendedConfigurationId": recommendation,
        "warnings": manifest["quality"]["warnings"],
        "createdAt": "2026-10-10T00:00:00Z",
        "completedAt": "2026-10-10T00:00:01Z",
    }
    return {
        "rules": {
            "pvQuantity": "1..min(100, floor(usableRoofAreaM2 / moduleAreaM2))",
            "dcAcRatio": {"minimum": 0.8, "maximum": 1.5},
            "inverterQuantity": 1,
            "batteryQuantity": "0 or 1..4 of one battery model",
            "ranking": "annualized cost cents, initial investment cents, configuration ID",
        },
        "request": request,
        "candidates": candidates,
        "ranking": [item["configurationId"] for item in ranking],
        "result": result,
    }
