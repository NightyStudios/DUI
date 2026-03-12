from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.main import build_dsl_transform


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform DUI DSL text with a natural-language prompt.")
    parser.add_argument("--source-file", required=True, help="Path to the current DSL source file")
    parser.add_argument("--prompt", required=True, help="User request to apply to the DSL")
    parser.add_argument("--surface-id", default=None, help="Optional surface id override")
    parser.add_argument("--mode", choices=["safe", "extended", "experimental"], default="extended")
    args = parser.parse_args()

    source_text = Path(args.source_file).read_text(encoding="utf-8")
    response = build_dsl_transform(
        source_text=source_text,
        user_prompt=args.prompt,
        surface_id=args.surface_id,
        mode=args.mode,
    )
    print(response.source_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
