"""High-performance scene image generator using local ComfyUI (Qwen-Image).

Features:
- Optimized DiT latent resolution (512x512, 1024 patches) for ~2.5x faster step speed on Apple Silicon.
- 14-step Euler/Simple sampler (fully converged editorial risograph style).
- Batch Queue Pipeline: Submits entire scene to ComfyUI's native queue upfront,
  eliminating Python dispatch latency and keeping VRAM weights resident.
- Live progress sync: Automatically copies completed frames to public/atlas/scene_images/
  as soon as each frame finishes.

Usage:
    python3 draw_scenes.py A1-002
    python3 draw_scenes.py A1-002 A1-003 --size 512 --steps 14
"""
import argparse
import json
import pathlib
from pathlib import Path
import re
import shutil
import sys
import time
import urllib.request
import zlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "out"
IMAGES = OUT / "images"
PUB_IMAGES = ROOT / "public" / "atlas" / "scene_images"

COMFY = "http://127.0.0.1:8188"
COMFY_OUT = Path.home() / "ComfyUI-Installs" / "ComfyUI" / "output"

# Shared editorial risograph art direction
_src = (ROOT / "scripts" / "atlas" / "gen_images.py").read_text()
STYLE = "".join(re.findall(r'"([^"]*)"', re.search(r"STYLE = \((.*?)\n\)", _src, re.S).group(1)))
NEG = (
    "text, letters, words, speech bubbles, thought bubbles, labels, numbers, watermark, signature, logo, "
    "bad anatomy, extra fingers, blurry, low quality, deformed"
)


def build_workflow(prompt: str, prefix: str, seed: int, size: int = 512, steps: int = 14):
    """Construct ComfyUI prompt graph for Qwen-Image 2.1."""
    return {
        "1": {"inputs": {"unet_name": "qwen-image-2.1-Q4_K_M.gguf"}, "class_type": "UnetLoaderGGUF"},
        "2": {
            "inputs": {"clip_name": "qwen3vl_8b_int8_convrot.safetensors", "type": "qwen_image", "device": "default"},
            "class_type": "CLIPLoader",
        },
        "3": {"inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}, "class_type": "VAELoader"},
        "4": {
            "inputs": {"prompt": prompt, "negative_prompt": NEG, "resolution": size, "clip": ["2", 0]},
            "class_type": "TextEncodeQwenImage21",
        },
        "5": {"inputs": {"width": size, "height": size, "batch_size": 1}, "class_type": "EmptyLatentImage"},
        "6": {
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["1", 0],
                "positive": ["4", 0],
                "negative": ["4", 1],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "7": {"inputs": {"samples": ["6", 0], "vae": ["3", 0]}, "class_type": "VAEDecode"},
        "8": {"inputs": {"filename_prefix": prefix, "images": ["7", 0]}, "class_type": "SaveImage"},
    }


def post_prompt(wf: dict) -> str:
    """Submit a workflow graph to ComfyUI queue and return prompt_id."""
    data = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(f"{COMFY}/prompt", data=data, headers={"Content-Type": "application/json"})
    res = json.loads(urllib.request.urlopen(req, timeout=30).read())
    return res["prompt_id"]


def get_history(prompt_id: str):
    """Fetch history for a specific prompt_id."""
    try:
        url = f"{COMFY}/history/{prompt_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "draw-scenes"})
        res = json.loads(urllib.request.urlopen(req, timeout=10).read())
        return res.get(prompt_id)
    except Exception:
        return None


def extract_output_path(hist_item: dict) -> Path | None:
    """Extract generated image path from ComfyUI history record."""
    if not hist_item:
        return None
    for o in hist_item.get("outputs", {}).values():
        for im in o.get("images", []):
            sub = im.get("subfolder", "")
            fname = im.get("filename", "")
            p = COMFY_OUT / sub / fname
            if p.exists():
                return p
    return None


def process_scene_pipeline(sid: str, size: int = 512, steps: int = 14):
    """Batch-queue all missing frames for a scene into ComfyUI pipeline."""
    scene_file = OUT / "reviewed" / f"{sid}.json"
    if not scene_file.exists():
        print(f"⚠️ Scene file not found: {scene_file}")
        return

    scene = json.loads(scene_file.read_text(encoding="utf-8"))
    sentences = scene.get("sentences", [])
    total_frames = len(sentences)
    seed = zlib.crc32(sid.encode("utf-8"))

    print(f"\n=======================================================")
    print(f"🎨 Scene {sid}: {scene.get('title')} ({total_frames} frames)")
    print(f"   Settings: {size}x{size}px | {steps} steps | Seed: {seed}")
    print(f"=======================================================")

    # 1. Identify tasks needing generation
    tasks = []  # list of (index, sentence_obj, dst_file, dst_pub)
    for i, s in enumerate(sentences, 1):
        dst = IMAGES / f"{sid}-{i:02d}.png"
        dst_pub = PUB_IMAGES / f"{sid}-{i:02d}.png"

        if dst.exists():
            if not dst_pub.exists():
                shutil.copy(dst, dst_pub)
            print(f"  Frame {i}/{total_frames}: (Cached) {s.get('en')}")
            continue

        tasks.append((i, s, dst, dst_pub))

    if not tasks:
        print(f"✨ All {total_frames} frames already exist for {sid}!")
        return

    print(f"\n🚀 Batch queueing {len(tasks)} frames into ComfyUI pipeline...")
    queued_jobs = []  # list of {i, s, dst, dst_pub, prompt_id, t_start}
    for i, s, dst, dst_pub in tasks:
        prompt_text = f"{STYLE}\n\nScene: {s['scene_prompt']}"
        prefix = f"scene_{sid}-{i:02d}"
        wf = build_workflow(prompt_text, prefix, seed, size=size, steps=steps)
        pid = post_prompt(wf)
        queued_jobs.append({
            "idx": i,
            "sentence": s,
            "dst": dst,
            "dst_pub": dst_pub,
            "prompt_id": pid,
            "start_time": time.time(),
        })
        print(f"  + Queued Frame {i:02d} (pid: {pid[:8]}...) -> \"{s['en']}\"")

    # 2. Watcher loop: poll queue and copy images as they finish
    print(f"\n⏳ Pipeline executing in ComfyUI... watching for completions:")
    t_pipeline_start = time.time()
    completed_count = 0
    total_to_generate = len(queued_jobs)

    while completed_count < total_to_generate:
        time.sleep(3)
        for job in queued_jobs:
            if job.get("done"):
                continue

            hist = get_history(job["prompt_id"])
            if hist:
                img_path = extract_output_path(hist)
                if img_path:
                    shutil.copy(img_path, job["dst"])
                    shutil.copy(img_path, job["dst_pub"])
                    elapsed = time.time() - job["start_time"]
                    completed_count += 1
                    job["done"] = True
                    print(
                        f"  ✅ [{completed_count}/{total_to_generate}] Frame {job['idx']:02d} completed in {elapsed:.1f}s: "
                        f"{job['dst'].name} -> {job['sentence']['en']}",
                        flush=True,
                    )
                else:
                    status = hist.get("status", {})
                    raise RuntimeError(f"ComfyUI job failed for Frame {job['idx']}: {status}")

    total_elapsed = time.time() - t_pipeline_start
    avg_per_frame = total_elapsed / total_to_generate if total_to_generate > 0 else 0
    print(f"\n🎉 {sid} finished! Generated {total_to_generate} frames in {total_elapsed/60:.1f}m (Avg: {avg_per_frame:.1f}s/frame)\n")


def main():
    parser = argparse.ArgumentParser(description="High-performance pipeline image generator for scenes.")
    parser.add_argument("scenes", nargs="+", help="Scene IDs (e.g. A1-002 A1-003)")
    parser.add_argument("--size", type=int, default=512, help="Image resolution (default 512)")
    parser.add_argument("--steps", type=int, default=14, help="Sampling steps (default 14)")
    args = parser.parse_args()

    IMAGES.mkdir(parents=True, exist_ok=True)
    PUB_IMAGES.mkdir(parents=True, exist_ok=True)

    for sid in args.scenes:
        process_scene_pipeline(sid, size=args.size, steps=args.steps)


if __name__ == "__main__":
    main()
