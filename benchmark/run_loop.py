"""Run the 30-case benchmark loop with real LLM calls."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from benchmark.extract import extract_plan
from benchmark.generate import write_datasets
from benchmark.llm_runner import LLMConfig, LLMConfigError, solve_with_llm
from benchmark.pipeline import (
    PipelineResult,
    aggregate_pipeline_results,
    pipeline_case_summary,
    run_pipeline,
    validate_mitigation_plan,
)
from benchmark.reference_solver import build_reference_plan


def _load_dotenv() -> None:
    import os

    candidates = [
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path.cwd() / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        try:
            from dotenv import load_dotenv

            load_dotenv(env_path, override=True)
        except ImportError:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")
        return


def resolve_data_dir(base: Path | None = None, seed: int = 42) -> Path:
    root = base or Path(__file__).parent
    if seed == 42:
        return root / "data"
    return root / "data" / f"seed_{seed}"


def _response_path(data_dir: Path, set_name: str, case_id: str) -> Path:
    return data_dir / "responses" / set_name / f"{case_id}.json"


def _load_or_run_raw(
    *,
    data_dir: Path,
    set_name: str,
    prompt_item: dict[str, Any],
    case: dict[str, Any],
    tool_enabled: bool,
    config: LLMConfig | None,
    use_cache: bool,
) -> dict[str, Any]:
    path = _response_path(data_dir, set_name, prompt_item["case_id"])
    if use_cache and path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if "raw" in cached:
            print(f"  [{set_name}] {prompt_item['case_id']} (cache)", flush=True)
            return cached["raw"]
        if "plan" in cached:
            print(f"  [{set_name}] {prompt_item['case_id']} (cache)", flush=True)
            return cached["plan"]

    print(f"  [{set_name}] {prompt_item['case_id']} (api)...", flush=True)
    raw = solve_with_llm(
        prompt_item["prompt"],
        case,
        tool_enabled=tool_enabled,
        config=config,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "case_id": prompt_item["case_id"],
                "tool_enabled": tool_enabled,
                "prompt": prompt_item["prompt"],
                "raw": raw,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return raw


def _reference_pipeline(case: dict[str, Any]) -> PipelineResult:
    raw = build_reference_plan(case)
    extraction = extract_plan(raw, case)
    assert extraction.ok and extraction.plan is not None
    compliance = validate_mitigation_plan(case, extraction.plan)
    return PipelineResult(
        case_id=case["id"],
        raw=raw,
        extraction=extraction,
        compliance=compliance,
    )


def run_loop(
    data_dir: Path | None = None,
    count: int = 30,
    seed: int = 42,
    *,
    mode: str = "llm",
    limit: int | None = None,
    use_cache: bool = True,
    config: LLMConfig | None = None,
    sets: str = "both",
) -> dict[str, Any]:
    _load_dotenv()
    data_dir = data_dir or resolve_data_dir(seed=seed)
    write_datasets(data_dir, count=count, seed=seed)

    variations = json.loads((data_dir / "variations.json").read_text(encoding="utf-8"))
    no_tool_prompts = json.loads((data_dir / "set_no_tool.json").read_text(encoding="utf-8"))
    with_tool_prompts = json.loads((data_dir / "set_with_tool.json").read_text(encoding="utf-8"))

    if limit is not None:
        variations = variations[:limit]
        no_tool_prompts = no_tool_prompts[:limit]
        with_tool_prompts = with_tool_prompts[:limit]

    case_by_id = {case["id"]: case for case in variations}

    if mode == "llm":
        config = config or LLMConfig.from_env()

    no_tool_results: list[PipelineResult] = []
    with_tool_results: list[PipelineResult] = []

    run_no_tool = sets in ("both", "no_tool")
    run_with_tool = sets in ("both", "with_tool")
    print(
        f"Benchmark: {len(variations)} cases, seed={seed}, sets={sets}, "
        f"cache={'on' if use_cache else 'off'}",
        flush=True,
    )

    if run_no_tool:
        for prompt_item in no_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            if mode == "reference":
                no_tool_results.append(_reference_pipeline(case))
            else:
                raw = _load_or_run_raw(
                    data_dir=data_dir,
                    set_name="no_tool",
                    prompt_item=prompt_item,
                    case=case,
                    tool_enabled=False,
                    config=config,
                    use_cache=use_cache,
                )
                no_tool_results.append(run_pipeline(case, raw))

    if run_with_tool:
        for prompt_item in with_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            if mode == "reference":
                with_tool_results.append(_reference_pipeline(case))
            else:
                raw = _load_or_run_raw(
                    data_dir=data_dir,
                    set_name="with_tool",
                    prompt_item=prompt_item,
                    case=case,
                    tool_enabled=True,
                    config=config,
                    use_cache=use_cache,
                )
                with_tool_results.append(run_pipeline(case, raw))

    if not run_no_tool and mode == "llm":
        for prompt_item in no_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            raw = _load_or_run_raw(
                data_dir=data_dir,
                set_name="no_tool",
                prompt_item=prompt_item,
                case=case,
                tool_enabled=False,
                config=config,
                use_cache=True,
            )
            no_tool_results.append(run_pipeline(case, raw))

    if not run_with_tool and mode == "llm":
        for prompt_item in with_tool_prompts:
            case = case_by_id[prompt_item["case_id"]]
            path = _response_path(data_dir, "with_tool", prompt_item["case_id"])
            if not path.exists():
                continue
            raw = _load_or_run_raw(
                data_dir=data_dir,
                set_name="with_tool",
                prompt_item=prompt_item,
                case=case,
                tool_enabled=True,
                config=config,
                use_cache=True,
            )
            with_tool_results.append(run_pipeline(case, raw))

    no_tool_summary = (
        aggregate_pipeline_results(no_tool_results)
        if no_tool_results
        else {"cases": 0, "extraction_success_rate_pct": 0.0, "avg_compliance_pct": 0.0, "full_pass_rate_pct": 0.0}
    )
    with_tool_summary = (
        aggregate_pipeline_results(with_tool_results)
        if with_tool_results
        else {"cases": 0, "extraction_success_rate_pct": 0.0, "avg_compliance_pct": 0.0, "full_pass_rate_pct": 0.0}
    )

    results = {
        "mode": mode,
        "model": config.model if config else None,
        "provider": config.provider if config else None,
        "variations": len(variations),
        "seed": seed,
        "max_tool_rounds": config.max_tool_rounds if config else None,
        "max_repair_rounds": int(__import__("os").getenv("BENCHMARK_MAX_REPAIR_ROUNDS", "1")),
        "architecture": "llm_output -> extract_plan -> validate_plan",
        "no_tool": no_tool_summary,
        "with_tool": with_tool_summary,
        "delta_avg_compliance_pct": round(
            with_tool_summary["avg_compliance_pct"] - no_tool_summary["avg_compliance_pct"],
            2,
        ),
        "delta_full_pass_rate_pct": round(
            with_tool_summary["full_pass_rate_pct"] - no_tool_summary["full_pass_rate_pct"],
            2,
        ),
        "delta_extraction_success_rate_pct": round(
            with_tool_summary["extraction_success_rate_pct"]
            - no_tool_summary["extraction_success_rate_pct"],
            2,
        ),
        "cases_no_tool": [pipeline_case_summary(result) for result in no_tool_results],
        "cases_with_tool": [pipeline_case_summary(result) for result in with_tool_results],
    }

    (data_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mitigation-plan LLM benchmark")
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--limit", type=int, default=None, help="Run first N cases only")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--mode",
        choices=["llm", "reference"],
        default="llm",
        help="llm=real API calls (default); reference=deterministic plans for tests",
    )
    parser.add_argument("--no-cache", action="store_true", help="Ignore cached LLM responses")
    parser.add_argument(
        "--set",
        dest="sets",
        choices=["both", "no_tool", "with_tool"],
        default="both",
        help="Which prompt set to run (default: both)",
    )
    args = parser.parse_args()

    try:
        results = run_loop(
            count=args.count,
            seed=args.seed,
            mode=args.mode,
            limit=args.limit,
            use_cache=not args.no_cache,
            sets=args.sets,
        )
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        print()
        print("Setup:")
        print('  pip install -e ".[benchmark]"')
        print("  copy .env.example .env")
        print("  python -m benchmark.run_loop --limit 3")
        raise SystemExit(1) from exc

    seed = results["seed"]
    data_path = resolve_data_dir(seed=seed)
    print(f"=== Benchmark ({results['variations']} casos, seed={seed}, mode={results['mode']}) ===")
    print(f"Pipeline: {results['architecture']}")
    if results.get("model"):
        print(f"Model: {results['model']}")
    print()
    if results["no_tool"]["cases"]:
        print("SET sin tool:")
        print(f"  extraction OK: {results['no_tool']['extraction_success_rate_pct']}%")
        print(f"  avg compliance: {results['no_tool']['avg_compliance_pct']}%")
        print(f"  full pass rate: {results['no_tool']['full_pass_rate_pct']}%")
        print()
    if results["with_tool"]["cases"]:
        print("SET con tool:")
        print(f"  extraction OK: {results['with_tool']['extraction_success_rate_pct']}%")
        print(f"  avg compliance: {results['with_tool']['avg_compliance_pct']}%")
        print(f"  full pass rate: {results['with_tool']['full_pass_rate_pct']}%")
        print()
    if results["no_tool"]["cases"] and results["with_tool"]["cases"]:
        print(f"Delta extraction OK: {results['delta_extraction_success_rate_pct']:+.2f} pp")
        print(f"Delta avg compliance: {results['delta_avg_compliance_pct']:+.2f} pp")
        print(f"Delta full pass rate: {results['delta_full_pass_rate_pct']:+.2f} pp")
        print()
    print(f"Results: {data_path / 'results.json'}")


if __name__ == "__main__":
    main()
