#!/usr/bin/env python3
"""Batch audio synthesis with Dual Cloned Voices (David 👨 + Rachel 👩).

Usage:
    # Synthesize A1-001 (David for narration, Rachel for sentences & words):
    python3 synthesize_audio.py --scene A1-001 --force

    # Custom role mapping:
    python3 synthesize_audio.py --scene A1-001 --role-narration david --role-sentence rachel --force
"""
import argparse
import json
import os
import pathlib
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
AUDIO_DIR = ROOT / "public" / "atlas" / "audio" / "scenes"
VOICE_DIR = HERE / "voice_clone"

MLX_PYTHON = Path.home() / ".venvs" / "german-tts" / "bin" / "python"
MODEL_NAME = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16"

# Load voice manifest
MANIFEST_FILE = VOICE_DIR / "manifest.json"
with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
    VOICES = json.load(f)["voices"]

def synth_with_voice(text: str, out_wav_or_mp3: pathlib.Path, voice_key: str = "rachel"):
    """Generate audio clip using specific cloned voice in MLX Qwen3-TTS."""
    v = VOICES.get(voice_key, VOICES["rachel"])
    ref_audio = VOICE_DIR / v["file"]
    ref_text = v["text"]

    out_wav_or_mp3.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_dir:
        cmd = [
            str(MLX_PYTHON), "-m", "mlx_audio.tts.generate",
            "--model", MODEL_NAME,
            "--ref_audio", str(ref_audio),
            "--ref_text", ref_text,
            "--text", text,
            "--lang_code", "en",
            "--speed", "1.0",
            "--output_path", tmp_dir,
            "--file_prefix", "clip"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            err = (r.stderr or "") + (r.stdout or "")
            raise RuntimeError(f"MLX TTS failed for {voice_key}: {err[-400:]}")

        wavs = list(pathlib.Path(tmp_dir).glob("clip*.wav"))
        if not wavs:
            raise RuntimeError(f"No WAV produced in {tmp_dir}")

        src_wav = wavs[0]
        # Loudness normalize and convert to high quality 128kbps MP3
        subprocess.run([
            "/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error",
            "-i", str(src_wav),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(out_wav_or_mp3)
        ], check=True)

def process_scene(scene: dict, role_narration="david", role_sentence="rachel", role_words="rachel", force=False):
    sid = scene["scene_id"]
    scene_dir = AUDIO_DIR / sid
    scene_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n==========================================")
    print(f"🎙️ Generating Multi-Voice Audio for {sid}: {scene.get('title')}")
    print(f"   Roles: Narration={role_narration} 👨 | Sentence={role_sentence} 👩 | Words={role_words} 👩")
    print(f"==========================================")

    for idx, sent in enumerate(scene.get("sentences", [])):
        prefix = f"{sid}_{idx+1:02d}"

        # 1. Narration (David 👨)
        narration = sent.get("narration")
        if narration:
            narr_path = scene_dir / f"{prefix}_narration.mp3"
            if force or not narr_path.exists():
                print(f"  [🎙️ Frame {idx+1} Narration ({role_narration})] {narration[:45]}...")
                synth_with_voice(narration, narr_path, voice_key=role_narration)
            else:
                print(f"  [🎙️ Frame {idx+1} Narration] (Cached)")

        # 2. Story Sentence (Rachel 👩)
        en_sentence = sent.get("en")
        if en_sentence:
            sent_path = scene_dir / f"{prefix}_sentence.mp3"
            if force or not sent_path.exists():
                print(f"  [📖 Frame {idx+1} Sentence ({role_sentence})] {en_sentence}")
                synth_with_voice(en_sentence, sent_path, voice_key=role_sentence)
            else:
                print(f"  [📖 Frame {idx+1} Sentence] (Cached)")

        # 3. Target Words (Rachel 👩)
        for tw in sent.get("sentence_targets", []):
            wid = tw["id"]
            word_str = tw["word"]
            word_path = scene_dir / f"{prefix}_word_{wid}.mp3"
            if force or not word_path.exists():
                print(f"  [🔤 Word ({role_words})] {word_str}")
                synth_with_voice(word_str, word_path, voice_key=role_words)
            else:
                print(f"  [🔤 Word] {word_str} (Cached)")

def main():
    parser = argparse.ArgumentParser(description="Multi-voice audio synthesis (David 👨 + Rachel 👩).")
    parser.add_argument("--scene", type=str, default="A1-001", help="Specific scene ID (default A1-001)")
    parser.add_argument("--all", action="store_true", help="Synthesize all 60 scenes")
    parser.add_argument("--role-narration", type=str, default="david", choices=list(VOICES.keys()))
    parser.add_argument("--role-sentence", type=str, default="rachel", choices=list(VOICES.keys()))
    parser.add_argument("--role-words", type=str, default="rachel", choices=list(VOICES.keys()))
    parser.add_argument("--force", action="store_true", help="Force regenerate existing files")
    args = parser.parse_args()

    units_file = OUT / "story_units.json"
    if not units_file.exists():
        print("Please run organize_story_units.py first!")
        sys.exit(1)

    with open(units_file, "r", encoding="utf-8") as f:
        story_units = json.load(f)

    if args.all:
        target_scenes = story_units
    else:
        target_scenes = [s for s in story_units if s["scene_id"] == args.scene]

    if not target_scenes:
        print(f"Scene {args.scene} not found!")
        sys.exit(1)

    for sc in target_scenes:
        process_scene(
            sc,
            role_narration=args.role_narration,
            role_sentence=args.role_sentence,
            role_words=args.role_words,
            force=args.force
        )

    print("\n✅ Multi-voice audio synthesis complete!")

if __name__ == "__main__":
    main()
