"""Run letter + audit benchmarks and print combined summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmark.letters.run_loop import run_loop as run_letters
from benchmark.llm_runner import LLMConfigError
from benchmark.run_loop import run_loop as run_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run both benchmark suites")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    use_cache = not args.no_cache
    try:
        letters = run_letters(limit=args.limit, use_cache=use_cache)
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    try:
        audit = run_audit(count=args.limit or 30, limit=args.limit, use_cache=use_cache)
    except LLMConfigError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1) from exc

    combined = {
        "letters": letters,
        "audit": audit,
    }
    out = Path(__file__).parent / "data" / "combined_results.json"
    out.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 60)
    print("RESUMEN COMBINADO")
    print("=" * 60)
    print()
    print("PALABRAS (30 casos — conteo de letras)")
    print(f"  Sin tool:  {letters['no_tool']['accuracy_pct']}%")
    print(f"  Con tool:  {letters['with_tool']['accuracy_pct']}%")
    print(f"  Delta:     {letters['delta_accuracy_pct']:+.2f} pp")
    print()
    print("AUDITORÍA (30 casos — plan de mitigación, 6 reglas)")
    print(f"  Sin tool:  extracción {audit['no_tool']['extraction_success_rate_pct']}% | cumplimiento {audit['no_tool']['avg_compliance_pct']}% | full pass {audit['no_tool']['full_pass_rate_pct']}%")
    print(f"  Con tool:  extracción {audit['with_tool']['extraction_success_rate_pct']}% | cumplimiento {audit['with_tool']['avg_compliance_pct']}% | full pass {audit['with_tool']['full_pass_rate_pct']}%")
    print(f"  Delta cumplimiento: {audit['delta_avg_compliance_pct']:+.2f} pp")
    print()
    print(f"Combined: {out}")


if __name__ == "__main__":
    main()
