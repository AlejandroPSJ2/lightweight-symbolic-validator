"""Generate seeded letter-count benchmark cases."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Literal

DATA_DIR = Path(__file__).parent / "data"
Profile = Literal["random", "hard"]

WORD_POOL = [
    "strawberry",
    "bookkeeper",
    "Mississippi",
    "possession",
    "parallel",
    "assess",
    "accommodation",
    "occurrence",
    "embarrassment",
    "success",
    "referring",
    "blackberry",
    "aggressive",
    "perseverance",
    "assassination",
    "committee",
    "millennium",
    "liaison",
    "rhythm",
    "bureaucracy",
    "abbreviation",
    "bookkeeping",
    "repertoire",
    "eccentricity",
    "uncopyrightable",
    "flibbertigibbet",
    "appalling",
    "misspell",
    "questionnaire",
    "entrepreneur",
    "conscientious",
    "supersede",
    "dumbbell",
    "occasionally",
    "maintenance",
    "pronunciation",
    "recommend",
    "separate",
    "definitely",
    "occurred",
    "argument",
    "surprise",
    "tomorrow",
    "calendar",
    "address",
    "grammar",
    "library",
    "February",
    "Wednesday",
    "necessary",
]

# Curated traps: complex spelling, double letters, and common misspellings.
# Ground truth counts the literal string given to the model (and the tool).
HARD_CASE_SPECS: list[tuple[str, str, str]] = [
    ("strawberry", "r", "trampa clásica: 3 r separadas"),
    ("bookkeeper", "e", "tres e, doble k"),
    ("Mississippi", "s", "cuatro s"),
    ("Mississippi", "p", "dos p"),
    ("accommodation", "c", "doble c correcta"),
    ("accomodation", "c", "ortografía errónea: falta una m"),
    ("occurrence", "r", "doble c, doble r"),
    ("ocurrence", "r", "ortografía errónea: falta una c"),
    ("embarrassment", "r", "doble r, doble s"),
    ("embarassment", "r", "ortografía errónea: una s de menos"),
    ("rhythm", "h", "sin vocal entre h"),
    ("rhythm", "y", "y como única vocal aparente"),
    ("dumbbell", "b", "doble b, doble l"),
    ("dumbell", "b", "ortografía errónea: falta una b"),
    ("conscientious", "s", "s dispersas"),
    ("conscience", "c", "tres c"),
    ("questionnaire", "n", "doble n"),
    ("flibbertigibbet", "b", "cuatro b"),
    ("uncopyrightable", "i", "una sola i"),
    ("supersede", "e", "tres e"),
    ("recommend", "m", "doble m"),
    ("seise", "e", "doble e en forma arcaica"),
    ("balloon", "l", "doble l, doble o"),
    ("baloon", "l", "ortografía errónea: un l de menos"),
    ("liaison", "i", "tres i"),
    ("liason", "i", "ortografía errónea: falta una i"),
    ("address", "d", "doble d"),
    ("addres", "d", "ortografía errónea: falta una d"),
    ("mississippi", "s", "minúsculas, cuatro s"),
    ("occassion", "s", "ortografía errónea: doble s extra"),
]


def _letter_positions(word: str, target: str) -> list[int]:
    return [i for i, ch in enumerate(word) if ch.lower() == target.lower()]


def _build_case(index: int, word: str, target: str, note: str = "") -> dict[str, Any]:
    positions = _letter_positions(word, target)
    case: dict[str, Any] = {
        "id": f"letter_{index:03d}",
        "word": word,
        "target": target,
        "expected_count": len(positions),
        "expected_positions": positions,
    }
    if note:
        case["note"] = note
    return case


def generate_case(index: int, rng: random.Random, seen: set[tuple[str, str]]) -> dict[str, Any]:
    for _ in range(200):
        word = rng.choice(WORD_POOL)
        letters = sorted({ch.lower() for ch in word if ch.isalpha()})
        target = rng.choice(letters)
        key = (word.lower(), target)
        if key in seen:
            continue
        positions = _letter_positions(word, target)
        if len(positions) < 1:
            continue
        seen.add(key)
        return _build_case(index, word, target)
    raise RuntimeError(f"Could not generate unique letter case at index {index}")


def generate_all(count: int = 30, seed: int = 42) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    seen: set[tuple[str, str]] = set()
    return [generate_case(i + 1, rng, seen) for i in range(count)]


def generate_hard_cases() -> list[dict[str, Any]]:
    return [
        _build_case(index, word, target, note)
        for index, (word, target, note) in enumerate(HARD_CASE_SPECS, start=1)
    ]


def build_prompt(case: dict[str, Any], tool_enabled: bool) -> str:
    tool_line = (
        "Tienes acceso a DiscreteStructureTool (frequency). "
        "Úsalo para contar con precisión. Responde SOLO con un número entero."
        if tool_enabled
        else "Responde SOLO con razonamiento propio. NO uses herramientas ni código. "
        "Responde SOLO con un número entero."
    )
    return (
        f'¿Cuántas veces aparece la letra "{case["target"]}" en la palabra "{case["word"]}"?\n'
        f"{tool_line}"
    )


def build_test_sets(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    no_tool: list[dict[str, Any]] = []
    with_tool: list[dict[str, Any]] = []
    for case in cases:
        base = {
            "case_id": case["id"],
            "prompt": "",
            "input": {"word": case["word"], "target": case["target"]},
        }
        no_tool.append(
            {
                **base,
                "tool_enabled": False,
                "prompt": build_prompt(case, tool_enabled=False),
            }
        )
        with_tool.append(
            {
                **base,
                "tool_enabled": True,
                "prompt": build_prompt(case, tool_enabled=True),
            }
        )
    return no_tool, with_tool


def resolve_data_dir(
    base: Path | None = None,
    *,
    seed: int = 42,
    profile: Profile = "random",
) -> Path:
    root = base or Path(__file__).parent
    if profile == "hard":
        return root / "data" / "hard"
    if seed == 42:
        return root / "data"
    return root / "data" / f"seed_{seed}"


def write_datasets(
    output_dir: Path | None = None,
    count: int = 30,
    seed: int = 42,
    profile: Profile = "random",
) -> Path:
    if profile == "hard":
        cases = generate_hard_cases()
        output_dir = output_dir or resolve_data_dir(profile="hard")
    else:
        cases = generate_all(count=count, seed=seed)
        output_dir = output_dir or resolve_data_dir(seed=seed, profile="random")

    output_dir.mkdir(parents=True, exist_ok=True)
    no_tool, with_tool = build_test_sets(cases)

    (output_dir / "cases.json").write_text(
        json.dumps(cases, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "set_no_tool.json").write_text(
        json.dumps(no_tool, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "set_with_tool.json").write_text(
        json.dumps(with_tool, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "meta.json").write_text(
        json.dumps(
            {
                "profile": profile,
                "seed": seed if profile == "random" else None,
                "cases": len(cases),
                "description": (
                    "30 casos difíciles: palabras complejas y ortografías erróneas. "
                    "El conteo es sobre la cadena literal."
                    if profile == "hard"
                    else "30 casos aleatorios por seed."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate letter-count benchmark datasets")
    parser.add_argument("--profile", choices=["random", "hard"], default="hard")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=30)
    args = parser.parse_args()
    path = write_datasets(count=args.count, seed=args.seed, profile=args.profile)
    print(f"Wrote letter benchmark to {path}")
