#!/usr/bin/env python3
"""Organize A1 scenes into 3-tier 'Look-and-Listen' (看图听话) story units:
1. scene_prompt (AI image generation prompt)
2. narration (Oral English picture description for listening) + narration_zh
3. en & zh (Story sentence)
4. sentence_targets (Core vocabulary in this frame with pos & zh definitions)
"""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
REVIEWED_DIR = OUT / "reviewed"
PUBLIC = ROOT / "public" / "atlas"

sys.path.insert(0, str(HERE))
from lexicon import load_words

def clean_for_speech(prompt: str) -> str:
    """Transform an image generation prompt into clean spoken English picture description."""
    if not prompt:
        return ""
    # Remove parenthetical character visual definitions (e.g. '(a ten-year-old boy...)')
    text = re.sub(r"\s*\([^)]*\)", "", prompt).strip()
    # Normalize punctuation and whitespace
    text = re.sub(r"\s+", " ", text)
    # Convert semicolons to periods for natural pause
    text = text.replace(";", ".")
    # Ensure ending period
    if text and not text.endswith((".", "!", "?")):
        text += "."
    return text

def main():
    print("1. Loading lexicon and coverage mapping...")
    words = {w["id"]: w for w in load_words()}

    with open(OUT / "coverage.json", "r", encoding="utf-8") as f:
        cov = json.load(f)

    # Invert coverage: scene_id -> sentence_idx -> list of word_ids
    scene_words_map = {}
    for wid, occ_list in cov.items():
        for occ in occ_list:
            sid, sidx_str = occ.split("#")
            sidx = int(sidx_str) - 1
            if sid not in scene_words_map:
                scene_words_map[sid] = {}
            if sidx not in scene_words_map[sid]:
                scene_words_map[sid][sidx] = []
            if wid not in scene_words_map[sid][sidx]:
                scene_words_map[sid][sidx].append(wid)

    print("2. Processing all 60 reviewed scenes...")
    all_story_units = []
    reviewed_files = sorted(REVIEWED_DIR.glob("A1-*.json"))

    for rf in reviewed_files:
        with open(rf, "r", encoding="utf-8") as f:
            sc = json.load(f)
        
        sid = sc["scene_id"]
        sid_map = scene_words_map.get(sid, {})

        for idx, sent in enumerate(sc.get("sentences", [])):
            # 1. AI Image prompt
            img_prompt = sent.get("scene_prompt", "")
            
            # 2. Oral picture narration
            narration = clean_for_speech(img_prompt)
            sent["narration"] = narration

            # 3. Sentence targets
            wids = sid_map.get(idx, [])
            # Also check if any scene targets match words in this sentence
            sentence_text = sent.get("en", "").lower()
            for tw in sc.get("targets", []):
                clean_tw = tw.replace("-", " ")
                if re.search(r"\b" + re.escape(clean_tw) + r"\b", sentence_text, re.IGNORECASE):
                    if tw not in wids:
                        wids.append(tw)

            targets_data = []
            for wid in wids:
                if wid in words:
                    w = words[wid]
                    targets_data.append({
                        "id": wid,
                        "word": w["word"],
                        "pos": "/".join(w["pos"]),
                        "zh": w["senses"][0]["zh"] if w["senses"] else "",
                        "en": w["senses"][0]["en"] if w["senses"] else ""
                    })
            
            sent["sentence_targets"] = targets_data

        # Update reviewed JSON file in-place
        with open(rf, "w", encoding="utf-8") as f:
            json.dump(sc, f, ensure_ascii=False, indent=1)

        all_story_units.append(sc)

    # Save consolidated story units
    out_all = OUT / "story_units.json"
    with open(out_all, "w", encoding="utf-8") as f:
        json.dump(all_story_units, f, ensure_ascii=False, indent=2)

    # The site only needs what the read-along view shows, plus whether a scene's
    # pictures and recordings are all present.
    public = [compact(sc) for sc in all_story_units]
    out_pub = PUBLIC / "story_units.json"
    out_pub.write_text(json.dumps(public, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    ready = sum(1 for sc in public if sc["ready"])
    print(f"Organized {len(public)} scenes, {ready} ready (all pictures and recordings present).")
    print(f"Saved {out_all} and {out_pub} ({out_pub.stat().st_size / 1024:.1f} KB)")


def is_ready(sc) -> bool:
    sid = sc["scene_id"]
    for i in range(1, len(sc["sentences"]) + 1):
        stem = f"{sid}_{i:02d}"
        files = [
            PUBLIC / "scene_images" / f"{sid}-{i:02d}.png",
            PUBLIC / "audio" / "scenes" / sid / f"{stem}_narration.mp3",
            PUBLIC / "audio" / "scenes" / sid / f"{stem}_sentence.mp3",
        ]
        if not all(f.exists() for f in files):
            return False
    return True


def compact(sc):
    return {
        "id": sc["scene_id"],
        "level": sc["level"],
        "topic": sc["topic"],
        "title": sc["title"],
        "title_zh": sc.get("title_zh", ""),
        "ready": is_ready(sc),
        "sentences": [
            {
                "en": s["en"],
                "zh": s["zh"],
                "narration": s.get("narration", ""),
                "words": [{"id": t["id"], "word": t["word"], "zh": t["zh"]} for t in s.get("sentence_targets", [])],
            }
            for s in sc["sentences"]
        ],
    }

if __name__ == "__main__":
    main()
