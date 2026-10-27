"""Rule checks for generated scenes (layer 1). Run with scripts/sentences/.venv/bin/python.

  check.py out/drafts/A1-001.json [...]    print problems for scene files
"""
import json
import re
import sys
from functools import lru_cache

import spacy

from lexicon import LENGTH, LEVELS, is_phrase, load_words

# Which spaCy coarse tags count as each dictionary part of speech.
POS_TAGS = {
    "n.": {"NOUN", "PROPN"},
    "v.": {"VERB", "AUX"},
    "adj.": {"ADJ"},
    "adv.": {"ADV", "ADP", "PART", "SCONJ", "INTJ"},
    "prep.": {"ADP", "SCONJ", "ADV", "PART"},
    "conj.": {"CCONJ", "SCONJ", "ADV"},
    "det.": {"DET", "PRON", "NUM", "ADJ"},
    "pron.": {"PRON", "DET", "ADJ"},
    "num.": {"NUM", "NOUN", "DET", "ADJ"},
    "int.": None,
    "phr.": None,
}
CJK = re.compile(r"[一-鿿]")


def norm(w):
    """Lowercase and fold British spellings so colour/color and organise/organize match."""
    w = w.lower().replace("’", "'")
    w = re.sub(r"our\b", "or", w)
    w = re.sub(r"is(e|ed|es|ing|ation)\b", r"iz\1", w)
    w = re.sub(r"yse\b", "yze", w)
    w = re.sub(r"([^aeiou])re\b", r"\1er", w)
    w = re.sub(r"ogue\b", "og", w)
    return w


@lru_cache(maxsize=1)
def nlp():
    return spacy.load("en_core_web_lg")


class Lexicon:
    def __init__(self, words=None):
        self.words = words or load_words()
        self.by_id = {w["id"]: w for w in self.words}
        self.level_of = {}
        for w in self.words:
            k = norm(w["word"])
            rank = LEVELS.index(w["level"])
            self.level_of[k] = min(rank, self.level_of.get(k, 99))

    def rank(self, token):
        for k in (norm(token.lemma_), norm(token.text)):
            if k in self.level_of:
                return self.level_of[k]
        return None


def inflections(w):
    """Regular forms of a word, for when spaCy's lemma is wrong (it reads "hates" as "hat")."""
    forms = {w, w + "s", w + "es", w + "ed", w + "d", w + "ing"}
    if w.endswith("e"):
        forms |= {w[:-1] + "ing"}
    if w.endswith("y") and len(w) > 2 and w[-2] not in "aeiou":
        forms |= {w[:-1] + "ies", w[:-1] + "ied"}
    if re.search(r"[^aeiou][aeiou][bdgklmnprt]$", w):
        forms |= {w + w[-1] + "ed", w + w[-1] + "ing"}
    return forms


def target_hit(word, doc, tokens_norm, lemmas_norm):
    """Is the headword used in this sentence, as one of its dictionary parts of speech?"""
    w = word["word"]
    if is_phrase(w):
        parts = [p for p in re.split(r"[\s\-]+", norm(w)) if p]
        n = len(parts)
        for seq in (tokens_norm, lemmas_norm):
            for i in range(len(seq) - n + 1):
                if seq[i : i + n] == parts:
                    return True
        text = norm(doc.text)
        return re.search(r"(?<![a-z])" + r"[\s\-]?".join(map(re.escape, parts)) + r"(?![a-z])", text) is not None
    key = norm(w)
    allowed = set()
    for p in word["pos"]:
        tags = POS_TAGS.get(p)
        if tags is None:
            allowed = None
            break
        allowed |= tags
    forms = inflections(key)
    for tok, t, l in zip(doc, tokens_norm, lemmas_norm):
        if key != l and t not in forms:
            continue
        if allowed is None or tok.pos_ in allowed:
            return True
        if "v." in word["pos"] and tok.text.lower().endswith("ing"):
            return True
        # Gerund headwords (swimming, reading) are tagged as verbs.
        if "n." in word["pos"] and key.endswith("ing") and tok.tag_ == "VBG":
            return True
        # Participle adjectives (tired, broken, interesting) are often tagged as verbs.
        if "adj." in word["pos"] and tok.tag_ in ("VBN", "VBG"):
            return True
    return False


def check_sentence(s, level, lex, targets, review, max_rare=1):
    """Problems with one sentence, and which scene targets it actually uses."""
    problems = []
    doc = nlp()(s["en"])
    words = [t for t in doc if not t.is_punct and not t.is_space]
    toks = [norm(t.text) for t in doc]
    lems = [norm(t.lemma_) for t in doc]
    lo, hi = LENGTH[level]
    if not lo <= len(words) <= hi:
        problems.append(f"length {len(words)} not in {lo}-{hi}")

    hits = [tid for tid in dict.fromkeys([*targets, *review])
            if tid in lex.by_id and target_hit(lex.by_id[tid], doc, toks, lems)]
    allowed = {norm(lex.by_id[i]["word"]) for i in [*targets, *review] if i in lex.by_id}
    cur = LEVELS.index(level)
    rare = []
    for t in words:
        if not t.is_alpha or t.pos_ in ("PROPN", "NUM") or t.is_stop:
            continue
        if norm(t.lemma_) in allowed or norm(t.text) in allowed:
            continue
        r = lex.rank(t)
        if r is None or r > cur:
            rare.append(t.text)
    if len(rare) > max_rare:
        problems.append("above level: " + ", ".join(rare))

    zh = s.get("zh", "")
    cjk = len(CJK.findall(zh))
    if not cjk:
        problems.append("missing Chinese")
    elif not 0.8 <= cjk / max(1, len(words)) <= 4:
        problems.append(f"Chinese length looks wrong ({cjk} chars for {len(words)} words)")
    return problems, hits


def bag(text):
    return set(re.findall(r"[a-z']+", text.lower()))


def check_scene(scene, unit, lex, seen=()):
    """Check a generated scene against its unit. `seen` holds earlier sentences of the corpus."""
    level = unit["level"]
    review = scene.get("review_words", [])
    results = []
    openings = {}
    prior = [bag(t) for t in seen]
    for i, s in enumerate(scene["sentences"]):
        problems, hits = check_sentence(s, level, lex, unit["targets"], review)
        b = bag(s["en"])
        for other in prior:
            if b and len(b & other) / len(b | other) >= 0.8:
                problems.append("near-duplicate of an earlier sentence")
                break
        prior.append(b)
        opening = " ".join(re.findall(r"[a-z']+", s["en"].lower())[:2])
        if opening in openings:
            problems.append(f"same opening as sentence {openings[opening] + 1}")
        openings.setdefault(opening, i)
        targets = set(unit["targets"])
        results.append({"i": i, "problems": problems,
                        "hits": [h for h in hits if h in targets],
                        "review_hits": [h for h in hits if h not in targets]})
    used = {h for r in results for h in r["hits"]}
    missing = [t for t in unit["targets"] if t not in used]
    reviewed = {h for r in results for h in r["review_hits"]}
    n = len(scene["sentences"])
    scene_problems = [] if 5 <= n <= 8 else [f"scene has {n} sentences, needs 5-8"]
    return {"sentences": results, "missing": missing, "scene_problems": scene_problems,
            "review_used": [w for w in review if w in reviewed],
            "review_needed": min(2, len(review))}


def main(paths):
    lex = Lexicon()
    units = {u["scene_id"]: u for u in json.load(open(lex_path("units.json")))}
    for p in paths:
        scene = json.load(open(p))
        res = check_scene(scene, units[scene["scene_id"]], lex)
        print(f"== {scene['scene_id']}  missing: {[lex.by_id[i]['word'] for i in res['missing']] or 'none'}  "
              f"review used: {len(res['review_used'])}/{res['review_needed']} needed  "
              f"{' '.join(res['scene_problems'])}")
        for r in res["sentences"]:
            s = scene["sentences"][r["i"]]
            print(f"  {'ok ' if not r['problems'] else 'BAD'} {s['en']}")
            for pr in r["problems"]:
                print(f"      - {pr}")


def lex_path(name):
    from lexicon import HERE
    return HERE / name


if __name__ == "__main__":
    main(sys.argv[1:])
