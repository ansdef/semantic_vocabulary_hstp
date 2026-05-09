"""Этап 5: строит 05_indicator_clouds.json"""
import json
import sys
from pathlib import Path

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "utils"))

from preprocessing import preprocess  # noqa: E402
from ngrams import build_cloud  # noqa: E402

PHRASES_PATH = BASE / "04_alias_phrases.json"
OUT_PATH = BASE / "05_indicator_clouds.json"


def build_indicator_cloud(indicator: str, entry: dict) -> dict[str, int]:
    corpus_texts: list[str] = [indicator, entry["alias"]]
    for phrases in entry["phrases"].values():
        corpus_texts.extend(phrases)

    lemma_lists = [preprocess(text) for text in corpus_texts]
    cloud = build_cloud(lemma_lists, max_n=3)
    return cloud


def main():
    phrases_data = json.loads(PHRASES_PATH.read_text(encoding="utf-8"))

    result = {}
    for i, (indicator, entry) in enumerate(phrases_data.items()):
        cloud = build_indicator_cloud(indicator, entry)
        result[indicator] = {
            "alias": entry["alias"],
            "indices": entry["indices"],
            "cloud": cloud,
        }
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(phrases_data)}")

    cloud_sizes = [len(v["cloud"]) for v in result.values()]
    print(f"Облаков: {len(result)}")
    print(f"Размер облака: min={min(cloud_sizes)}, max={max(cloud_sizes)}, avg={sum(cloud_sizes)//len(cloud_sizes)}")

    OUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Записано → {OUT_PATH}")


if __name__ == "__main__":
    main()
