import { ChevronLeft, ChevronRight, Pause, Play, RotateCcw, Volume2, X } from "lucide-react";
import { Fragment, useCallback, useEffect, useRef, useState } from "react";
import { useAtlas } from "../atlas/context";
import { play, stopAudio } from "../lib/audio";
import { openWord } from "../lib/router";
import { useStore } from "../store/store";
import { BASE, type Story, type StoryFrame, type StoryWord } from "./StoryScenes";

type Track = "narration" | "sentence" | `word:${string}`;

const SUBS_KEY = "story-player:subs";
const RATE_KEY = "story-player:rate";

function readPref(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}

function writePref(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // Private mode: the setting just isn't remembered.
  }
}

const pad = (n: number) => String(n).padStart(2, "0");

/** Splits a sentence so target words (and their inflections) can be marked. */
function markTargets(text: string, words: StoryWord[]) {
  if (!words.length) return [{ text, word: null as StoryWord | null }];
  const alts = words
    .map((w) => w.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .sort((a, b) => b.length - a.length);
  const re = new RegExp(`\\b(${alts.join("|")})[a-z]*\\b`, "gi");
  const parts: { text: string; word: StoryWord | null }[] = [];
  let last = 0;
  for (const m of text.matchAll(re)) {
    const at = m.index ?? 0;
    if (at > last) parts.push({ text: text.slice(last, at), word: null });
    const word = words.find((w) => w.word.toLowerCase() === m[1].toLowerCase()) ?? null;
    parts.push({ text: m[0], word });
    last = at + m[0].length;
  }
  if (last < text.length) parts.push({ text: text.slice(last), word: null });
  return parts;
}

/** Hidden subtitles: one blank per word, so the learner still sees the sentence's shape. */
function Blanks({ text }: { text: string }) {
  return (
    <span className="story-blanks" aria-label="字幕已隐藏">
      {text.split(/\s+/).map((w, i) => (
        <span key={i} className="story-blank" style={{ width: `${Math.max(2, w.length) * 0.55}em` }} />
      ))}
    </span>
  );
}

export function StoryPlayer({ story, onClose }: { story: Story; onClose: () => void }) {
  const atlas = useAtlas();
  const accent = useStore((s) => s.settings.accent);
  const [idx, setIdx] = useState(0);
  const [subs, setSubs] = useState(() => readPref(SUBS_KEY, "off") === "on");
  const [rate, setRate] = useState(() => Number(readPref(RATE_KEY, "1")) || 1);
  const [auto, setAuto] = useState(false);
  const [playing, setPlaying] = useState<Track | null>(null);
  const [deviceVoice, setDeviceVoice] = useState(false);

  const total = story.sentences.length;
  const frame: StoryFrame = story.sentences[idx];
  const session = useRef(0);
  const autoRef = useRef(false);
  const rateRef = useRef(rate);
  rateRef.current = rate;

  const audioUrl = useCallback(
    (i: number, kind: "narration" | "sentence") =>
      `${BASE}/atlas/audio/scenes/${story.id}/${story.id}_${pad(i + 1)}_${kind}.mp3`,
    [story.id],
  );

  const stop = useCallback(() => {
    session.current++;
    stopAudio();
    setPlaying(null);
  }, []);

  /** Plays one track; resolves false if something else took over meanwhile. */
  const playTrack = useCallback(
    async (my: number, track: Track, url: string | null, text: string, voice: "uk" | "us") => {
      setPlaying(track);
      const how = await play(url, text, voice, rateRef.current);
      if (session.current !== my) return false;
      if (how === "device") setDeviceVoice(true);
      setPlaying(null);
      return true;
    },
    [],
  );

  /** Narration, then the story sentence; in auto mode, then the next picture. */
  const playFrame = useCallback(
    async (i: number) => {
      const my = ++session.current;
      const f = story.sentences[i];
      const still = async (ms: number) => {
        await new Promise((r) => setTimeout(r, ms));
        return session.current === my;
      };
      if (!(await playTrack(my, "narration", audioUrl(i, "narration"), f.narration, "uk"))) return;
      if (!(await still(400))) return;
      if (!(await playTrack(my, "sentence", audioUrl(i, "sentence"), f.en, "us"))) return;
      if (!autoRef.current || !(await still(1000))) return;
      if (i < total - 1) setIdx(i + 1);
      else {
        autoRef.current = false;
        setAuto(false);
      }
    },
    [story, total, playTrack, audioUrl],
  );

  const playOne = async (kind: "narration" | "sentence") => {
    autoRef.current = false;
    setAuto(false);
    const my = ++session.current;
    await playTrack(my, kind, audioUrl(idx, kind), kind === "sentence" ? frame.en : frame.narration, kind === "sentence" ? "us" : "uk");
  };

  const playWord = async (w: StoryWord) => {
    autoRef.current = false;
    setAuto(false);
    const ref = atlas.byId.get(w.id);
    const my = ++session.current;
    await playTrack(my, `word:${w.id}`, ref ? atlas.audio(ref, accent) : null, w.word, accent);
  };

  // Each new picture plays on arrival, like turning a page.
  useEffect(() => {
    playFrame(idx);
    return stop;
  }, [idx, playFrame, stop]);

  const go = useCallback(
    (to: number) => {
      if (to < 0 || to >= total) return;
      setIdx(to);
    },
    [total],
  );

  const toggleAuto = useCallback(() => {
    if (autoRef.current) {
      autoRef.current = false;
      setAuto(false);
      stop();
      return;
    }
    autoRef.current = true;
    setAuto(true);
    if (idx === total - 1) setIdx(0);
    else playFrame(idx);
  }, [idx, total, playFrame, stop]);

  const toggleSubs = useCallback(() => {
    setSubs((on) => {
      writePref(SUBS_KEY, on ? "off" : "on");
      return !on;
    });
  }, []);

  const toggleRate = () => {
    const next = rate === 1 ? 0.75 : 1;
    setRate(next);
    writePref(RATE_KEY, String(next));
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      // The word entry handles Escape first and may already be gone from the DOM.
      if (e.defaultPrevented) return;
      const t = e.target;
      if (t instanceof Element && t.closest("input, textarea, select, [contenteditable]")) return;
      // A word entry opened from here owns the keyboard until it closes.
      if (document.querySelector(".sheet-root")) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "ArrowRight") go(idx + 1);
      else if (e.key === "ArrowLeft") go(idx - 1);
      else if (e.key === "Escape") onClose();
      else if (e.key === "c" || e.key === "C") toggleSubs();
      else if (e.key === " ") toggleAuto();
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [idx, go, onClose, toggleSubs, toggleAuto]);

  const close = () => {
    stop();
    onClose();
  };

  return (
    <div className="story-player" role="dialog" aria-modal="true" aria-label={`${story.title} 点读`}>
      <header className="story-bar">
        <button className="icon-btn" onClick={close} aria-label="关闭">
          <X size={20} />
        </button>
        <div className="story-bar-title">
          <strong lang="en">{story.title}</strong>
          <span>{story.title_zh}</span>
        </div>
        <span className="story-count">
          {idx + 1} / {total}
        </span>
      </header>

      <div className="story-body">
        <article className="story-card-frame">
          <div className="story-tools">
            <button className="story-tool" onClick={toggleRate} aria-label="切换语速">
              {rate === 1 ? "1.0×" : "0.75×"}
            </button>
            {deviceVoice && <span className="story-note">部分录音缺失，正在用浏览器朗读</span>}
            <button className={`story-tool ${subs ? "is-on" : ""}`} onClick={toggleSubs} aria-pressed={subs}>
              {subs ? "隐藏字幕" : "显示字幕"} <kbd>C</kbd>
            </button>
          </div>

          <button className="story-picture" onClick={() => playFrame(idx)} aria-label="重播这一幅">
            <img src={`${BASE}/atlas/scene_images/${story.id}-${pad(idx + 1)}.png`} alt={subs ? frame.en : "故事插图"} />
            {frame.words.length > 0 && (
              <span className="story-tag" lang="en">
                {frame.words.map((w) => w.word).join(" · ")}
              </span>
            )}
          </button>

          <section className={`story-line story-sentence ${playing === "sentence" ? "is-playing" : ""}`}>
            <div className="story-line-head">
              <span className="eyebrow">故事例句</span>
              <button className="icon-btn" onClick={() => playOne("sentence")} aria-label="播放故事例句">
                <Volume2 size={17} />
              </button>
            </div>
            {subs ? (
              <>
                <p className="story-en" lang="en">
                  {markTargets(frame.en, frame.words).map((p, i) =>
                    p.word ? (
                      <button
                        key={i}
                        className={`story-word ${playing === `word:${p.word.id}` ? "is-playing" : ""}`}
                        onClick={() => playWord(p.word!)}
                        onDoubleClick={() => openWord(p.word!.id)}
                        title="单击朗读，双击查看词条"
                      >
                        {p.text}
                      </button>
                    ) : (
                      <Fragment key={i}>{p.text}</Fragment>
                    ),
                  )}
                </p>
                <p className="story-zh">{frame.zh}</p>
              </>
            ) : (
              <p className="story-en">
                <Blanks text={frame.en} />
              </p>
            )}
          </section>

          <section className={`story-line story-narration ${playing === "narration" ? "is-playing" : ""}`}>
            <div className="story-line-head">
              <span className="eyebrow">画面描述</span>
              <button className="icon-btn" onClick={() => playOne("narration")} aria-label="播放画面描述">
                <Volume2 size={17} />
              </button>
            </div>
            <p className="story-desc" lang="en">
              {subs ? frame.narration : <Blanks text={frame.narration} />}
            </p>
          </section>

          {subs && frame.words.length > 0 && (
            <ul className="story-words">
              {frame.words.map((w) => (
                <li key={w.id}>
                  <button
                    className={`story-chip ${playing === `word:${w.id}` ? "is-playing" : ""}`}
                    onClick={() => playWord(w)}
                    onDoubleClick={() => openWord(w.id)}
                    title="单击朗读，双击查看词条"
                  >
                    <b lang="en">{w.word}</b>
                    <span>{w.zh}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>
      </div>

      <footer className="story-dock">
        <button className="btn btn-ghost" onClick={() => go(idx - 1)} disabled={idx === 0} aria-label="上一幅">
          <ChevronLeft size={18} />
          <span>上一幅</span>
        </button>
        <button className="btn btn-ghost" onClick={() => playFrame(idx)} aria-label="重播">
          <RotateCcw size={16} />
          <span>重播</span>
        </button>
        <button className="btn btn-primary" onClick={toggleAuto} aria-pressed={auto}>
          {auto ? <Pause size={16} /> : <Play size={16} />}
          <span>{auto ? "停止" : "自动播放"}</span>
        </button>
        <button className="btn btn-ghost" onClick={() => go(idx + 1)} disabled={idx === total - 1} aria-label="下一幅">
          <span>下一幅</span>
          <ChevronRight size={18} />
        </button>
      </footer>
    </div>
  );
}
