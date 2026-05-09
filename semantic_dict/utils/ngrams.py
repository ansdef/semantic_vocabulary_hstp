from collections import Counter


def build_ngrams(lemmas: list[str], max_n: int = 3) -> list[str]:
    result = []
    for n in range(1, max_n + 1):
        for i in range(len(lemmas) - n + 1):
            gram = "_".join(lemmas[i : i + n])
            result.append(gram)
    return result


def build_cloud(corpus: list[list[str]], max_n: int = 3) -> dict[str, int]:
    counter: Counter = Counter()
    for lemmas in corpus:
        grams = build_ngrams(lemmas, max_n)
        counter.update(grams)
    return dict(counter)
