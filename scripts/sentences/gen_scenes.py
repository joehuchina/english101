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
REPAIR_ROUNDS = 3

SYSTEM = """You write graded English reading scenes for Chinese learners of English.
A scene is a short, natural little story: the same 1-3 characters in one place, told in consecutive sentences that follow on from each other.
Rules:
- Use EVERY target word at least once, in the meaning given. Inflected forms are fine (plural, past tense, -ing).
- Spread the target words over the sentences; each sentence carries 1-4 of them.
- Every other word must be very common and easy for the given level. Avoid rare words.
- Each sentence must be something an illustrator can draw as one picture: visible people, objects, actions, places. No text, signs, letters or numbers in the picture.
- Sentences must sound like real English a native speaker would write. No lists of words, no forced combinations.
- Vary sentence openings. Safe for all ages, no brands, no real people.
- zh: a natural Chinese translation.
- scene_prompt: one English sentence describing the picture for that sentence, naming the characters by their look (from "characters"), so every picture of the scene shows the same people.
Return JSON only:
{"title": "...", "title_zh": "...", "setting": "...", "characters": [{"name": "...", "look": "..."}],
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


def request_text(unit, lex, review):
    lo, hi = LENGTH[unit["level"]]
    text = (f"Level: CEFR {unit['level']}\nTopic: {unit['topic']}\n"
            f"Write exactly {unit['sentences']} sentences, each {lo}-{hi} words long.\n\n"
            f"Target words (use every one):\n{describe(lex, unit['targets'])}\n")
    if review:
        text += f"\nReview words (use each once if it fits naturally):\n{describe(lex, review)}\n"
    return text


def problems_text(scene, res, lex):
    lines = []
    for r in res["sentences"]:
        for p in r["problems"]:
            lines.append(f'- sentence {r["i"] + 1} "{scene["sentences"][r["i"]]["en"]}": {p}')
    if res["missing"]:
        lines.append("- these target words are not used yet (or not in the right part of speech): "
                     + ", ".join(lex.by_id[i]["word"] for i in res["missing"]))
    return "\n".join(lines)


def count_bad(res):
    return sum(1 for r in res["sentences"] if r["problems"]) + len(res["missing"])


def ledger():
    """How often each word has been taught so far, and corpus sentences per level."""
    counts, sentences = Counter(), {}
    for p in sorted(DRAFTS.glob("*.json")):
        d = json.loads(p.read_text())
        for r in d["check"]["sentences"]:
            counts.update(r["hits"])
        counts.update(d.get("review_hits", []))
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
    counts, corpus = ledger()
    review = pick_review(units, unit, counts)
    seen = corpus.get(unit["level"], [])
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": request_text(unit, lex, review)}]
    t0 = time.time()
    scene = chat(messages, 0.7)
    scene["review_words"] = review
    res = check_scene(scene, unit, lex, seen)
    attempts = 1
    while count_bad(res) and attempts <= REPAIR_ROUNDS:
        messages += [{"role": "assistant", "content": json.dumps(scene, ensure_ascii=False)},
                     {"role": "user", "content": "Fix these problems and return the whole scene again as JSON. "
                      "Keep the sentences that have no problems.\n" + problems_text(scene, res, lex)}]
        fixed = chat(messages, 0.4)
        fixed["review_words"] = review
        fres = check_scene(fixed, unit, lex, seen)
        attempts += 1
        if count_bad(fres) <= count_bad(res):
            scene, res = fixed, fres
    review_keys = {lex.by_id[w]["word"].lower() for w in review}
    text = " ".join(s["en"].lower() for s in scene["sentences"])
    scene.update({
        "scene_id": unit["scene_id"], "level": unit["level"], "topic": unit["topic"],
        "targets": unit["targets"], "check": res, "attempts": attempts,
        "seconds": round(time.time() - t0, 1),
        "review_hits": [w for w in review if lex.by_id[w]["word"].lower() in review_keys
                        and re.search(r"\b" + re.escape(lex.by_id[w]["word"].lower()), text)],
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
    if a.limit:
        todo = todo[: a.limit]
    DRAFTS.mkdir(parents=True, exist_ok=True)
    lex = Lexicon()
    for u in todo:
        path = DRAFTS / f"{u['scene_id']}.json"
        if path.exists():
            continue
        scene = generate(u, units, lex)
        path.write_text(json.dumps(scene, ensure_ascii=False, indent=1))
        res = scene["check"]
        print(f"{u['scene_id']}  {scene['seconds']:5.0f}s  attempts={scene['attempts']}  "
              f"bad sentences={sum(1 for r in res['sentences'] if r['problems'])}  "
              f"missing={len(res['missing'])}/{len(u['targets'])}  {scene.get('title', '')}", flush=True)


if __name__ == "__main__":
    main()
