"""Build a comprehensive, interactive standalone HTML review page for A1 graded scenes."""
import html
import json
import os
import pathlib
import re

ROOT = pathlib.Path("/Users/mac/Documents/codes/englishtest")
SCRIPTS = ROOT / "scripts" / "sentences"
OUT = SCRIPTS / "out"
REVIEWED_DIR = OUT / "reviewed"
DRAFTS_DIR = OUT / "drafts"

# Load words
import sys
sys.path.insert(0, str(SCRIPTS))
from lexicon import load_words

print("Loading lexicon...")
all_words = load_words()
words_map = {w["id"]: w for w in all_words}

# Load review logs
print("Loading review logs...")
with open(OUT / "review_log.json", "r", encoding="utf-8") as f:
    review_logs = json.load(f)

# Group review logs by scene_id and sentence index i
logs_by_scene = {}
for log in review_logs:
    sid = log["scene_id"]
    if sid not in logs_by_scene:
        logs_by_scene[sid] = {}
    logs_by_scene[sid][log["i"]] = log

# Load reviewed scenes
print("Loading reviewed scenes...")
scenes = []
reviewed_files = sorted(REVIEWED_DIR.glob("*.json"))

for rf in reviewed_files:
    with open(rf, "r", encoding="utf-8") as f:
        sc = json.load(f)
    
    sid = sc["scene_id"]
    # Check if draft exists
    draft_file = DRAFTS_DIR / f"{sid}.json"
    draft_sc = None
    if draft_file.exists():
        with open(draft_file, "r", encoding="utf-8") as f:
            draft_sc = json.load(f)
            
    sc["draft"] = draft_sc
    sc["logs"] = logs_by_scene.get(sid, {})
    
    # Collect word dictionary info for targets and review_words
    word_info = {}
    for wid in sc.get("targets", []):
        if wid in words_map:
            w = words_map[wid]
            word_info[wid] = {
                "word": w["word"],
                "pos": w["pos"],
                "senses": [s["zh"] for s in w["senses"]],
                "en_senses": [s["en"] for s in w["senses"]]
            }
    for wid in sc.get("review_words", []):
        if wid in words_map and wid not in word_info:
            w = words_map[wid]
            word_info[wid] = {
                "word": w["word"],
                "pos": w["pos"],
                "senses": [s["zh"] for s in w["senses"]],
                "en_senses": [s["en"] for s in w["senses"]]
            }
    sc["word_info"] = word_info
    scenes.append(sc)

print(f"Loaded {len(scenes)} scenes.")

# Embed as JSON into standalone HTML
data_json = json.dumps(scenes, ensure_ascii=False)

html_content = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>A1 Graded Scenes Review · 分级情境例句审核台</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0c0d0e;
      --card-bg: #141618;
      --card-border: #22262a;
      --card-hover: #1a1d20;
      --sidebar-bg: #0f1113;
      --text-main: #f0f3f6;
      --text-sub: #9aa2ab;
      --text-dim: #5c646e;
      --accent: #3b82f6;
      --accent-glow: rgba(59, 130, 246, 0.15);
      --green: #10b981;
      --green-glow: rgba(16, 185, 129, 0.15);
      --yellow: #f59e0b;
      --yellow-glow: rgba(245, 158, 11, 0.15);
      --red: #ef4444;
      --purple: #a855f7;
      --font-sans: 'Plus Jakarta Sans', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }

    /* Top Navigation Bar */
    header {
      height: 60px;
      background: var(--sidebar-bg);
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 20px;
      z-index: 10;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-badge {
      background: #1e293b;
      color: #60a5fa;
      border: 1px solid #2563eb40;
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 6px;
      letter-spacing: 0.05em;
    }

    .brand h1 {
      font-size: 15px;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .brand h1 span {
      color: var(--text-sub);
      font-weight: 400;
      font-size: 13px;
    }

    .header-stats {
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 13px;
    }

    .stat-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      background: var(--card-bg);
      padding: 4px 12px;
      border-radius: 20px;
      border: 1px solid var(--card-border);
      color: var(--text-sub);
    }

    .stat-pill strong {
      color: var(--text-main);
      font-weight: 600;
      font-family: var(--font-mono);
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .btn {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 12px;
      font-weight: 600;
      padding: 6px 12px;
      border-radius: 8px;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
      user-select: none;
    }

    .btn:hover {
      background: var(--card-hover);
      border-color: #38414a;
    }

    .btn:active {
      transform: translateY(1px);
    }

    .btn-primary {
      background: #2563eb;
      border-color: #3b82f6;
      color: #ffffff;
    }
    .btn-primary:hover {
      background: #1d4ed8;
      border-color: #60a5fa;
    }

    .btn-success {
      background: #065f46;
      border-color: #10b981;
      color: #ecfdf5;
    }
    .btn-success:hover {
      background: #047857;
    }

    .btn-warning {
      background: #78350f;
      border-color: #f59e0b;
      color: #fffbeb;
    }
    .btn-warning:hover {
      background: #92400e;
    }

    /* Main Container */
    .app-body {
      display: flex;
      flex: 1;
      overflow: hidden;
      height: calc(100vh - 60px);
    }

    /* Sidebar */
    aside {
      width: 340px;
      background: var(--sidebar-bg);
      border-right: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .search-filter-box {
      padding: 14px 16px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .search-input-wrapper {
      position: relative;
    }

    .search-input-wrapper input {
      width: 100%;
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-main);
      font-size: 13px;
      padding: 8px 12px 8px 32px;
      border-radius: 8px;
      outline: none;
      transition: border-color 0.15s;
    }

    .search-input-wrapper input:focus {
      border-color: var(--accent);
    }

    .search-icon {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-dim);
      font-size: 12px;
      pointer-events: none;
    }

    .filter-pills {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      scrollbar-width: none;
      padding-bottom: 2px;
    }
    .filter-pills::-webkit-scrollbar { display: none; }

    .filter-chip {
      font-size: 11px;
      font-weight: 500;
      padding: 3px 8px;
      border-radius: 12px;
      background: var(--card-bg);
      color: var(--text-sub);
      border: 1px solid var(--card-border);
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
    }

    .filter-chip.active {
      background: #1e293b;
      color: #93c5fd;
      border-color: #3b82f6;
    }

    .topic-select {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      color: var(--text-sub);
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 6px;
      outline: none;
    }

    .scene-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .scene-item {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.15s;
      border: 1px solid transparent;
      position: relative;
    }

    .scene-item:hover {
      background: var(--card-hover);
    }

    .scene-item.active {
      background: #1a2230;
      border-color: #2563eb60;
    }

    .scene-status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--text-dim);
      margin-top: 6px;
      flex-shrink: 0;
    }

    .scene-status-dot.approved {
      background: var(--green);
      box-shadow: 0 0 6px var(--green-glow);
    }

    .scene-status-dot.flagged {
      background: var(--yellow);
      box-shadow: 0 0 6px var(--yellow-glow);
    }

    .scene-item-content {
      flex: 1;
      min-width: 0;
    }

    .scene-item-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 2px;
    }

    .scene-item-id {
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 700;
      color: var(--text-main);
    }

    .scene-item-topic {
      font-size: 10px;
      color: var(--text-dim);
      background: var(--card-bg);
      padding: 1px 6px;
      border-radius: 4px;
      border: 1px solid var(--card-border);
      text-transform: capitalize;
    }

    .scene-item-title-en {
      font-size: 13px;
      font-weight: 600;
      color: var(--text-main);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .scene-item-title-zh {
      font-size: 11px;
      color: var(--text-sub);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .scene-item-badges {
      display: flex;
      gap: 6px;
      margin-top: 4px;
      font-size: 10px;
      color: var(--text-dim);
    }

    /* Main Content View */
    main {
      flex: 1;
      overflow-y: auto;
      background: var(--bg);
      padding: 24px 32px;
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .scene-header-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .scene-top-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
    }

    .scene-meta-group {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 8px;
    }

    .badge {
      font-size: 11px;
      font-weight: 700;
      font-family: var(--font-mono);
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .badge-level {
      background: #1e3a8a;
      color: #93c5fd;
      border: 1px solid #3b82f640;
    }

    .badge-topic {
      background: #312e81;
      color: #c4b5fd;
      border: 1px solid #8b5cf640;
    }

    .badge-reviewed {
      background: #064e3b;
      color: #6ee7b7;
      border: 1px solid #10b98140;
    }

    .scene-title-h2 {
      font-size: 22px;
      font-weight: 800;
      color: var(--text-main);
      display: flex;
      align-items: baseline;
      gap: 12px;
    }

    .scene-title-zh {
      font-size: 16px;
      font-weight: 500;
      color: var(--text-sub);
    }

    .scene-setting {
      color: var(--text-sub);
      font-size: 13px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .scene-characters {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }

    .char-card {
      background: #191c20;
      border: 1px solid var(--card-border);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .char-avatar {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      background: #27272a;
      color: #e4e4e7;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 11px;
    }

    .char-info strong {
      color: var(--text-main);
      margin-right: 4px;
    }

    .char-info span {
      color: var(--text-sub);
    }

    /* Target Words Box */
    .words-section {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 16px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .words-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-sub);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .words-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .word-chip {
      background: #181b1e;
      border: 1px solid var(--card-border);
      padding: 5px 10px;
      border-radius: 8px;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .word-chip:hover {
      background: #22262b;
      border-color: #3b82f6;
      transform: translateY(-1px);
    }

    .word-chip.highlighted {
      background: #1e3a8a;
      border-color: #60a5fa;
      color: #ffffff;
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.3);
    }

    .word-chip strong {
      color: var(--text-main);
    }

    .word-chip .word-pos {
      color: #60a5fa;
      font-family: var(--font-mono);
      font-size: 10px;
    }

    .word-chip .word-zh {
      color: var(--text-sub);
      font-size: 11px;
    }

    .review-chip {
      background: #231c2c;
      border-color: #581c8740;
    }
    .review-chip .word-pos {
      color: #c084fc;
    }

    /* Sentences Section */
    .sentences-list {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .sentence-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      position: relative;
      transition: border-color 0.15s;
    }

    .sentence-card:hover {
      border-color: #31363c;
    }

    .sentence-top {
      display: flex;
      align-items: flex-start;
      gap: 14px;
    }

    .sentence-num {
      width: 26px;
      height: 26px;
      border-radius: 6px;
      background: #1f2429;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 700;
      flex-shrink: 0;
    }

    .sentence-texts {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .sentence-en {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.5;
      letter-spacing: -0.01em;
    }

    .sentence-en mark {
      background: rgba(59, 130, 246, 0.25);
      color: #93c5fd;
      padding: 1px 4px;
      border-radius: 4px;
      font-weight: 700;
      border-bottom: 2px solid #3b82f6;
    }

    .sentence-en mark.target-focus {
      background: #2563eb;
      color: #ffffff;
      animation: pulse 1s infinite alternate;
    }

    @keyframes pulse {
      from { box-shadow: 0 0 4px #3b82f6; }
      to { box-shadow: 0 0 12px #60a5fa; }
    }

    .sentence-zh {
      font-size: 14px;
      color: var(--text-sub);
      line-height: 1.4;
    }

    .sentence-actions {
      display: flex;
      gap: 6px;
      flex-shrink: 0;
    }

    .icon-btn {
      width: 32px;
      height: 32px;
      border-radius: 8px;
      background: #181b1e;
      border: 1px solid var(--card-border);
      color: var(--text-sub);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.15s;
    }

    .icon-btn:hover {
      background: var(--card-hover);
      color: var(--text-main);
      border-color: #3b82f6;
    }

    /* Scene Prompt Box */
    .prompt-box {
      background: #121416;
      border: 1px solid #1c2024;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 12px;
      color: var(--text-dim);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .prompt-box span {
      flex: 1;
      font-family: var(--font-mono);
      font-size: 11px;
      line-height: 1.4;
      color: #8b949e;
    }

    .copy-chip {
      cursor: pointer;
      color: #58a6ff;
      font-size: 11px;
      white-space: nowrap;
      user-select: none;
    }
    .copy-chip:hover {
      text-decoration: underline;
    }

    /* Diff Container */
    .diff-box {
      background: #171a1d;
      border: 1px solid #2d333b;
      border-radius: 8px;
      padding: 10px 14px;
      font-size: 13px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .diff-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
      color: var(--text-dim);
      font-weight: 600;
    }

    .diff-reason {
      background: #374151;
      color: #e5e7eb;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }

    .diff-line {
      display: flex;
      align-items: baseline;
      gap: 8px;
      font-size: 13px;
      line-height: 1.4;
    }

    .diff-line.before {
      color: #f87171;
      text-decoration: line-through;
      opacity: 0.8;
    }

    .diff-line.after {
      color: #34d399;
      font-weight: 500;
    }

    .diff-tag {
      font-size: 10px;
      font-family: var(--font-mono);
      font-weight: 700;
      padding: 1px 4px;
      border-radius: 3px;
      flex-shrink: 0;
    }
    .diff-line.before .diff-tag {
      background: #7f1d1d;
      color: #fca5a5;
    }
    .diff-line.after .diff-tag {
      background: #064e3b;
      color: #6ee7b7;
    }

    /* Reviewer Notes & Decision Area */
    .review-action-panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px 24px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .review-notes-textarea {
      width: 100%;
      height: 80px;
      background: #111315;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 12px;
      color: var(--text-main);
      font-family: var(--font-sans);
      font-size: 13px;
      outline: none;
      resize: vertical;
      transition: border-color 0.15s;
    }

    .review-notes-textarea:focus {
      border-color: var(--accent);
    }

    .review-bottom-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    /* Modal */
    .modal-backdrop {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      z-index: 100;
      align-items: center;
      justify-content: center;
    }

    .modal-card {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      width: 650px;
      max-width: 90vw;
      max-height: 85vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }

    .modal-header {
      padding: 16px 20px;
      border-bottom: 1px solid var(--card-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-body {
      padding: 20px;
      overflow-y: auto;
      flex: 1;
    }

    .modal-textarea {
      width: 100%;
      height: 350px;
      background: #111315;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 12px;
      color: var(--text-main);
      font-family: var(--font-mono);
      font-size: 12px;
      line-height: 1.5;
      outline: none;
      resize: none;
    }

    /* Toast Notification */
    #toast {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: #1e293b;
      color: #f8fafc;
      border: 1px solid #334155;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 13px;
      font-weight: 500;
      box-shadow: 0 8px 24px rgba(0,0,0,0.4);
      transform: translateY(100px);
      opacity: 0;
      transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 999;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    #toast.show {
      transform: translateY(0);
      opacity: 1;
    }

    /* Keyboard Shortcuts Legend */
    .shortcuts-hint {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 11px;
      color: var(--text-dim);
    }

    kbd {
      background: #1f2429;
      border: 1px solid #31363c;
      padding: 1px 5px;
      border-radius: 4px;
      font-family: var(--font-mono);
      color: var(--text-sub);
    }
  </style>
</head>
<body>

  <!-- Top Bar -->
  <header>
    <div class="brand">
      <div class="brand-badge">A1 CORPUS</div>
      <h1>Scenes Review <span>分级情境例句审核台</span></h1>
    </div>

    <div class="header-stats">
      <div class="stat-pill">
        <span>Reviewed:</span>
        <strong id="statReviewed">0 / 60</strong>
      </div>
      <div class="stat-pill">
        <span style="color:var(--green)">✓ Approved:</span>
        <strong id="statApproved" style="color:var(--green)">0</strong>
      </div>
      <div class="stat-pill">
        <span style="color:var(--yellow)">⚑ Flagged:</span>
        <strong id="statFlagged" style="color:var(--yellow)">0</strong>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn" onclick="openExportModal()">
        <span>📋</span> Export Notes
      </button>
      <button class="btn btn-primary" onclick="toggleDiffMode()" id="diffToggleBtn">
        <span>⚖️</span> Compare Draft
      </button>
    </div>
  </header>

  <!-- Body -->
  <div class="app-body">
    <!-- Sidebar -->
    <aside>
      <div class="search-filter-box">
        <div class="search-input-wrapper">
          <span class="search-icon">🔍</span>
          <input type="text" id="searchInput" placeholder="Search word, title, text, character..." oninput="onSearchChange()">
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <select id="topicFilter" class="topic-select" onchange="onFilterChange()">
            <option value="all">All Topics (全部主题)</option>
          </select>
          <div class="filter-pills">
            <div class="filter-chip active" data-filter="all" onclick="setFilter('all')">All</div>
            <div class="filter-chip" data-filter="pending" onclick="setFilter('pending')">Pending</div>
            <div class="filter-chip" data-filter="approved" onclick="setFilter('approved')">✓ Approved</div>
            <div class="filter-chip" data-filter="flagged" onclick="setFilter('flagged')">⚑ Flagged</div>
          </div>
        </div>
      </div>

      <div class="scene-list" id="sceneList">
        <!-- Rendered via JS -->
      </div>
    </aside>

    <!-- Main Workspace -->
    <main id="mainWorkspace">
      <!-- Rendered via JS -->
    </main>
  </div>

  <!-- Export Modal -->
  <div class="modal-backdrop" id="exportModal">
    <div class="modal-card">
      <div class="modal-header">
        <h3 style="font-size:15px; font-weight:700;">Export Review Progress & Notes</h3>
        <button class="btn" onclick="closeExportModal()">✕</button>
      </div>
      <div class="modal-body" style="display:flex; flex-direction:column; gap:12px;">
        <div style="display:flex; gap:8px;">
          <button class="btn btn-primary" onclick="generateReport('markdown')">Markdown Format</button>
          <button class="btn" onclick="generateReport('json')">JSON Format</button>
          <button class="btn" onclick="copyReportText()">📋 Copy All</button>
        </div>
        <textarea id="reportTextarea" class="modal-textarea" readonly></textarea>
      </div>
    </div>
  </div>

  <!-- Toast -->
  <div id="toast"></div>

  <script>
    // Embedded Data
    const SCENES = __SCENES_DATA_PLACEHOLDER__;

    // Review status stored in localStorage
    const STORAGE_KEY = 'a1_scenes_review_state';
    let reviewState = {};
    try {
      reviewState = JSON.parse(localStorage.getItem(STORAGE_KEY)) || {};
    } catch (e) {
      reviewState = {};
    }

    let currentIndex = 0;
    let currentFilter = 'all';
    let currentTopic = 'all';
    let searchQuery = '';
    let showDiff = false;
    let selectedWord = null;

    // Save state
    function saveState() {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reviewState));
      updateStats();
      renderSidebar();
    }

    function showToast(msg) {
      const toast = document.getElementById('toast');
      toast.textContent = msg;
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2000);
    }

    // Initialize Topics dropdown
    function initTopics() {
      const topics = new Set();
      SCENES.forEach(s => {
        if (s.topic) topics.add(s.topic);
      });
      const select = document.getElementById('topicFilter');
      Array.from(topics).sort().forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t.charAt(0).toUpperCase() + t.slice(1);
        select.appendChild(opt);
      });
    }

    // Update Stats
    function updateStats() {
      const total = SCENES.length;
      let approved = 0;
      let flagged = 0;
      SCENES.forEach(s => {
        const st = reviewState[s.scene_id]?.status;
        if (st === 'approved') approved++;
        else if (st === 'flagged') flagged++;
      });
      document.getElementById('statReviewed').textContent = `${approved + flagged} / ${total}`;
      document.getElementById('statApproved').textContent = approved;
      document.getElementById('statFlagged').textContent = flagged;
    }

    // Filter scenes
    function getFilteredScenes() {
      return SCENES.filter(s => {
        const st = reviewState[s.scene_id]?.status || 'pending';
        if (currentFilter === 'approved' && st !== 'approved') return false;
        if (currentFilter === 'flagged' && st !== 'flagged') return false;
        if (currentFilter === 'pending' && (st === 'approved' || st === 'flagged')) return false;

        if (currentTopic !== 'all' && s.topic !== currentTopic) return false;

        if (searchQuery) {
          const q = searchQuery.toLowerCase();
          const inId = s.scene_id.toLowerCase().includes(q);
          const inTitleEn = s.title.toLowerCase().includes(q);
          const inTitleZh = (s.title_zh || '').includes(q);
          const inTargets = (s.targets || []).some(t => t.toLowerCase().includes(q));
          const inSentences = (s.sentences || []).some(sent => 
            sent.en.toLowerCase().includes(q) || (sent.zh || '').includes(q)
          );
          if (!inId && !inTitleEn && !inTitleZh && !inTargets && !inSentences) return false;
        }

        return true;
      });
    }

    // Render Sidebar
    function renderSidebar() {
      const container = document.getElementById('sceneList');
      const filtered = getFilteredScenes();
      container.innerHTML = '';

      if (filtered.length === 0) {
        container.innerHTML = `<div style="text-align:center; padding:30px 10px; color:var(--text-dim); font-size:13px;">No matching scenes found.</div>`;
        return;
      }

      filtered.forEach(s => {
        const actualIndex = SCENES.findIndex(x => x.scene_id === s.scene_id);
        const isActive = actualIndex === currentIndex;
        const st = reviewState[s.scene_id]?.status || 'pending';
        const notes = reviewState[s.scene_id]?.notes || '';
        const editCount = Object.keys(s.logs || {}).length;

        const div = document.createElement('div');
        div.className = `scene-item ${isActive ? 'active' : ''}`;
        div.onclick = () => selectScene(actualIndex);

        let dotClass = '';
        if (st === 'approved') dotClass = 'approved';
        else if (st === 'flagged') dotClass = 'flagged';

        div.innerHTML = `
          <div class="scene-status-dot ${dotClass}"></div>
          <div class="scene-item-content">
            <div class="scene-item-header">
              <span class="scene-item-id">${s.scene_id}</span>
              <span class="scene-item-topic">${s.topic}</span>
            </div>
            <div class="scene-item-title-en">${s.title}</div>
            <div class="scene-item-title-zh">${s.title_zh || ''}</div>
            <div class="scene-item-badges">
              <span>${(s.sentences || []).length} sentences</span>
              <span>•</span>
              <span>${(s.targets || []).length} targets</span>
              ${editCount > 0 ? `<span>•</span><span style="color:#60a5fa">${editCount} edits</span>` : ''}
              ${notes ? `<span>•</span><span style="color:#f59e0b">📝 note</span>` : ''}
            </div>
          </div>
        `;
        container.appendChild(div);
      });
    }

    // Select Scene
    function selectScene(index) {
      currentIndex = index;
      selectedWord = null;
      renderSidebar();
      renderMain();
      // Scroll active sidebar item into view
      const activeEl = document.querySelector('.scene-item.active');
      if (activeEl) {
        activeEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }

    function toggleDiffMode() {
      showDiff = !showDiff;
      const btn = document.getElementById('diffToggleBtn');
      if (showDiff) {
        btn.classList.add('btn-primary');
        btn.innerHTML = `<span>✓</span> Diff Mode ON`;
      } else {
        btn.classList.remove('btn-primary');
        btn.innerHTML = `<span>⚖️</span> Compare Draft`;
      }
      renderMain();
    }

    function markStatus(status) {
      const s = SCENES[currentIndex];
      if (!reviewState[s.scene_id]) reviewState[s.scene_id] = {};
      
      if (reviewState[s.scene_id].status === status) {
        // Toggle off
        delete reviewState[s.scene_id].status;
        showToast(`Reset ${s.scene_id} status`);
      } else {
        reviewState[s.scene_id].status = status;
        showToast(`Marked ${s.scene_id} as ${status}`);
        // If approved, optionally jump next
        if (status === 'approved' && currentIndex < SCENES.length - 1) {
          setTimeout(() => selectScene(currentIndex + 1), 250);
        }
      }
      saveState();
      renderMain();
    }

    function onNotesChange(val) {
      const s = SCENES[currentIndex];
      if (!reviewState[s.scene_id]) reviewState[s.scene_id] = {};
      reviewState[s.scene_id].notes = val;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(reviewState));
      renderSidebar();
    }

    // Highlight text with target words
    function formatSentenceText(text, targets, focusWord) {
      if (!targets || targets.length === 0) return escapeHtml(text);
      
      // Escape HTML first
      let res = escapeHtml(text);

      // Highlight target words
      // Sort targets by length descending to match phrases first
      const sorted = [...targets].sort((a,b) => b.length - a.length);
      sorted.forEach(t => {
        const cleanT = t.replace(/-/g, ' ');
        // Regex with word boundary or boundary-like
        const re = new RegExp(`\\\\b(${cleanT}|${t})\\\\b`, 'gi');
        res = res.replace(re, (match) => {
          const isFocus = focusWord && (match.toLowerCase() === focusWord.toLowerCase() || focusWord.toLowerCase().includes(match.toLowerCase()));
          const focusCls = isFocus ? 'target-focus' : '';
          return `<mark class="${focusCls}">${match}</mark>`;
        });
      });
      return res;
    }

    function escapeHtml(str) {
      if (!str) return '';
      return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    // Text to Speech
    function speakText(text) {
      if (!('speechSynthesis' in window)) {
        alert('Text-to-speech not supported in this browser.');
        return;
      }
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = 'en-US';
      u.rate = 0.95;
      window.speechSynthesis.speak(u);
    }

    function speakEntireScene() {
      const s = SCENES[currentIndex];
      if (!s.sentences) return;
      window.speechSynthesis.cancel();
      s.sentences.forEach((sent, idx) => {
        const u = new SpeechSynthesisUtterance(sent.en);
        u.lang = 'en-US';
        u.rate = 0.95;
        window.speechSynthesis.speak(u);
      });
      showToast('Playing scene audio...');
    }

    function copyToClipboard(text, msg = 'Copied to clipboard!') {
      navigator.clipboard.writeText(text).then(() => {
        showToast(msg);
      });
    }

    // Word selection
    function toggleWordHighlight(wordId) {
      if (selectedWord === wordId) {
        selectedWord = null;
      } else {
        selectedWord = wordId;
      }
      renderMain();
    }

    // Render Main Area
    function renderMain() {
      const container = document.getElementById('mainWorkspace');
      const s = SCENES[currentIndex];
      if (!s) return;

      const st = reviewState[s.scene_id]?.status || 'pending';
      const notes = reviewState[s.scene_id]?.notes || '';
      const draft = s.draft;
      const logs = s.logs || {};

      let html = `
        <!-- Scene Header -->
        <div class="scene-header-card">
          <div class="scene-top-row">
            <div>
              <div class="scene-meta-group">
                <span class="badge badge-level">${s.level}</span>
                <span class="badge badge-topic">${s.topic}</span>
                <span class="badge" style="background:#27272a; color:#a1a1aa;">${s.scene_id}</span>
                <span class="badge badge-reviewed">Reviewed by ${s.reviewed_by || 'Opus 5.5'}</span>
              </div>
              <h2 class="scene-title-h2">
                ${escapeHtml(s.title)}
                <span class="scene-title-zh">${escapeHtml(s.title_zh || '')}</span>
              </h2>
            </div>

            <!-- Header Action Controls -->
            <div style="display:flex; align-items:center; gap:8px;">
              <button class="btn ${st === 'approved' ? 'btn-success' : ''}" onclick="markStatus('approved')" title="Shortcut: 'a'">
                <span>✓</span> ${st === 'approved' ? 'Approved' : 'Approve'}
              </button>
              <button class="btn ${st === 'flagged' ? 'btn-warning' : ''}" onclick="markStatus('flagged')" title="Shortcut: 'f'">
                <span>⚑</span> ${st === 'flagged' ? 'Flagged' : 'Flag'}
              </button>
              <button class="btn" onclick="speakEntireScene()" title="Read all sentences aloud">
                <span>🔊</span> Listen All
              </button>
              <button class="btn" onclick="copySceneJSON()">
                <span>{ }</span> Copy JSON
              </button>
            </div>
          </div>

          <!-- Setting & Characters -->
          <div class="scene-setting">
            <strong>Setting:</strong> ${escapeHtml(s.setting || 'Not specified')}
          </div>

          <div class="scene-characters">
            ${(s.characters || []).map(c => `
              <div class="char-card">
                <div class="char-avatar">${c.name ? c.name[0].toUpperCase() : '?'}</div>
                <div class="char-info">
                  <strong>${escapeHtml(c.name)}:</strong>
                  <span>${escapeHtml(c.look || '')}</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Targets & Review Words Panel -->
        <div class="words-section">
          <div class="words-header">
            <span>Target Words (${(s.targets || []).length} 目标核心词)</span>
            <span style="font-size:11px; color:var(--text-dim);">Click chip to locate in sentences</span>
          </div>
          <div class="words-grid">
            ${(s.targets || []).map(wid => {
              const info = s.word_info?.[wid];
              const isSelected = selectedWord === wid;
              return `
                <div class="word-chip ${isSelected ? 'highlighted' : ''}" onclick="toggleWordHighlight('${wid}')">
                  <strong>${info ? info.word : wid}</strong>
                  ${info?.pos ? `<span class="word-pos">${info.pos.join('/')}</span>` : ''}
                  ${info?.senses ? `<span class="word-zh">${info.senses[0]}</span>` : ''}
                </div>
              `;
            }).join('')}
          </div>

          ${(s.review_words && s.review_words.length > 0) ? `
            <div class="words-header" style="margin-top:8px;">
              <span>Review Words (${s.review_words.length} 复习旧词)</span>
            </div>
            <div class="words-grid">
              ${s.review_words.map(wid => {
                const info = s.word_info?.[wid];
                const isSelected = selectedWord === wid;
                return `
                  <div class="word-chip review-chip ${isSelected ? 'highlighted' : ''}" onclick="toggleWordHighlight('${wid}')">
                    <strong>${info ? info.word : wid}</strong>
                    ${info?.pos ? `<span class="word-pos">${info.pos.join('/')}</span>` : ''}
                    ${info?.senses ? `<span class="word-zh">${info.senses[0]}</span>` : ''}
                  </div>
                `;
              }).join('')}
            </div>
          ` : ''}
        </div>

        <!-- Sentences Section -->
        <div class="sentences-list">
          ${(s.sentences || []).map((sent, i) => {
            const log = logs[i];
            const draftSent = draft?.sentences?.[i];
            const hasDiff = !!log || (draftSent && draftSent.en !== sent.en);

            return `
              <div class="sentence-card">
                <div class="sentence-top">
                  <div class="sentence-num">${i + 1}</div>
                  <div class="sentence-texts">
                    <div class="sentence-en">
                      ${formatSentenceText(sent.en, s.targets, selectedWord)}
                    </div>
                    <div class="sentence-zh">${escapeHtml(sent.zh || '')}</div>
                  </div>
                  <div class="sentence-actions">
                    <button class="icon-btn" onclick="speakText('${escapeHtml(sent.en.replace(/'/g, "\\\\'"))}')" title="Play audio">
                      🔊
                    </button>
                    <button class="icon-btn" onclick="copyToClipboard('${escapeHtml(sent.en.replace(/'/g, "\\\\'"))}')" title="Copy sentence">
                      📋
                    </button>
                  </div>
                </div>

                <!-- Scene Prompt -->
                ${sent.scene_prompt ? `
                  <div class="prompt-box">
                    <span><strong>Visual Prompt:</strong> ${escapeHtml(sent.scene_prompt)}</span>
                    <span class="copy-chip" onclick="copyToClipboard('${escapeHtml(sent.scene_prompt.replace(/'/g, "\\\\'"))}')">Copy Prompt</span>
                  </div>
                ` : ''}

                <!-- Diff view (if showDiff is active or sentence was edited) -->
                ${(showDiff || hasDiff) && draftSent && draftSent.en !== sent.en ? `
                  <div class="diff-box">
                    <div class="diff-header">
                      <span>REVISION FROM DRAFT</span>
                      ${log?.reason ? `<span class="diff-reason">原因: ${escapeHtml(log.reason)}</span>` : ''}
                    </div>
                    <div class="diff-line before">
                      <span class="diff-tag">DRAFT</span>
                      <span>${escapeHtml(draftSent.en)}</span>
                    </div>
                    <div class="diff-line after">
                      <span class="diff-tag">OPUS</span>
                      <span>${escapeHtml(sent.en)}</span>
                    </div>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>

        <!-- Reviewer Notes & Navigation Panel -->
        <div class="review-action-panel">
          <div style="font-size:13px; font-weight:700; color:var(--text-main); display:flex; justify-content:space-between; align-items:center;">
            <span>Reviewer Notes & Feedback (审核备注)</span>
            <span style="font-size:11px; color:var(--text-dim);">Auto-saved locally</span>
          </div>
          <textarea 
            class="review-notes-textarea" 
            placeholder="Write comments, issues, or replacement sentence ideas here..."
            oninput="onNotesChange(this.value)"
          >${escapeHtml(notes)}</textarea>

          <div class="review-bottom-bar">
            <div class="shortcuts-hint">
              <span>Shortcuts:</span>
              <kbd>→</kbd> Next
              <kbd>←</kbd> Prev
              <kbd>A</kbd> Approve
              <kbd>F</kbd> Flag
              <kbd>S</kbd> Audio
            </div>

            <div style="display:flex; gap:10px;">
              <button class="btn" onclick="prevScene()" ${currentIndex === 0 ? 'disabled style="opacity:0.4;"' : ''}>
                ← Previous Scene
              </button>
              <button class="btn btn-primary" onclick="nextScene()" ${currentIndex === SCENES.length - 1 ? 'disabled style="opacity:0.4;"' : ''}>
                Next Scene →
              </button>
            </div>
          </div>
        </div>
      `;

      container.innerHTML = html;
      container.scrollTop = 0;
    }

    function prevScene() {
      if (currentIndex > 0) {
        selectScene(currentIndex - 1);
      }
    }

    function nextScene() {
      if (currentIndex < SCENES.length - 1) {
        selectScene(currentIndex + 1);
      }
    }

    function copySceneJSON() {
      const s = SCENES[currentIndex];
      const clean = { ...s };
      delete clean.draft;
      delete clean.logs;
      delete clean.word_info;
      copyToClipboard(JSON.stringify(clean, null, 2), `Copied ${s.scene_id} JSON!`);
    }

    // Search and Filters
    function onSearchChange() {
      searchQuery = document.getElementById('searchInput').value.trim();
      renderSidebar();
    }

    function onFilterChange() {
      currentTopic = document.getElementById('topicFilter').value;
      renderSidebar();
    }

    function setFilter(flt) {
      currentFilter = flt;
      document.querySelectorAll('.filter-chip').forEach(c => {
        c.classList.toggle('active', c.dataset.filter === flt);
      });
      renderSidebar();
    }

    // Modal Export
    function openExportModal() {
      document.getElementById('exportModal').style.display = 'flex';
      generateReport('markdown');
    }

    function closeExportModal() {
      document.getElementById('exportModal').style.display = 'none';
    }

    function generateReport(format) {
      const approved = [];
      const flagged = [];
      const pending = [];

      SCENES.forEach(s => {
        const item = reviewState[s.scene_id];
        const record = {
          scene_id: s.scene_id,
          title: s.title,
          title_zh: s.title_zh,
          status: item?.status || 'pending',
          notes: item?.notes || ''
        };
        if (record.status === 'approved') approved.push(record);
        else if (record.status === 'flagged') flagged.push(record);
        else pending.push(record);
      });

      const textarea = document.getElementById('reportTextarea');
      if (format === 'markdown') {
        let md = `# A1 Sentences Corpus Review Report\\n\\n`;
        md += `**Date**: ${new Date().toLocaleDateString()}\\n`;
        md += `**Total Scenes**: 60 | **Approved**: ${approved.length} | **Flagged**: ${flagged.length} | **Pending**: ${pending.length}\\n\\n`;

        if (flagged.length > 0) {
          md += `## ⚑ Flagged Scenes (Needs Attention)\\n\\n`;
          flagged.forEach(f => {
            md += `- **${f.scene_id}** [${f.title} / ${f.title_zh}]: ${f.notes || '_No notes entered_'}\\n`;
          });
          md += `\\n`;
        }

        if (approved.length > 0) {
          md += `## ✓ Approved Scenes (${approved.length})\\n\\n`;
          approved.forEach(a => {
            md += `- **${a.scene_id}** [${a.title}]${a.notes ? ' - Note: ' + a.notes : ''}\\n`;
          });
          md += `\\n`;
        }

        if (pending.length > 0) {
          md += `## ⚪ Pending Review (${pending.length})\\n\\n`;
          pending.forEach(p => {
            md += `- **${p.scene_id}** [${p.title}]\\n`;
          });
        }
        textarea.value = md;
      } else {
        textarea.value = JSON.stringify({ approved, flagged, pending }, null, 2);
      }
    }

    function copyReportText() {
      const textarea = document.getElementById('reportTextarea');
      copyToClipboard(textarea.value, 'Report copied to clipboard!');
    }

    // Keyboard Shortcuts
    window.addEventListener('keydown', (e) => {
      // Ignore if typing in input or textarea
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 'ArrowRight' || e.key === 'j' || e.key === ']') {
        nextScene();
      } else if (e.key === 'ArrowLeft' || e.key === 'k' || e.key === '[') {
        prevScene();
      } else if (e.key === 'a' || e.key === 'A') {
        markStatus('approved');
      } else if (e.key === 'f' || e.key === 'F') {
        markStatus('flagged');
      } else if (e.key === 's' || e.key === 'S') {
        speakEntireScene();
      } else if (e.key === '/') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
      } else if (e.key === 'Escape') {
        closeExportModal();
      }
    });

    // Startup
    initTopics();
    updateStats();
    renderSidebar();
    renderMain();
  </script>
</body>
</html>
"""

# Replace placeholder with actual data safely
html_content = html_content.replace("__SCENES_DATA_PLACEHOLDER__", data_json)

# Output paths
out_file1 = OUT / "review.html"
out_file2 = ROOT / "public" / "review.html"

out_file1.write_text(html_content, encoding="utf-8")
print(f"Generated review page: {out_file1} ({out_file1.stat().st_size / 1024:.1f} KB)")

out_file2.write_text(html_content, encoding="utf-8")
print(f"Generated review page in public: {out_file2} ({out_file2.stat().st_size / 1024:.1f} KB)")
