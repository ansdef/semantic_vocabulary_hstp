"""Этап 7: движок сопоставления запроса с облаками показателей.

Использование:
    cd semantic_dict
    python3 07_match_engine.py "сколько у нас исследователей в IT"
"""
import json
import sys
import time
from pathlib import Path

_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE / "utils"))
sys.path.insert(0, str(_BASE))

from preprocessing import preprocess  # noqa: E402
from ngrams import build_ngrams  # noqa: E402

_CLOUDS_PATH = _BASE / "05_indicator_clouds.json"
_SYNONYMS_PATH = _BASE / "utils" / "synonyms.json"

_indicator_clouds: dict | None = None
_synonyms: dict | None = None


def _get_clouds() -> dict:
    global _indicator_clouds
    if _indicator_clouds is None:
        _indicator_clouds = json.loads(_CLOUDS_PATH.read_text(encoding="utf-8"))
    return _indicator_clouds


def _get_synonyms() -> dict:
    global _synonyms
    if _synonyms is None:
        _synonyms = json.loads(_SYNONYMS_PATH.read_text(encoding="utf-8"))
    return _synonyms


def build_query_cloud(query: str) -> dict[str, int]:
    """Обрабатывает строку запроса и возвращает облако лексем с весами."""
    lemmas = preprocess(query)
    cloud: dict[str, int] = {}

    grams = build_ngrams(lemmas, max_n=3)
    for g in grams:
        cloud[g] = cloud.get(g, 0) + 1

    synonyms = _get_synonyms()
    for lemma in [g for g in grams if "_" not in g]:
        for syn in synonyms.get(lemma, [])[:3]:
            syn_lemmas = preprocess(syn)
            if not syn_lemmas:
                continue
            for sg in build_ngrams(syn_lemmas, max_n=3):
                cloud[sg] = cloud.get(sg, 0) + 1

    return cloud


def match(query_cloud: dict[str, int], indicator_clouds: dict | None = None) -> list[dict]:
    """Сопоставляет облако запроса с облаками всех показателей.

    Возвращает список совпадений, отсортированный по убыванию Жаккара.
    """
    if indicator_clouds is None:
        indicator_clouds = _get_clouds()

    q_keys = set(query_cloud.keys())
    results = []

    for indicator, data in indicator_clouds.items():
        ind_cloud = data["cloud"]
        ind_keys = set(ind_cloud.keys())
        intersection = q_keys & ind_keys
        if not intersection:
            continue
        union = q_keys | ind_keys
        jaccard = len(intersection) / len(union)
        overlap = len(intersection) / min(len(q_keys), len(ind_keys))
        results.append(
            {
                "indicator": indicator,
                "alias": data["alias"],
                "indices": data["indices"],
                "matched_lexemes": sorted(intersection),
                "cloud_A_size": len(q_keys),
                "cloud_B_size": len(ind_keys),
                "intersection_size": len(intersection),
                "jaccard": round(jaccard, 4),
                "overlap": round(overlap, 4),
            }
        )

    return sorted(results, key=lambda x: x["jaccard"], reverse=True)


def search(query: str) -> list[dict]:
    """Полный пайплайн: строка запроса → отсортированный список результатов."""
    cloud = build_query_cloud(query)
    return match(cloud)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "сколько у нас исследователей в IT"
    t0 = time.time()
    results = search(query)
    elapsed = time.time() - t0

    print(f"Запрос: {query!r}")
    print(f"Совпадений: {len(results)}, время: {elapsed * 1000:.0f} мс")
    print()
    for r in results[:10]:
        print(
            f"  J={r['jaccard']:.4f}  O={r['overlap']:.4f}  [{r['alias']}]  "
            f"{r['indicator'][:65]}"
        )
        print(f"    совпало: {r['matched_lexemes'][:6]}")
