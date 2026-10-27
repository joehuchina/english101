import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Headphones,
  Pause,
  Play,
  Volume2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { openWord } from "../lib/router";

export interface StoryTarget {
  id: string;
  word: string;
  pos: string;
  zh: string;
  en: string;
}

export interface StorySentence {
  en: string;
  zh: string;
  scene_prompt?: string;
  narration?: string;
  sentence_targets?: StoryTarget[];
}

export interface StoryUnit {
  scene_id: string;
  level: string;
  topic: string;
  title: string;
  title_zh?: string;
  setting?: string;
  characters?: { name: string; look?: string }[];
  targets: string[];
  review_words?: string[];
  sentences: StorySentence[];
}

// Browser Text-To-Speech fallback
function speakText(text: string, onEnd?: () => void) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    if (onEnd) onEnd();
    return;
  }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-US";
  u.rate = 0.95;
  if (onEnd) {
    u.onend = onEnd;
    u.onerror = onEnd;
  }
  window.speechSynthesis.speak(u);
}

const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export function StoryScenes({ onBack }: { onBack?: () => void }) {
  const [stories, setStories] = useState<StoryUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeStory, setActiveStory] = useState<StoryUnit | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string>("all");

  useEffect(() => {
    fetch(`${BASE}/atlas/story_units.json`)
      .then((r) => r.json())
      .then((data: StoryUnit[]) => {
        setStories(data);
        setLoading(false);
      })
      .catch((e) => {
        console.error("Failed to load story units:", e);
        setLoading(false);
      });
  }, []);

  const topics = Array.from(new Set(stories.map((s) => s.topic))).sort();
  const filtered = stories.filter(
    (s) => selectedTopic === "all" || s.topic === selectedTopic,
  );

  if (activeStory) {
    return (
      <StoryPlayer
        story={activeStory}
        onClose={() => {
          window.speechSynthesis?.cancel();
          setActiveStory(null);
        }}
      />
    );
  }

  return (
    <div className="story-scenes-page" style={{ padding: "16px 20px 80px", maxWidth: 900, margin: "0 auto" }}>
      {/* Top Banner */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, display: "flex", alignItems: "center", gap: 8 }}>
            <Headphones size={22} /> 看图听话 · 情景绘本故事
          </h2>
          {onBack && (
            <button className="btn btn-ghost" onClick={onBack} style={{ fontSize: 13 }}>
              返回
            </button>
          )}
        </div>
        <p style={{ color: "var(--fg-dim, #71717a)", fontSize: 13, lineHeight: 1.5 }}>
          针对画面内容设计的「画面旁白 🎙️ + 故事例句 📖 + 核心单词 🔤」三段式沉浸听力。A1 阶段 60 个生活故事，覆盖 785 个核心词。
        </p>
      </div>

      {/* Topic Filter Pills */}
      <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 12, marginBottom: 16 }}>
        <button
          className={`filter-chip ${selectedTopic === "all" ? "active" : ""}`}
          onClick={() => setSelectedTopic("all")}
          style={{
            padding: "4px 12px",
            borderRadius: 16,
            fontSize: 12,
            border: "1px solid var(--border, #27272a)",
            background: selectedTopic === "all" ? "#2563eb" : "transparent",
            color: selectedTopic === "all" ? "#fff" : "inherit",
            cursor: "pointer",
            whiteSpace: "nowrap",
          }}
        >
          全部 ({stories.length})
        </button>
        {topics.map((t) => (
          <button
            key={t}
            onClick={() => setSelectedTopic(t)}
            style={{
              padding: "4px 12px",
              borderRadius: 16,
              fontSize: 12,
              border: "1px solid var(--border, #27272a)",
              background: selectedTopic === t ? "#2563eb" : "transparent",
              color: selectedTopic === t ? "#fff" : "inherit",
              cursor: "pointer",
              whiteSpace: "nowrap",
              textTransform: "capitalize",
            }}
          >
            {t}
          </button>
        ))}
      </div>

      {/* Grid of Stories */}
      {loading ? (
        <div style={{ textAlign: "center", padding: 40, color: "var(--fg-dim)" }}>正在加载情景故事...</div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
            gap: 14,
          }}
        >
          {filtered.map((s) => (
            <div
              key={s.scene_id}
              onClick={() => setActiveStory(s)}
              role="button"
              tabIndex={0}
              style={{
                background: "var(--card-bg, #18181b)",
                border: "1px solid var(--card-border, #27272a)",
                borderRadius: 12,
                padding: 16,
                cursor: "pointer",
                transition: "all 0.15s ease",
                display: "flex",
                flexDirection: "column",
                gap: 8,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono, monospace)",
                    fontSize: 11,
                    fontWeight: 700,
                    color: "#60a5fa",
                  }}
                >
                  {s.scene_id}
                </span>
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--fg-dim, #71717a)",
                    textTransform: "capitalize",
                  }}
                >
                  {s.topic}
                </span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>{s.title}</div>
              <div style={{ fontSize: 13, color: "var(--fg-dim, #a1a1aa)" }}>{s.title_zh || ""}</div>
              <div
                style={{
                  fontSize: 11,
                  color: "var(--fg-dim, #71717a)",
                  marginTop: 4,
                  display: "flex",
                  gap: 8,
                }}
              >
                <span>{s.sentences.length} 帧画面</span>
                <span>•</span>
                <span>{s.targets.length} 目标词</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StoryPlayer({ story, onClose }: { story: StoryUnit; onClose: () => void }) {
  const [frameIdx, setFrameIdx] = useState(0);
  const [isPlayingStory, setIsPlayingStory] = useState(false);
  const [blindMode, setBlindMode] = useState(true);
  const [revealedTracks, setRevealedTracks] = useState<{ narration: boolean; sentence: boolean; words: boolean }>({
    narration: false,
    sentence: false,
    words: false,
  });
  const [playingTrack, setPlayingTrack] = useState<"narration" | "sentence" | "word" | null>(null);
  const [playingWordId, setPlayingWordId] = useState<string | null>(null);

  const totalFrames = story.sentences.length;
  const current = story.sentences[frameIdx];

  const prefix = `${story.scene_id}_${String(frameIdx + 1).padStart(2, "0")}`;
  const audioBase = `${BASE}/atlas/audio/scenes/${story.scene_id}/${prefix}`;
  const imgUrl = `${BASE}/atlas/scene_images/${story.scene_id}-${String(frameIdx + 1).padStart(2, "0")}.png`;

  // Audio synchronization refs
  const activeAudioRef = useRef<HTMLAudioElement | null>(null);
  const activeTimerRef = useRef<any>(null);
  const playbackSessionRef = useRef<number>(0);

  // Global stop: halts audio element, timers, and browser speech
  const stopAllAudio = useCallback((stopStory = false) => {
    playbackSessionRef.current += 1;
    if (activeTimerRef.current) {
      clearTimeout(activeTimerRef.current);
      activeTimerRef.current = null;
    }
    if (activeAudioRef.current) {
      activeAudioRef.current.pause();
      activeAudioRef.current.onended = null;
      activeAudioRef.current.onerror = null;
      activeAudioRef.current = null;
    }
    window.speechSynthesis?.cancel();
    setPlayingTrack(null);
    setPlayingWordId(null);
    if (stopStory) {
      setIsPlayingStory(false);
    }
  }, []);

  const playAudioOrFallback = useCallback(
    (
      url: string,
      text: string,
      trackType: "narration" | "sentence" | "word",
      wordId?: string,
      onComplete?: () => void
    ) => {
      stopAllAudio(false);

      const sessionId = ++playbackSessionRef.current;
      setPlayingTrack(trackType);
      if (wordId) setPlayingWordId(wordId);

      const finish = () => {
        if (playbackSessionRef.current !== sessionId) return;
        setPlayingTrack(null);
        setPlayingWordId(null);
        activeAudioRef.current = null;
        if (onComplete) onComplete();
      };

      const a = new Audio(url);
      activeAudioRef.current = a;
      a.onended = finish;
      a.onerror = () => {
        if (playbackSessionRef.current !== sessionId) return;
        speakText(text, finish);
      };
      a.play().catch(() => {
        if (playbackSessionRef.current !== sessionId) return;
        speakText(text, finish);
      });
    },
    [stopAllAudio]
  );

  const playNarration = useCallback(
    (onComplete?: () => void) => {
      if (!current?.narration) {
        if (onComplete) onComplete();
        return;
      }
      playAudioOrFallback(`${audioBase}_narration.mp3`, current.narration, "narration", undefined, onComplete);
    },
    [current, audioBase, playAudioOrFallback]
  );

  const playSentence = useCallback(
    (onComplete?: () => void) => {
      if (!current?.en) {
        if (onComplete) onComplete();
        return;
      }
      playAudioOrFallback(`${audioBase}_sentence.mp3`, current.en, "sentence", undefined, onComplete);
    },
    [current, audioBase, playAudioOrFallback]
  );

  const playSingleWord = useCallback(
    (wordId: string, wordText: string) => {
      stopAllAudio(true);
      playAudioOrFallback(`${audioBase}_word_${wordId}.mp3`, wordText, "word", wordId);
    },
    [audioBase, playAudioOrFallback, stopAllAudio]
  );

  const playWords = useCallback(
    (onComplete?: () => void) => {
      const words = current?.sentence_targets || [];
      if (words.length === 0) {
        if (onComplete) onComplete();
        return;
      }
      stopAllAudio(true);
      const sessionId = playbackSessionRef.current;
      let i = 0;
      const playNext = () => {
        if (playbackSessionRef.current !== sessionId) return;
        if (i >= words.length) {
          setPlayingTrack(null);
          setPlayingWordId(null);
          if (onComplete) onComplete();
          return;
        }
        const w = words[i++];
        playAudioOrFallback(`${audioBase}_word_${w.id}.mp3`, w.word, "word", w.id, () => {
          if (playbackSessionRef.current !== sessionId) return;
          activeTimerRef.current = setTimeout(playNext, 400);
        });
      };
      playNext();
    },
    [current, audioBase, playAudioOrFallback, stopAllAudio]
  );

  // Sequential stream for current frame: Narration (David) -> Sentence (Rachel) -> Advance to next frame
  const playCurrentFrame = useCallback(() => {
    stopAllAudio(false);
    const sessionId = playbackSessionRef.current;

    playNarration(() => {
      if (playbackSessionRef.current !== sessionId) return;
      activeTimerRef.current = setTimeout(() => {
        if (playbackSessionRef.current !== sessionId) return;
        playSentence(() => {
          if (playbackSessionRef.current !== sessionId) return;
          // After sentence finishes, auto advance to next frame
          activeTimerRef.current = setTimeout(() => {
            if (playbackSessionRef.current !== sessionId) return;
            setFrameIdx((f) => {
              if (f < totalFrames - 1) {
                return f + 1;
              } else {
                setIsPlayingStory(false);
                return f;
              }
            });
          }, 1200);
        });
      }, 500);
    });
  }, [stopAllAudio, playNarration, playSentence, totalFrames]);

  // Master Toggle: Continuous story play across frames or Pause
  const togglePlayStory = useCallback(() => {
    if (isPlayingStory || playingTrack !== null) {
      stopAllAudio(true);
    } else {
      if (frameIdx >= totalFrames - 1) {
        setFrameIdx(0);
      }
      setIsPlayingStory(true);
    }
  }, [isPlayingStory, playingTrack, frameIdx, totalFrames, stopAllAudio]);

  // When story is playing, trigger audio on frameIdx change
  useEffect(() => {
    setRevealedTracks({ narration: false, sentence: false, words: false });
    if (isPlayingStory) {
      activeTimerRef.current = setTimeout(() => {
        playCurrentFrame();
      }, 350);
    }
    return () => {
      if (activeTimerRef.current) {
        clearTimeout(activeTimerRef.current);
      }
      stopAllAudio(false);
    };
  }, [frameIdx, isPlayingStory]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard navigation
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "j") {
        if (frameIdx < totalFrames - 1) {
          stopAllAudio(false);
          setFrameIdx((f) => f + 1);
        }
      } else if (e.key === "ArrowLeft" || e.key === "k") {
        if (frameIdx > 0) {
          stopAllAudio(false);
          setFrameIdx((f) => f - 1);
        }
      } else if (e.key === "Escape") {
        onClose();
      } else if (e.key === " ") {
        e.preventDefault();
        togglePlayStory();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frameIdx, totalFrames, onClose, togglePlayStory, stopAllAudio]);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--bg, #09090b)",
        zIndex: 50,
        display: "flex",
        flexDirection: "column",
        overflowY: "auto",
        padding: "16px 20px 40px",
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          maxWidth: 800,
          width: "100%",
          margin: "0 auto 16px",
        }}
      >
        <button className="icon-btn" onClick={onClose} aria-label="关闭">
          <ArrowLeft size={20} />
        </button>

        <div style={{ textAlign: "center" }}>
          <div style={{ fontSize: 16, fontWeight: 700 }}>
            {story.title} <span style={{ color: "var(--fg-dim, #71717a)", fontWeight: 400 }}>{story.title_zh}</span>
          </div>
          <div style={{ fontSize: 12, color: "var(--fg-dim, #71717a)", fontFamily: "monospace" }}>
            {story.scene_id} · 第 {frameIdx + 1} / {totalFrames} 画面
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <button
            className="btn"
            style={{
              background: blindMode ? "#1e293b" : "#18181b",
              color: blindMode ? "#60a5fa" : "var(--fg-dim, #71717a)",
              border: "1px solid",
              borderColor: blindMode ? "#3b82f6" : "var(--card-border, #27272a)",
              fontSize: 12,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
            onClick={() => setBlindMode((b) => !b)}
            title="盲听模式：模糊字幕，先看图听音，点击字幕查看"
          >
            {blindMode ? <EyeOff size={14} /> : <Eye size={14} />}
            {blindMode ? "盲听模式 (已模糊)" : "明文模式"}
          </button>
        </div>
      </div>

      {/* Main Picture Book Card View */}
      <div
        style={{
          maxWidth: 820,
          width: "100%",
          margin: "0 auto",
          background: "var(--card-bg, #141416)",
          border: "1px solid var(--card-border, #27272a)",
          borderRadius: 20,
          overflow: "hidden",
          boxShadow: "0 12px 36px rgba(0, 0, 0, 0.5)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* 1. TOP OF PICTURE: 口语旁白点读区 (David-UK 🇬🇧) */}
        {current?.narration && (() => {
          const isBlurred = blindMode && !revealedTracks.narration;
          const isSpeaking = playingTrack === "narration";
          return (
            <div
              style={{
                padding: "14px 20px",
                background: isSpeaking ? "#1e293b" : "#18181b",
                borderBottom: "1px solid var(--card-border, #27272a)",
                display: "flex",
                alignItems: "center",
                gap: 14,
                cursor: isBlurred ? "pointer" : "default",
                transition: "all 0.2s ease",
              }}
              onClick={() => {
                if (isBlurred) {
                  setRevealedTracks((prev) => ({ ...prev, narration: true }));
                }
              }}
            >
              {/* Narration Play Button */}
              <button
                className="icon-btn"
                style={{
                  background: isSpeaking ? "#2563eb" : "rgba(59, 130, 246, 0.15)",
                  color: isSpeaking ? "#fff" : "#60a5fa",
                  width: 38,
                  height: 38,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  boxShadow: isSpeaking ? "0 0 12px rgba(37, 99, 235, 0.5)" : "none",
                  transition: "all 0.2s ease",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (isSpeaking) {
                    stopAllAudio(false);
                  } else {
                    stopAllAudio(true);
                    playNarration();
                  }
                }}
                title={isSpeaking ? "停止播放" : "点击播放画面口语旁白 (David-UK 🇬🇧)"}
              >
                {isSpeaking ? <Pause size={18} /> : <Volume2 size={18} />}
              </button>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#60a5fa", letterSpacing: "0.05em", marginBottom: 3, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span>🎙️ 画面口语旁白</span>
                    <span style={{ background: "#1e3a8a", color: "#bfdbfe", padding: "1px 6px", borderRadius: 4, fontSize: 10 }}>David-UK 🇬🇧</span>
                  </div>
                  {isBlurred && (
                    <span style={{ fontSize: 11, color: "#93c5fd", background: "rgba(59,130,246,0.15)", padding: "1px 6px", borderRadius: 4 }}>
                      👆 点击显现字幕
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 13,
                    lineHeight: 1.5,
                    color: "#cbd5e1",
                    filter: isBlurred ? "blur(7px)" : "none",
                    userSelect: isBlurred ? "none" : "text",
                    transition: "filter 0.25s ease",
                  }}
                >
                  {current.narration}
                </div>
              </div>
            </div>
          );
        })()}

        {/* 2. CENTER: 绘本插画 (Illustration) */}
        <div
          style={{
            minHeight: 300,
            background: "#0c0d0e",
            padding: 16,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            textAlign: "center",
            position: "relative",
          }}
        >
          <img
            key={imgUrl}
            src={imgUrl}
            alt={current?.en}
            style={{
              maxHeight: 340,
              maxWidth: "100%",
              borderRadius: 10,
              objectFit: "contain",
              boxShadow: "0 8px 28px rgba(0,0,0,0.6)",
            }}
            onError={(e) => {
              (e.target as HTMLElement).style.display = "none";
            }}
          />

          {/* Quick Nav Overlay Arrows */}
          <button
            onClick={() => {
              if (frameIdx > 0) {
                stopAllAudio(false);
                setFrameIdx((f) => f - 1);
              }
            }}
            disabled={frameIdx === 0}
            style={{
              position: "absolute",
              left: 14,
              top: "50%",
              transform: "translateY(-50%)",
              background: "rgba(0,0,0,0.55)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#fff",
              width: 38,
              height: 38,
              borderRadius: "50%",
              cursor: frameIdx === 0 ? "not-allowed" : "pointer",
              opacity: frameIdx === 0 ? 0.25 : 0.85,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "opacity 0.2s",
            }}
            title="上一幅"
          >
            <ChevronLeft size={22} />
          </button>
          <button
            onClick={() => {
              if (frameIdx < totalFrames - 1) {
                stopAllAudio(false);
                setFrameIdx((f) => f + 1);
              }
            }}
            disabled={frameIdx === totalFrames - 1}
            style={{
              position: "absolute",
              right: 14,
              top: "50%",
              transform: "translateY(-50%)",
              background: "rgba(0,0,0,0.55)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#fff",
              width: 38,
              height: 38,
              borderRadius: "50%",
              cursor: frameIdx === totalFrames - 1 ? "not-allowed" : "pointer",
              opacity: frameIdx === totalFrames - 1 ? 0.25 : 0.85,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "opacity 0.2s",
            }}
            title="下一幅"
          >
            <ChevronRight size={22} />
          </button>
        </div>

        {/* 3. BELOW PICTURE: 故事例句点读区 (Rachel-US 🇺🇸) */}
        {(() => {
          const isBlurred = blindMode && !revealedTracks.sentence;
          const isSpeaking = playingTrack === "sentence";
          return (
            <div
              style={{
                padding: "20px 24px",
                background: isSpeaking ? "#1e293b" : "#18181b",
                borderTop: "1px solid var(--card-border, #27272a)",
                display: "flex",
                alignItems: "center",
                gap: 16,
                cursor: isBlurred ? "pointer" : "default",
                transition: "all 0.2s ease",
              }}
              onClick={() => {
                if (isBlurred) {
                  setRevealedTracks((prev) => ({ ...prev, sentence: true }));
                }
              }}
            >
              {/* Sentence Play Button */}
              <button
                className="icon-btn"
                style={{
                  background: isSpeaking ? "#10b981" : "rgba(16, 185, 129, 0.15)",
                  color: isSpeaking ? "#fff" : "#34d399",
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  boxShadow: isSpeaking ? "0 0 14px rgba(16, 185, 129, 0.5)" : "none",
                  transition: "all 0.2s ease",
                }}
                onClick={(e) => {
                  e.stopPropagation();
                  if (isSpeaking) {
                    stopAllAudio(false);
                  } else {
                    stopAllAudio(true);
                    playSentence();
                  }
                }}
                title={isSpeaking ? "停止播放" : "点击点读故事例句 (Rachel-US 🇺🇸)"}
              >
                {isSpeaking ? <Pause size={22} /> : <Volume2 size={22} />}
              </button>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#34d399", letterSpacing: "0.05em", marginBottom: 5, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span>📖 故事例句</span>
                    <span style={{ background: "#064e3b", color: "#a7f3d0", padding: "1px 6px", borderRadius: 4, fontSize: 10 }}>Rachel-US 🇺🇸</span>
                  </div>
                  {isBlurred && (
                    <span style={{ fontSize: 11, color: "#6ee7b7", background: "rgba(16,185,129,0.15)", padding: "1px 6px", borderRadius: 4 }}>
                      👆 点击显现字幕
                    </span>
                  )}
                </div>
                <div
                  style={{
                    filter: isBlurred ? "blur(8px)" : "none",
                    userSelect: isBlurred ? "none" : "text",
                    transition: "filter 0.25s ease",
                  }}
                >
                  <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.45, color: "#f8fafc", marginBottom: 4 }}>
                    {current?.en}
                  </div>
                  <div style={{ fontSize: 14, color: "var(--fg-dim, #94a3b8)" }}>{current?.zh}</div>
                </div>
              </div>
            </div>
          );
        })()}

        {/* 4. UNDER SENTENCE: 核心生词点读区 */}
        {current?.sentence_targets && current.sentence_targets.length > 0 && (() => {
          const isBlurred = blindMode && !revealedTracks.words;
          return (
            <div style={{ padding: "14px 24px", background: "rgba(0,0,0,0.25)", borderTop: "1px solid var(--card-border, #27272a)", display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--fg-dim, #71717a)", letterSpacing: "0.05em", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span>🔤 本画面核心单词（点击单词单独发音）</span>
                  <span style={{ background: "#27272a", color: "#e4e4e7", padding: "1px 6px", borderRadius: 4, fontSize: 10 }}>Rachel-US 🇺🇸</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      playWords();
                    }}
                    disabled={playingTrack !== null}
                    style={{
                      background: playingTrack === "word" ? "#3b82f6" : "rgba(255,255,255,0.06)",
                      border: "1px solid #3f3f46",
                      color: playingTrack === "word" ? "#fff" : "#a1a1aa",
                      borderRadius: 4,
                      padding: "2px 8px",
                      fontSize: 10,
                      cursor: playingTrack !== null ? "not-allowed" : "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                    title="手动顺序朗读所有核心单词"
                  >
                    <Volume2 size={12} /> 读全部生词
                  </button>
                </div>
                {isBlurred && (
                  <span
                    onClick={() => setRevealedTracks((prev) => ({ ...prev, words: true }))}
                    style={{ fontSize: 11, color: "#93c5fd", cursor: "pointer", textDecoration: "underline" }}
                  >
                    👆 点击显现单词
                  </span>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 10,
                  filter: isBlurred ? "blur(7px)" : "none",
                  userSelect: isBlurred ? "none" : "text",
                  transition: "filter 0.25s ease",
                  cursor: isBlurred ? "pointer" : "default",
                }}
                onClick={() => {
                  if (isBlurred) {
                    setRevealedTracks((prev) => ({ ...prev, words: true }));
                  }
                }}
              >
                {current.sentence_targets.map((tw) => {
                  const isWordSpeaking = playingWordId === tw.id;
                  return (
                    <div
                      key={tw.id}
                      onClick={(e) => {
                        if (!isBlurred) {
                          e.stopPropagation();
                          if (isWordSpeaking) {
                            stopAllAudio(false);
                          } else {
                            playSingleWord(tw.id, tw.word);
                          }
                        }
                      }}
                      onDoubleClick={(e) => {
                        if (!isBlurred) {
                          e.stopPropagation();
                          openWord(tw.id);
                        }
                      }}
                      style={{
                        background: isWordSpeaking ? "#1e3a5f" : "#1e2430",
                        border: "1px solid",
                        borderColor: isWordSpeaking ? "#3b82f6" : "#2d3748",
                        borderRadius: 8,
                        padding: "6px 12px",
                        fontSize: 13,
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        cursor: "pointer",
                        transition: "all 0.15s",
                        boxShadow: isWordSpeaking ? "0 0 10px rgba(59, 130, 246, 0.4)" : "none",
                      }}
                    >
                      <strong style={{ color: "#fff" }}>{tw.word}</strong>
                      <span style={{ fontSize: 11, color: "#60a5fa", fontFamily: "monospace" }}>{tw.pos}</span>
                      <span style={{ fontSize: 12, color: "#94a3b8" }}>{tw.zh}</span>
                      <Volume2 size={14} color={isWordSpeaking ? "#60a5fa" : "#94a3b8"} />
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })()}

        {/* Bottom Master Playback & Navigation Dock */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--card-border, #27272a)",
            background: "#121214",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 16,
          }}
        >
          {/* Previous Frame */}
          <button
            className="btn btn-ghost"
            onClick={() => {
              stopAllAudio(false);
              setFrameIdx((f) => Math.max(0, f - 1));
            }}
            disabled={frameIdx === 0}
            style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4, minWidth: 90 }}
          >
            <ChevronLeft size={16} /> 上一幅
          </button>

          {/* Center Master Story Player Dock */}
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
            <button
              onClick={togglePlayStory}
              style={{
                background: isPlayingStory ? "#dc2626" : "#2563eb",
                color: "#fff",
                border: "none",
                borderRadius: 24,
                padding: "8px 24px",
                fontSize: 14,
                fontWeight: 700,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                boxShadow: isPlayingStory
                  ? "0 0 16px rgba(220, 38, 38, 0.5)"
                  : "0 0 16px rgba(37, 99, 235, 0.4)",
                transition: "all 0.2s ease",
              }}
              title="播放整个绘本故事，逐幅连播（空格键快捷启停）"
            >
              {isPlayingStory ? <Pause size={18} /> : <Play size={18} />}
              <span>{isPlayingStory ? "暂停故事" : "播放故事"}</span>
            </button>

            {/* Frame Dots Indicator */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ display: "flex", gap: 6 }}>
                {story.sentences.map((_, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      stopAllAudio(false);
                      setFrameIdx(i);
                    }}
                    title={`跳转到第 ${i + 1} 画面`}
                    style={{
                      width: i === frameIdx ? 22 : 8,
                      height: 8,
                      borderRadius: 4,
                      background: i === frameIdx ? "#3b82f6" : "#3f3f46",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                  />
                ))}
              </div>
              <span style={{ fontSize: 11, color: "var(--fg-dim, #71717a)", fontFamily: "monospace" }}>
                {frameIdx + 1} / {totalFrames}
              </span>
            </div>
          </div>

          {/* Next Frame */}
          <button
            className="btn btn-ghost"
            onClick={() => {
              stopAllAudio(false);
              setFrameIdx((f) => Math.min(totalFrames - 1, f + 1));
            }}
            disabled={frameIdx === totalFrames - 1}
            style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 4, minWidth: 90, justifyContent: "flex-end" }}
          >
            下一幅 <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
