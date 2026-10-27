"""Word data for the sentence corpus, read from the published atlas."""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]
ATLAS = ROOT / "public" / "atlas"
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "out"

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
# New words per sentence and allowed sentence length (in words) for each level.
DENSITY = {"A1": 2, "A2": 2.5, "B1": 3, "B2": 3, "C1": 3.5, "C2": 4}
LENGTH = {"A1": (6, 9), "A2": (8, 11), "B1": (10, 14), "B2": (12, 16), "C1": (14, 20), "C2": (14, 20)}
SENTENCES_PER_SCENE = 6
ABSTRACT_TOPICS = {"emotion", "thinking"}


def load_words():
    """All headwords in learning-path order, with level, topic, parts of speech and senses."""
    index = json.loads((ATLAS / "index.json").read_text())
    topics = [t[0] for t in index["topics"]]
    entries = {}
    for p in (ATLAS / "entries").glob("*.json"):
        for e in json.loads(p.read_text()):
            entries[e["id"]] = e
    words = []
    for order, row in enumerate(index["words"]):
        wid, word, _zh, _ipa, cefr, topic, _media = row
        e = entries[wid]
        words.append({
            "id": wid,
            "word": word,
            "level": index["cefr"][cefr],
            "topic": topics[topic],
            "order": order,
            "pos": sorted({s["pos"] for s in e["senses"]}),
            "senses": [{"pos": s["pos"], "zh": s["zh"], "en": s["en"]} for s in e["senses"]],
        })
    return words


def is_phrase(word):
    return bool(re.search(r"[\s\-'.]", word))


def load_cast():
    return json.loads((HERE / "cast.json").read_text())


# Names earlier drafts used that are not in the cast; they must not appear any more.
OLD_NAMES = {"Tom", "Mary", "Sam", "Jack", "Ali", "Emma", "Zoe", "Raj", "Lucy", "Aiko", "Finn", "Maya"}
