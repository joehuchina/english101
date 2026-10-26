"""Coverage and quality report; writes out/coverage.json.

  .venv/bin/python report.py            all levels
  .venv/bin/python report.py --level A1
"""
import argparse
import json
from collections import Counter

from check import Lexicon, check_scene
from lexicon import HERE, LEVELS, OUT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", default="")
    a = ap.parse_args()
    lex = Lexicon()
    units = json.loads((HERE / "units.json").read_text())
    levels = [a.level] if a.level else LEVELS
    coverage = {}  # word id -> [sentence refs where it is a checked target]
    stats = Counter()
    problems = Counter()
    for u in units:
        if u["level"] not in levels:
            continue
        stats["scenes"] += 1
        path = OUT / "reviewed" / f"{u['scene_id']}.json"
        kind = "reviewed"
        if not path.exists():
            path, kind = OUT / "drafts" / f"{u['scene_id']}.json", "draft"
        if not path.exists():
            continue
        stats[kind] += 1
        scene = json.loads(path.read_text())
        res = check_scene(scene, u, lex)
        for r in res["sentences"]:
            stats["sentences"] += 1
            ref = f"{u['scene_id']}#{r['i'] + 1}"
            if r["problems"]:
                stats["bad sentences"] += 1
                for p in r["problems"]:
                    problems[p.split(":")[0].split(" (")[0].rstrip("0123456789 -")] += 1
            for h in r["hits"] + r["review_hits"]:
                coverage.setdefault(h, []).append(ref)
        stats["review words used"] += len(res["review_used"])
        stats["review words offered"] += len(scene.get("review_words", []))

    print(f"scenes: {stats['scenes']}  (reviewed {stats['reviewed']}, draft only {stats['draft']}, "
          f"not generated {stats['scenes'] - stats['reviewed'] - stats['draft']})")
    print(f"sentences: {stats['sentences']}  failing rule checks: {stats['bad sentences']}")
    for p, n in problems.most_common():
        print(f"   {n:4d}  {p}")
    print(f"review words used: {stats['review words used']} / {stats['review words offered']}")
    print()
    for level in levels:
        words = [w["id"] for w in lex.words if w["level"] == level]
        got = [w for w in words if w in coverage]
        print(f"{level}: {len(got)}/{len(words)} words covered ({len(got) * 100 // len(words)}%)")
    want = [w for w in lex.words if w["level"] in levels]
    missing = [w["word"] for w in want if w["id"] not in coverage]
    if missing:
        print(f"not covered ({len(missing)}): {', '.join(missing[:60])}{' …' if len(missing) > 60 else ''}")
    times = Counter(min(len(coverage.get(w["id"], [])), 3) for w in want)
    print(f"times seen: 0×{times[0]}  1×{times[1]}  2×{times[2]}  3+×{times[3]}")
    (OUT / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
