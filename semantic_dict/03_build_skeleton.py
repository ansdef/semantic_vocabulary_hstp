"""Этап 3: строит 03_alias_phrases_skeleton.json"""
import json
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).parent
ALIAS_PATH = BASE / "01_indicator_alias.json"
INDEX_PATH = BASE / "02_indicator_index.json"
OUT_PATH = BASE / "03_alias_phrases_skeleton.json"


def main():
    aliases = json.loads(ALIAS_PATH.read_text(encoding="utf-8"))
    index_records = json.loads(INDEX_PATH.read_text(encoding="utf-8"))

    indicator_indices: dict[str, list[str]] = defaultdict(list)
    for rec in index_records:
        indicator_indices[rec["indicator"]].append(rec["index"])

    result = {}
    for indicator, alias in aliases.items():
        result[indicator] = {
            "alias": alias,
            "indices": indicator_indices.get(indicator, []),
            "phrases": {
                "head": [],
                "news": [],
                "social": [],
                "synonyms": [],
            },
        }

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Скелетов: {len(result)} → {OUT_PATH}")


if __name__ == "__main__":
    main()
