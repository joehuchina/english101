"""Print what a reviewer needs for one scene: targets with meanings, review words, and the draft.

  .venv/bin/python show_scene.py A1-006 [A1-007 ...]
"""
import json
import sys

from lexicon import HERE, LENGTH, OUT, load_words

words = {w["id"]: w for w in load_words()}
units = {u["scene_id"]: u for u in json.loads((HERE / "units.json").read_text())}
for sid in sys.argv[1:]:
    u = units[sid]
    d = json.loads((OUT / "drafts" / f"{sid}.json").read_text())
    print(f"## {sid}  level {u['level']}  sentence length {LENGTH[u['level']][0]}-{LENGTH[u['level']][1]} words  "
          f"5-8 sentences  topic {u['topic']}")
    print("targets (id: word, part of speech, meaning):")
    for i in u["targets"]:
        w = words[i]
        print(f"  {i}: {w['word']} ({'/'.join(w['pos'])}) " + " | ".join(s['zh'] for s in w["senses"]))
    print("review words (use at least 2):", ", ".join(f"{i}: {words[i]['word']}" for i in d["review_words"]) or "none")
    print("draft:", json.dumps({k: d.get(k) for k in ("story", "title", "title_zh", "setting", "characters")}, ensure_ascii=False))
    for s in d["sentences"]:
        print(f"  - {s['en']} | {s['zh']}")
    print()
