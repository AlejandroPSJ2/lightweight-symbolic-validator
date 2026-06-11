"""Run the 30-case letter-count benchmark (with / without tool)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmark.llm_runner import LLMConfig, LLMConfigError
from benchmark.letters.evaluate import aggregate_results, evaluate_answer
from benchmark.letters.generate import Profile, resolve_data_dir, write_datasets
from benchmark.letters.llm_runner import _letters_pre_inject_tool, solve_letter_with_llm
from benchmark.run_loop import _load_dotenv


def _response_path(data_dir: Path, set_name: str, case_id: str) -> Path:
    return data_dir / "responses" / set_name / f"{case_id}.txt"


def _load_or_run(
    *,
    data_dir: Path,
    set_name: str,
    prompt_item: dict[str, Any],
    config: LLMConfig,
    use_cache: bool,
) -> str:
    path = _response_path(data_dir, set_name, prompt_item["case_id"])
    if use_cache and path.exists():
        print(f"  [{set_name}] {prompt_item['case_id']} (cache)", flush=True)
        return path.read_text(encoding="utf-8")

    print(f"  [{set_name}] {prompt_item['case_id']} (api)...", flush=True)
    try:
        raw = solve_letter_with_llm(
            prompt_item["prompt"],
            tool_enabled=prompt_item["tool_enabled"],
            config=config,
            case_input=prompt_item.get("input"),
        )
    except RuntimeError as exc:
        raw = f"ERROR: {exc}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw, encoding="utf-8")
    return raw


def run_loop(
    data_dir: Path | None = None,
    *,
    count: int = 30,
    seed: int = 42,
    profile: Profile = "random",
    limit: int | None = None,
    use_cache: bool = True,
    config: LLMConfig | None = None,
    sets: str = "both",
) -> dict[str, Any]:
    _load_dotenv()
    data_dir = data_dir or resolve_data_dir(seed=seed, profile=profile)
    write_datasets(data_dir, count=count, seed=seed, profile=profile)
    config = config or LLMConfig.from_env()

    cases = json.loads((data_dir / "cases.json").read_text(encoding="utf-8"))
    no_tool_prompts = json.loads((data_dir / "set_no_tool.json").read_text(encoding="utf-8"))
    with_tool_prompts = json.loads((data_dir / "set_with_tool.json").read_text(encoding="utf-8"))

    if limit is not None:
        case_ids = {case["id"] for case in cases[:limit]}
        cases = cases[:limit]
        no_tool_prompts = [item for item in no_tool_prompts if item["case_id"] in case_ids]
        with_tool_prompts = [item for item in with_tool_prompts if item["case_id"] in case_ids]

    case_by_id = {case["id"]: case for case in cases}
    run_no_tool = sets in ("both", "no_tool")
    run_with_tool = sets in ("both", "with_tool")

    pre_inject = _letters_pre_inject_tool()
    print(
        f"Letters: {len(cases)} cases, profile={profile}, seed={seed}, sets={sets}, "
        f"pre_inject={pre_inject}, cache={'on' if use_cache else 'off'}",
        flush=True,
    )

    no_tool_results: list[dict[str, Any]] = []
    if run_no_tool:
        for prompt_item in no_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            raw = _load_or_run(
                data_dir=data_dir,
                set_name="no_tool",
                prompt_item=prompt_item,
                config=config,
                use_cache=use_cache,
            )
            no_tool_results.append(evaluate_answer(case, raw))

    with_tool_results: list[dict[str, Any]] = []
    if run_with_tool:
        for prompt_item in with_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            raw = _load_or_run(
                data_dir=data_dir,
                set_name="with_tool",
                prompt_item=prompt_item,
                config=config,
                use_cache=use_cache,
            )
            with_tool_results.append(evaluate_answer(case, raw))

    if not run_no_tool:
        for prompt_item in no_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            raw = _load_or_run(
                data_dir=data_dir,
                set_name="no_tool",
                prompt_item=prompt_item,
                config=config,
                use_cache=True,
            )
            no_tool_results.append(evaluate_answer(case, raw))

    no_tool_summary = (
        aggregate_results(no_tool_results)
        if no_tool_results
        else {"cases": 0, "correct": 0, "accuracy_pct": 0.0}
    )
    with_tool_summary = (
        aggregate_results(with_tool_results)
        if with_tool_results
        else {"cases": 0, "correct": 0, "accuracy_pct": 0.0}
    )

    results = {
        "suite": "letters",
        "profile": profile,
        "seed": seed if profile == "random" else None,
        "letters_pre_inject_tool": _letters_pre_inject_tool(),
        "model": config.model,
        "provider": config.provider,
        "cases": len(cases),
        "no_tool": no_tool_summary,
        "with_tool": with_tool_summary,
        "delta_accuracy_pct": round(
            with_tool_summary["accuracy_pct"] - no_tool_summary["accuracy_pct"],
            2,
        ),
        "cases_no_tool": no_tool_results,
        "cases_with_tool": with_tool_results,
    }

    (data_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run letter-count LLM benchmark")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--profile",
        choices=["random", "hard"],
        default="random",
        help="random=seeded sample; hard=fixed 30 tricky/misspelled words",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument(
        "--set",
        dest="sets",
        choices=["both", "no_tool", "with_tool"],
        default="both",
    )
    args = parser.parse_args()

    try:
        results = run_loop(
            count=args.count,
            seed=args.seed,
            profile=args.profile,
            limit=args.limit,
            use_cache=not args.no_cache,
            sets=args.sets,
        )
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    profile = results.get("profile", "random")
    data_path = resolve_data_dir(seed=results.get("seed") or 42, profile=profile)
    seed_suffix = f", seed={results['seed']}" if results.get("seed") is not None else ""
    print(f"=== Benchmark palabras ({results['cases']} casos, profile={profile}{seed_suffix}) ===")
    if results.get("model"):
        print(f"Model: {results['model']}")
    print()
    if results["no_tool"]["cases"]:
        print(
            f"Sin tool:  {results['no_tool']['accuracy_pct']}% "
            f"({results['no_tool']['correct']}/{results['no_tool']['cases']})"
        )
    if results["with_tool"]["cases"]:
        print(
            f"Con tool:  {results['with_tool']['accuracy_pct']}% "
            f"({results['with_tool']['correct']}/{results['with_tool']['cases']})"
        )
    if results["no_tool"]["cases"] and results["with_tool"]["cases"]:
        print(f"Delta:     {results['delta_accuracy_pct']:+.2f} pp")
    print()
    print(f"Results: {data_path / 'results.json'}")


if __name__ == "__main__":
    main()
