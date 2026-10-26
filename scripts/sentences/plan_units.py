"""Split the 7,298 headwords into scenes: per level, grouped by topic, common words first.

Output: scripts/sentences/units.json
  [{"scene_id": "A1-001", "level": "A1", "topic": "daily", "sentences": 6, "targets": ["library", ...]}]
"""
import json
import math
from collections import defaultdict

from lexicon import ABSTRACT_TOPICS, DENSITY, HERE, LEVELS, SENTENCES_PER_SCENE, load_words


def chunk(items, size):
    n = max(1, round(len(items) / size))
    step = math.ceil(len(items) / n)
    return [items[i : i + step] for i in range(0, len(items), step)]


def plan_level(level, words):
    size = round(SENTENCES_PER_SCENE * DENSITY[level])
    concrete = defaultdict(list)
    abstract = []
    for w in words:
        (abstract if w["topic"] in ABSTRACT_TOPICS else concrete[w["topic"]]).append(w)

    # Topics too small for half a scene join "daily" so scenes stay full.
    for topic in [t for t, ws in concrete.items() if t != "daily" and len(ws) < size / 2]:
        concrete["daily"].extend(concrete.pop(topic))

    scenes = []
    for topic, ws in concrete.items():
        ws.sort(key=lambda w: w["order"])
        for part in chunk(ws, size):
            scenes.append({"topic": topic, "words": part})
    if not scenes:
        scenes = [{"topic": "daily", "words": []}]

    # Abstract words ride on concrete scenes, spread evenly, common words first.
    abstract.sort(key=lambda w: w["order"])
    scenes.sort(key=lambda s: len(s["words"]))
    for i, w in enumerate(abstract):
        scenes[i % len(scenes)]["words"].append(w)

    scenes.sort(key=lambda s: sum(w["order"] for w in s["words"]) / len(s["words"]))
    return [
        {
            "scene_id": f"{level}-{i + 1:03d}",
            "level": level,
            "topic": s["topic"],
            "sentences": max(5, min(8, math.ceil(len(s["words"]) / DENSITY[level]))),
            "targets": [w["id"] for w in s["words"]],
        }
        for i, s in enumerate(scenes)
    ]


def main():
    words = load_words()
    by_level = defaultdict(list)
    for w in words:
        by_level[w["level"]].append(w)
    units = []
    for level in LEVELS:
        units.extend(plan_level(level, by_level[level]))
    covered = [t for u in units for t in u["targets"]]
    assert len(covered) == len(set(covered)) == len(words), "every word must be in exactly one scene"
    (HERE / "units.json").write_text(json.dumps(units, ensure_ascii=False, indent=1))
    for level in LEVELS:
        lu = [u for u in units if u["level"] == level]
        print(f"{level}: {len(lu):3d} scenes, {sum(u['sentences'] for u in lu):4d} sentences, "
              f"{sum(len(u['targets']) for u in lu):4d} words")
    print(f"total: {len(units)} scenes, {sum(u['sentences'] for u in units)} sentences, {len(covered)} words")


if __name__ == "__main__":
    main()
