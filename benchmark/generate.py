"""Generate 30 seeded variations of the mitigation-plan benchmark."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"

RISK_NAMES = [
    "Pérdida de órdenes históricas",
    "Corrupción de catálogo de productos",
    "Desalineación de jerarquías comerciales",
    "Errores de transformación ETL",
    "Duplicidad de clientes",
    "Fallo en reconciliación financiera",
    "Latencia excesiva en dashboards",
    "Pérdida de trazabilidad de inventario",
    "Fallo de sincronización con SAP",
    "Inconsistencia de precios",
    "Brecha de calidad en master data",
    "Retraso en cierre contable",
]

CONTROL_NAMES = [
    "Backup completo",
    "Validación automática",
    "Pruebas piloto",
    "Monitoreo en tiempo real",
    "Rollback automatizado",
    "Data profiling",
    "Auditoría financiera",
    "Validación de inventario",
    "Control de acceso temporal",
    "Reconciliación cruzada",
    "Catálogo de reglas de negocio",
]

DEP_NAMES = [
    "SAP Product Master",
    "SAP Orders",
    "SAP Customers",
    "Snowflake Landing Zone",
    "ETL Pipelines",
    "Finance Data Mart",
    "Inventory Service",
    "QA Environment",
    "Monitoring Platform",
    "Pricing Engine",
    "Identity Provider",
]

OWNER_POOL = [
    "Ana",
    "Luis",
    "Carlos",
    "Maria",
    "Pedro",
    "Sofia",
    "Jorge",
    "Elena",
    "Miguel",
    "Laura",
    "Tomás",
    "Beatriz",
    "Felipe",
    "Lucía",
    "Renata",
    "Camila",
    "Diego",
    "Pablo",
    "Sara",
    "Iván",
]

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM"]
RULES = [
    "Todo riesgo crítico debe tener al menos un control.",
    "Ningún control puede existir sin estar asociado a algún riesgo.",
    "Ningún owner puede ser responsable de más de un riesgo.",
    "Toda dependencia debe estar asociada a al menos un riesgo.",
    "Todo riesgo debe tener al menos una dependencia.",
    "Todo riesgo debe tener al menos un owner.",
]


def _pick(pool: list[str], count: int, rng: random.Random) -> list[str]:
    return rng.sample(pool, count)


def generate_variation(index: int, rng: random.Random) -> dict[str, Any]:
    risk_count = rng.randint(8, 12)
    control_count = rng.randint(6, 10)
    dep_count = rng.randint(6, 10)

    owners = _pick(OWNER_POOL, risk_count, rng)
    if rng.random() < 0.45:
        duplicate_at = rng.randint(0, risk_count - 1)
        owners[duplicate_at] = owners[(duplicate_at + 1) % risk_count]

    risks = []
    for i in range(risk_count):
        severity = rng.choices(SEVERITIES, weights=[0.35, 0.4, 0.25])[0]
        risks.append(
            {
                "id": f"R{i + 1}",
                "name": RISK_NAMES[i % len(RISK_NAMES)],
                "severity": severity,
                "owner": owners[i],
            }
        )

    controls = [
        {"id": f"C{i + 1}", "name": CONTROL_NAMES[i % len(CONTROL_NAMES)]}
        for i in range(control_count)
    ]
    dependencies = [
        {"id": f"D{i + 1}", "name": DEP_NAMES[i % len(DEP_NAMES)]}
        for i in range(dep_count)
    ]

    return {
        "id": f"var_{index:03d}",
        "seed": index,
        "rules": RULES,
        "risks": risks,
        "controls": controls,
        "dependencies": dependencies,
    }


def generate_all(count: int = 30, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    return [generate_variation(i + 1, rng) for i in range(count)]


def build_prompt(case: dict[str, Any], tool_enabled: bool) -> str:
    tool_line = (
        "Tienes acceso a DiscreteStructureTool y validate_mitigation_plan. "
        "Valida antes de responder. Si falla, corrige solo usando failed_checks.witness "
        "y vuelve a validar hasta all_passed."
        if tool_enabled
        else "Responde solo con razonamiento propio; NO uses DiscreteStructureTool ni código externo."
    )
    return (
        f"Caso {case['id']}. Diseña un plan de mitigación cumpliendo estas reglas:\n"
        + "\n".join(f"{i + 1}. {rule}" for i, rule in enumerate(case["rules"]))
        + "\n\n"
        + f"Riesgos: {json.dumps(case['risks'], ensure_ascii=False)}\n"
        + f"Controles: {json.dumps(case['controls'], ensure_ascii=False)}\n"
        + f"Dependencias: {json.dumps(case['dependencies'], ensure_ascii=False)}\n\n"
        + "Devuelve JSON con: risk_owners, risk_controls, risk_dependencies.\n"
        + tool_line
    )


def build_test_sets(variations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    no_tool: list[dict[str, Any]] = []
    with_tool: list[dict[str, Any]] = []
    for case in variations:
        no_tool.append(
            {
                "case_id": case["id"],
                "tool_enabled": False,
                "prompt": build_prompt(case, tool_enabled=False),
                "input": {
                    "risks": case["risks"],
                    "controls": case["controls"],
                    "dependencies": case["dependencies"],
                },
            }
        )
        with_tool.append(
            {
                "case_id": case["id"],
                "tool_enabled": True,
                "prompt": build_prompt(case, tool_enabled=True),
                "input": {
                    "risks": case["risks"],
                    "controls": case["controls"],
                    "dependencies": case["dependencies"],
                },
            }
        )
    return no_tool, with_tool


def write_datasets(
    output_dir: Path | None = None,
    count: int = 30,
    seed: int = 42,
) -> Path:
    output_dir = output_dir or DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    variations = generate_all(count=count, seed=seed)
    no_tool, with_tool = build_test_sets(variations)

    (output_dir / "variations.json").write_text(
        json.dumps(variations, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "set_no_tool.json").write_text(
        json.dumps(no_tool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output_dir / "set_with_tool.json").write_text(
        json.dumps(with_tool, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return output_dir


if __name__ == "__main__":
    path = write_datasets()
    print(f"Wrote 30 variations and 2 test sets to {path}")
