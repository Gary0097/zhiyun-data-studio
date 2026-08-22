# -*- coding: utf-8 -*-
"""Configurable department metric fusion without hard-coded source columns."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def analyze_department_metrics(records: list[dict[str, Any]], mapping: dict[str, str]) -> dict[str, Any]:
    """Group records and calculate output, labor, cost and loss metrics."""
    required = {"department", "output", "labor_hours"}
    missing = sorted(required - {key for key, value in mapping.items() if value})
    if missing:
        raise ValueError(f"missing metric mappings: {', '.join(missing)}")
    groups: dict[str, dict[str, float]] = defaultdict(lambda: {"output": 0.0, "labor_hours": 0.0, "employee_count": 0.0, "cost": 0.0, "loss": 0.0, "record_count": 0.0})
    invalid_rows = 0
    for row in records:
        department = str(row.get(mapping["department"], "")).strip()
        if not department:
            invalid_rows += 1
            continue
        item = groups[department]
        item["record_count"] += 1
        for metric in ["output", "labor_hours", "employee_count", "cost", "loss"]:
            field = mapping.get(metric)
            if field:
                item[metric] += _number(row.get(field))

    results = []
    for department, item in groups.items():
        output = item["output"]
        hours = item["labor_hours"]
        employees = item["employee_count"]
        results.append({
            "department": department,
            "record_count": int(item["record_count"]),
            "output": round(output, 2),
            "labor_hours": round(hours, 2),
            "employee_count": round(employees, 2),
            "cost": round(item["cost"], 2),
            "loss": round(item["loss"], 2),
            "output_per_hour": round(output / hours, 2) if hours else None,
            "output_per_employee": round(output / employees, 2) if employees else None,
            "cost_per_output": round(item["cost"] / output, 2) if output else None,
            "loss_rate": round(100 * item["loss"] / output, 2) if output else None,
        })
    results.sort(key=lambda item: (-item["output"], item["department"]))
    productivity = [item for item in results if item["output_per_hour"] is not None]
    unit_cost = [item for item in results if item["cost_per_output"] is not None]
    loss_rate = [item for item in results if item["loss_rate"] is not None]
    highlights = {
        "highest_productivity": max(productivity, key=lambda item: item["output_per_hour"])["department"] if productivity else None,
        "lowest_unit_cost": min(unit_cost, key=lambda item: item["cost_per_output"])["department"] if unit_cost else None,
        "lowest_loss_rate": min(loss_rate, key=lambda item: item["loss_rate"])["department"] if loss_rate else None,
    }
    return {
        "summary": {
            "departments": len(results),
            "valid_records": sum(item["record_count"] for item in results),
            "invalid_records": invalid_rows,
            "total_output": round(sum(item["output"] for item in results), 2),
            "total_cost": round(sum(item["cost"] for item in results), 2),
            "total_loss": round(sum(item["loss"] for item in results), 2),
        },
        "mapping": mapping,
        "highlights": highlights,
        "results": results,
    }
