import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { StoryPlayer } from "./StoryPlayer";

export interface StoryWord {
  id: string;
  word: string;
  zh: string;
}

export interface StoryFrame {
  en: string;
  zh: string;
  narration: string;
  words: StoryWord[];
}

export interface Story {
  id: string;
  level: string;
  topic: string;
  title: string;
  title_zh: string;
  /** All pictures and recordings exist. */
  ready: boolean;
  sentences: StoryFrame[];
}

export const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export function StoryScenes() {
  const [stories, setStories] = useState<Story[] | null>(null);
  const [failed, setFailed] = useState(false);
  const [topic, setTopic] = useState("all");
  const [active, setActive] = useState<Story | null>(null);

  useEffect(() => {
    fetch(`${BASE}/atlas/story_units.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then((data: Story[]) => setStories(data))
      .catch(() => setFailed(true));
  }, []);

  if (failed) return <p className="muted">故事加载失败，请刷新页面重试。</p>;
  if (!stories) return <div className="spinner" aria-label="加载中" />;

  const ready = stories.filter((s) => s.ready);
  const pending = stories.length - ready.length;
  const topics = [...new Set(ready.map((s) => s.topic))].sort();
  const shown = ready.filter((s) => topic === "all" || s.topic === topic);
  const words = ready.reduce((n, s) => n + s.sentences.reduce((m, f) => m + f.words.length, 0), 0);

  return (
    <section className="story-list">
      <header className="page-head">
        <p className="eyebrow">看图听话 · Picture Stories</p>
        <h1 className="display">先看图，再听懂它。</h1>
        <p className="lede">
          每个故事 5–8 幅图。每幅先听一段画面描述，再听一句故事例句；字幕默认隐藏，听不懂再打开。
          {ready.length > 0 && ` 现在有 ${ready.length} 个故事可以点读，共 ${words} 个生词。`}
        </p>
      </header>

      {topics.length > 1 && (
        <div className="chips">
          <button className={`chip-btn ${topic === "all" ? "is-on" : ""}`} onClick={() => setTopic("all")}>
            全部 {ready.length}
          </button>
          {topics.map((t) => (
            <button key={t} className={`chip-btn ${topic === t ? "is-on" : ""}`} onClick={() => setTopic(t)}>
              {t}
            </button>
          ))}
        </div>
      )}

      <div className="story-grid">
        {shown.map((s) => (
          <button key={s.id} className="story-card" onClick={() => setActive(s)}>
            <img
              className="story-card-img"
              src={`${BASE}/atlas/scene_images/${s.id}-01.png`}
              alt=""
              loading="lazy"
            />
            <span className="story-card-body">
              <span className="story-card-meta">
                {s.id} · {s.topic}
              </span>
              <span className="story-card-title" lang="en">
                {s.title}
              </span>
              <span className="story-card-zh">{s.title_zh}</span>
              <span className="story-card-meta">
                {s.sentences.length} 幅 · {s.sentences.reduce((m, f) => m + f.words.length, 0)} 个生词
              </span>
            </span>
          </button>
        ))}
      </div>

      {pending > 0 && <p className="muted story-pending">另有 {pending} 个故事正在配图和录音。</p>}

      {active && createPortal(<StoryPlayer story={active} onClose={() => setActive(null)} />, document.body)}
    </section>
  );
}
