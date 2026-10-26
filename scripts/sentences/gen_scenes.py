"""Draft scenes with local gemma4 (Ollama), then repair them against check.py.

  .venv/bin/python gen_scenes.py --level A1 --limit 5
  .venv/bin/python gen_scenes.py --only A1-001,A1-002

Drafts go to out/drafts/<scene_id>.json; finished scenes are skipped, so runs resume.
"""
import argparse
import json
import re
import time
import urllib.request
from collections import Counter

from check import Lexicon, check_scene
from lexicon import HERE, LENGTH, OUT

OLLAMA = "http://localhost:11434/api/chat"
MODEL = "gemma4:26b"
DRAFTS = OUT / "drafts"
REVIEWED = OUT / "reviewed"
REPAIR_ROUNDS = 3

NAMES = ["Ben", "Anna", "Leo", "Mia", "Sam", "Lily", "Omar", "Nina", "Jack", "Rosa", "Ali", "Emma",
         "Kofi", "Hana", "Max", "Zoe", "Raj", "Lucy", "Dan", "Aiko", "Finn", "Sara", "Ivan", "Maya"]

SYSTEM = """You write graded English reading scenes for Chinese learners of English.

A scene is one small, believable story: the same 1-3 characters in one place, and every sentence follows from the one before.
Work in this order:
1. "story": first decide the plot in 2-3 plain sentences. Choose a situation where the target words come up NATURALLY.
2. Then write the sentences that tell that story.

Rules:
- Use EVERY target word at least once, in the meaning given (for example "glass: 玻璃" means the material, so "the window glass", not "a glass of water").
- Use at least 2 of the review words, also naturally.
- A sentence may carry just 1 target word. Never squeeze words together that do not belong together. If two words do not fit in one sentence, put them in different sentences.
- Every sentence must make sense on its own and be true inside the story. A child should be able to picture it.
- Other words must be very common and easy for the level.
- Each sentence can be drawn as one picture: visible people, objects, actions, places. No text, signs, letters or numbers in the picture.
- Use only the character names you are given. Vary sentence openings. Safe for all ages, no brands, no real people.

Bad sentences (never write like this):
- "Strong men drink juice every minute."  (strange claim, words forced together)
- "They eat lunch without any food."  (contradicts itself)
- "He puts his head in front."  (no clear meaning)
- "Anna will let him use fruit."  (unnatural: you eat fruit, you don't "use" it)
Good sentences:
- "His clothes are all over the bedroom floor."
- "Leo gives her a sandwich from his lunch."

zh: a natural Chinese translation.
scene_prompt: one English sentence describing the picture, naming each character with the same look every time.
Return JSON only:
{"story": "...", "title": "...", "title_zh": "...", "setting": "...", "characters": [{"name": "...", "look": "..."}],
 "sentences": [{"en": "...", "zh": "...", "scene_prompt": "..."}]}"""


def chat(messages, temperature):
    payload = {"model": MODEL, "messages": messages, "stream": False, "format": "json",
               "think": False, "options": {"temperature": temperature, "num_ctx": 8192}}
    req = urllib.request.Request(OLLAMA, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        content = json.load(r)["message"]["content"]
    return json.loads(re.sub(r"^```(?:json)?|```$", "", content.strip()).strip())


def describe(lex, ids):
    lines = []
    for i in ids:
        w = lex.by_id[i]
        sense = w["senses"][0]
        lines.append(f'- {w["word"]} ({"/".join(w["pos"])}): {sense["zh"]} — {sense["en"]}')
    return "\n".join(lines)


def names_for(index):
    return [NAMES[(index * 3 + k) % len(NAMES)] for k in range(3)]


def request_text(unit, lex, review, names):
    lo, hi = LENGTH[unit["level"]]
    n = unit["sentences"]
    text = (f"Level: CEFR {unit['level']}\nTopic: {unit['topic']}\n"
            f"Write {n} or {n + 1} sentences, each {lo}-{hi} words long.\n"
            f"Character names you may use: {', '.join(names)}.\n\n"
            f"Target words (use every one):\n{describe(lex, unit['targets'])}\n")
    if review:
        text += f"\nReview words (use at least 2):\n{describe(lex, review)}\n"
    return text


def problems_text(scene, res, lex):
    lines = []
    for r in res["sentences"]:
        for p in r["problems"]:
            lines.append(f'- sentence {r["i"] + 1} "{scene["sentences"][r["i"]]["en"]}": {p}')
    if res["missing"]:
        lines.append("- these target words are not used yet (or not in the right part of speech): "
                     + ", ".join(lex.by_id[i]["word"] for i in res["missing"]))
    if len(res["review_used"]) < res["review_needed"]:
        lines.append(f"- use at least {res['review_needed']} review words; used so far: "
                     + (", ".join(lex.by_id[i]["word"] for i in res["review_used"]) or "none"))
    return "\n".join(lines)


def count_bad(res):
    return (sum(1 for r in res["sentences"] if r["problems"]) + len(res["missing"])
            + max(0, res["review_needed"] - len(res["review_used"])))


def ledger(units, lex):
    """How often each word has been taught so far, and corpus sentences per level.
    A reviewed scene counts instead of its draft."""
    counts, sentences = Counter(), {}
    by_id = {u["scene_id"]: u for u in units}
    for p in sorted(DRAFTS.glob("*.json")):
        d = json.loads(p.read_text())
        rv = REVIEWED / p.name
        if rv.exists():
            d = json.loads(rv.read_text())
            res = check_scene(d, by_id[d["scene_id"]], lex)
        else:
            res = d["check"]
        for r in res["sentences"]:
            counts.update(r["hits"])
            counts.update(r.get("review_hits", []))
        sentences.setdefault(d["level"], []).extend(s["en"] for s in d["sentences"])
    return counts, sentences


def pick_review(units, unit, counts, n=4):
    earlier = []
    for u in units:
        if u["scene_id"] == unit["scene_id"]:
            break
        earlier.extend(u["targets"])
    earlier = [w for w in earlier if counts[w] > 0]
    order = {w: i for i, w in enumerate(earlier)}
    earlier.sort(key=lambda w: (counts[w], order[w]))
    return earlier[:n]


def generate(unit, units, lex):
    counts, corpus = ledger(units, lex)
    review = pick_review(units, unit, counts)
    seen = corpus.get(unit["level"], [])
    names = names_for(units.index(unit))
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": request_text(unit, lex, review, names)}]
    t0 = time.time()
    scene = chat(messages, 0.7)
    scene["review_words"] = review
    res = check_scene(scene, unit, lex, seen)
    attempts = 1
    while count_bad(res) and attempts <= REPAIR_ROUNDS:
        messages += [{"role": "assistant", "content": json.dumps(scene, ensure_ascii=False)},
                     {"role": "user", "content": "Fix these problems and return the whole scene again as JSON. "
                      "Keep the sentences that have no problems, and keep the story making sense.\n"
                      + problems_text(scene, res, lex)}]
        fixed = chat(messages, 0.4)
        fixed["review_words"] = review
        fres = check_scene(fixed, unit, lex, seen)
        attempts += 1
        if count_bad(fres) <= count_bad(res):
            scene, res = fixed, fres
    scene.update({
        "scene_id": unit["scene_id"], "level": unit["level"], "topic": unit["topic"],
        "targets": unit["targets"], "check": res, "attempts": attempts,
        "seconds": round(time.time() - t0, 1),
    })
    return scene


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    units = json.loads((HERE / "units.json").read_text())
    todo = [u for u in units if (not a.level or u["level"] == a.level)
            and (not a.only or u["scene_id"] in a.only.split(","))]
    DRAFTS.mkdir(parents=True, exist_ok=True)
    todo = [u for u in todo if not (DRAFTS / f"{u['scene_id']}.json").exists()]
    if a.limit:
        todo = todo[: a.limit]
    lex = Lexicon()
    for u in todo:
        scene = generate(u, units, lex)
        (DRAFTS / f"{u['scene_id']}.json").write_text(json.dumps(scene, ensure_ascii=False, indent=1))
        res = scene["check"]
        print(f"{u['scene_id']}  {scene['seconds']:5.0f}s  attempts={scene['attempts']}  "
              f"bad sentences={sum(1 for r in res['sentences'] if r['problems'])}  "
              f"missing={len(res['missing'])}/{len(u['targets'])}  "
              f"review={len(res['review_used'])}/{len(scene['review_words'])}  {scene.get('title', '')}", flush=True)


if __name__ == "__main__":
    main()
