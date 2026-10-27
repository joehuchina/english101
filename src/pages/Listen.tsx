import { StoryScenes } from "./StoryScenes";
import {
  ArrowRight,
  BookOpen,
  Check,
  Headphones,
  Map,
  Pause,
  Play,
  RotateCcw,
  Star,
  Swords,
  Volume2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { prefetch, useAtlas, useEntry } from "../atlas/context";
import type { Atlas, WordRef } from "../atlas/types";
import { applyListenResult } from "../listen/progress";
import {
  buildStages,
  CATEGORIES,
  pickDistractors,
  REVIEW_PREFIX,
  stageTitle,
  type ListenStage,
} from "../listen/stages";
import { play, stopAudio } from "../lib/audio";
import { go, type Route } from "../lib/router";
import { cue, type Cue } from "../lib/sound";
import { shuffle } from "../lib/text";
import { dayKey, store, useStore } from "../store/store";
import { Highlight } from "../ui/EntryView";
import { Illustration } from "../ui/Illustration";
import { Sheet } from "../ui/Sheet";
import { useKeys } from "./Learn";

const WEAK_ID = `${REVIEW_PREFIX}weak`;
/** Pause after the example sentence before the next question (correct answers only). */
const NEXT_DELAY_MS = 900;
/** Learn-mode autoplay: pause between words. */
const AUTO_GAP_MS = 900;

function useStages() {
  const atlas = useAtlas();
  return useMemo(
    () =>
      // Easier words first: by level, then by the atlas's learning order.
      buildStages(CATEGORIES, (id) => {
        const w = atlas.byId.get(id);
        return w && w.cefr * 100000 + w.order;
      }),
    [atlas],
  );
}

/** A stage from the map, or the weak-word review built from the current weak list. */
function useStage(id: string): ListenStage | null {
  const stages = useStages();
  const weak = useStore((s) => s.progress.listen.weak);
  // The review set is fixed when it opens, so answering does not reshuffle it mid-round.
  const [review] = useState(() => weak.slice(0, 20));
  return useMemo(() => {
    if (id !== WEAK_ID) return stages.find((s) => s.id === id) ?? null;
    if (!review.length) return null;
    const cat = {
      id: "weak",
      zh: "弱词复习",
      en: "Weak words",
      icon: "🔁",
      words: review,
    };
    return {
      id: WEAK_ID,
      category: cat,
      part: 1,
      parts: 1,
      words: review,
    };
  }, [id, stages, review]);
}

function sfx(c: Cue) {
  if (store.get().settings.sfx) void cue(c);
}

function sayWord(atlas: Atlas, ref: WordRef, rate = 1) {
  const accent = store.get().settings.accent;
  return play(atlas.audio(ref, accent), ref.word, accent, rate);
}

async function saySentence(atlas: Atlas, ref: WordRef) {
  const entry = await atlas.entry(ref.id).catch(() => null);
  const ex = entry?.ex[0];
  if (!entry || !ex) return sayWord(atlas, ref);
  return play(atlas.audio(entry, "ex"), ex.en, store.get().settings.accent);
}

function Stars({ n, size = 14 }: { n: number; size?: number }) {
  return (
    <span className="lp-stars" aria-label={`${n} 星`}>
      {[1, 2, 3].map((i) => (
        <Star key={i} size={size} className={i <= n ? "is-on" : ""} />
      ))}
    </span>
  );
}

export function Listen({
  route,
}: {
  route: Extract<Route, { page: "listen" }>;
}) {
  const atlas = useAtlas();
  if (atlas.kind !== "open")
    return (
      <div className="page">
        <p className="lede">
          听音选图使用开放词库的插画，请先在「我的」里切换回开放词库。
        </p>
      </div>
    );
  if (route.stage)
    return (
      <StagePlay
        key={route.stage}
        stageId={route.stage}
        mode={route.mode ?? "learn"}
      />
    );
  return <Hub />;
}

/* ---------- map of stages ---------- */

function Hub() {
  const atlas = useAtlas();
  const stages = useStages();
  const listen = useStore((s) => s.progress.listen);
  const [subTab, setSubTab] = useState<"stories" | "words">("stories");
  const [briefing, setBriefing] = useState<ListenStage | null>(null);
  // Coming back from a stage stays on this page, so the shell does not reset the scroll.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, []);
  const totalStars = stages.reduce(
    (n, s) => n + (listen.stages[s.id]?.stars ?? 0),
    0,
  );
  const words = stages.reduce((n, s) => n + s.words.length, 0);
  const next = stages.find((s) => !listen.stages[s.id]?.stars);
  const weak = listen.weak
    .map((id) => atlas.byId.get(id))
    .filter((w): w is WordRef => !!w);

  return (
    <>
      <div className="page listen-hub">
        {/* Sub-tab Navigation */}
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 24 }}>
          <div
            style={{
              display: "inline-flex",
              background: "var(--card-bg, #18181b)",
              border: "1px solid var(--card-border, #27272a)",
              borderRadius: 24,
              padding: 4,
              gap: 4,
            }}
          >
            <button
              onClick={() => setSubTab("stories")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 16px",
                borderRadius: 20,
                fontSize: 13,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                background: subTab === "stories" ? "#2563eb" : "transparent",
                color: subTab === "stories" ? "#fff" : "var(--fg-dim, #a1a1aa)",
                transition: "all 0.15s",
              }}
            >
              <Headphones size={15} /> 看图听话 (绘本)
            </button>
            <button
              onClick={() => setSubTab("words")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "6px 16px",
                borderRadius: 20,
                fontSize: 13,
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                background: subTab === "words" ? "#2563eb" : "transparent",
                color: subTab === "words" ? "#fff" : "var(--fg-dim, #a1a1aa)",
                transition: "all 0.15s",
              }}
            >
              <Map size={15} /> 词汇闯关 (地图)
            </button>
          </div>
        </div>

        {subTab === "stories" ? (
          <StoryScenes />
        ) : (
          <>
            <header className="page-head">
              <p className="eyebrow">听图 · Listen & Pick</p>
              <h1 className="display">先听见，再认出它。</h1>
              <p className="lede">
                每关先翻一遍有声画册，再听音选图。答错的词会在本轮最后再考一次，也会收进错词本。
              </p>
            </header>

        <div className="lp-summary">
          <dl className="mini-stats">
            <div>
              <dt>星星</dt>
              <dd>
                {totalStars}
                <small>/ {stages.length * 3}</small>
              </dd>
            </div>
            <div>
              <dt>已掌握</dt>
              <dd>
                {listen.mastered.length}
                <small>/ {words}</small>
              </dd>
            </div>
            <div>
              <dt>弱词</dt>
              <dd>{weak.length}</dd>
            </div>
          </dl>
          {weak.length > 0 && (
            <button
              className="lp-weak"
              onClick={() =>
                go({ page: "listen", stage: WEAK_ID, mode: "learn" })
              }
            >
              <span className="lp-weak-art">
                {weak.slice(0, 3).map((w) => (
                  <Illustration
                    key={w.id}
                    src={atlas.img(w, "thumb")}
                    word={w.word}
                    topic={w.topic}
                  />
                ))}
              </span>
              <span>
                <b>弱词复习</b>
                <small>
                  最近答错的 {Math.min(20, weak.length)} 个词，先听再测
                </small>
              </span>
              <ArrowRight size={18} />
            </button>
          )}
        </div>

        {CATEGORIES.map((cat) => {
          const list = stages.filter((s) => s.category.id === cat.id);
          if (!list.length) return null;
          const stars = list.reduce(
            (n, s) => n + (listen.stages[s.id]?.stars ?? 0),
            0,
          );
          return (
            <section key={cat.id} className="lp-round">
              <div className="lp-round-head">
                <h2>
                  {cat.icon} {cat.zh}
                </h2>
                <p>
                  {cat.en} · {list.reduce((n, s) => n + s.words.length, 0)} 词 ·{" "}
                  {stars}/{list.length * 3} 星
                </p>
              </div>
              <ul className="lp-stages">
                {list.map((s) => {
                  const rec = listen.stages[s.id];
                  const cover = atlas.byId.get(s.words[0]);
                  return (
                    <li key={s.id}>
                      <button
                        className={`lp-stage ${s === next ? "is-next" : ""} ${rec?.stars ? "is-done" : ""}`}
                        onClick={() => setBriefing(s)}
                      >
                        {cover && (
                          <Illustration
                            src={atlas.img(cover, "thumb")}
                            word={cover.word}
                            topic={cover.topic}
                            className="lp-stage-art"
                          />
                        )}
                        <span className="lp-stage-body">
                          <b>第 {s.part} 关</b>
                          <small>{s.words.length} 词</small>
                          <Stars n={rec?.stars ?? 0} />
                        </span>
                        {s === next && (
                          <span className="lp-next-tag">下一关</span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          );
        })}
          </>
        )}
      </div>
      {/* Outside .page: its entry animation would trap the fixed overlay. */}
      <Sheet
        open={!!briefing}
        onClose={() => setBriefing(null)}
        label={briefing ? `${stageTitle(briefing)} 关卡` : "关卡"}
      >
        {briefing && <Briefing stage={briefing} />}
      </Sheet>
    </>
  );
}

function Briefing({ stage }: { stage: ListenStage }) {
  const atlas = useAtlas();
  const rec = useStore((s) => s.progress.listen.stages[stage.id]);
  const refs = stage.words
    .map((id) => atlas.byId.get(id))
    .filter((w): w is WordRef => !!w);
  return (
    <div className="lp-brief">
      <p className="eyebrow">
        {stage.category.en}
        {stage.parts > 1 ? ` · 第 ${stage.part} / ${stage.parts} 关` : ""}
      </p>
      <h2 className="display">
        {stage.category.icon} {stageTitle(stage)}
      </h2>
      <p className="muted">
        {stage.words.length} 个词
        {rec ? ` · 最高 ${rec.best} 分 · 玩过 ${rec.plays} 次` : ""}
      </p>
      <ul className="lp-brief-words">
        {refs.map((w) => (
          <li key={w.id}>
            <button
              onClick={() => void sayWord(atlas, w)}
              aria-label={`朗读 ${w.word}`}
            >
              <Illustration
                src={atlas.img(w, "thumb")}
                word={w.word}
                topic={w.topic}
              />
            </button>
          </li>
        ))}
      </ul>
      <div className="lp-brief-actions">
        <button
          className="btn btn-ghost btn-xl"
          onClick={() => go({ page: "listen", stage: stage.id, mode: "learn" })}
        >
          <BookOpen size={18} /> 先学：有声画册
        </button>
        <button
          className="btn btn-primary btn-xl"
          onClick={() => go({ page: "listen", stage: stage.id, mode: "test" })}
        >
          <Swords size={18} /> 直接测试
        </button>
      </div>
    </div>
  );
}

/* ---------- a stage: learn or test ---------- */

function StagePlay({
  stageId,
  mode,
}: {
  stageId: string;
  mode: "learn" | "test";
}) {
  const atlas = useAtlas();
  const stage = useStage(stageId);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!stage) {
      go({ page: "listen" }, null, true);
      return;
    }
    let live = true;
    // Entries hold the example sentences; pictures load as they appear.
    prefetch(atlas, stage.words).then(() => live && setReady(true));
    return () => {
      live = false;
    };
  }, [atlas, stage]);
  useEffect(() => () => stopAudio(), []);
  if (!stage || !ready)
    return (
      <div className="learn learn-loading">
        <span className="spinner" />
      </div>
    );
  const exit = () => {
    stopAudio();
    go({ page: "listen" });
  };
  const switchTo = (m: "learn" | "test") => {
    stopAudio();
    go({ page: "listen", stage: stage.id, mode: m }, null, true);
  };
  return mode === "learn" ? (
    <LearnBook stage={stage} onExit={exit} onTest={() => switchTo("test")} />
  ) : (
    <Test
      key={stage.id}
      stage={stage}
      onExit={exit}
      onLearn={() => switchTo("learn")}
    />
  );
}

function PlayTop({
  stage,
  onExit,
  children,
}: {
  stage: ListenStage;
  onExit: () => void;
  children?: React.ReactNode;
}) {
  return (
    <header className="learn-top lp-top">
      <button className="icon-btn" onClick={onExit} aria-label="退出本关">
        <X size={22} />
      </button>
      <span className="lp-top-title">
        {stage.category.icon} {stageTitle(stage)}
      </span>
      {children}
    </header>
  );
}

/** Picture book: tap to hear, tap again to see the word. */
function LearnBook({
  stage,
  onExit,
  onTest,
}: {
  stage: ListenStage;
  onExit: () => void;
  onTest: () => void;
}) {
  const atlas = useAtlas();
  const refs = useMemo(
    () =>
      stage.words
        .map((id) => atlas.byId.get(id))
        .filter((w): w is WordRef => !!w),
    [atlas, stage],
  );
  const [heard, setHeard] = useState<Set<string>>(() => new Set());
  const [active, setActive] = useState<string | null>(null);
  const [flipped, setFlipped] = useState<string | null>(null);
  const [auto, setAuto] = useState(false);
  const autoToken = useRef(0);
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, []);

  const hear = useCallback(
    (w: WordRef) => {
      setActive(w.id);
      setHeard((h) => (h.has(w.id) ? h : new Set(h).add(w.id)));
      return sayWord(atlas, w);
    },
    [atlas],
  );

  // Autoplay reads every card in order, waiting for each recording to end.
  useEffect(() => {
    if (!auto) return;
    const mine = ++autoToken.current;
    (async () => {
      const start = Math.max(
        0,
        refs.findIndex((w) => w.id === active),
      );
      for (let i = active ? start + 1 : 0; i < refs.length; i++) {
        if (autoToken.current !== mine) return;
        setFlipped(null);
        await hear(refs[i]);
        await new Promise((r) => window.setTimeout(r, AUTO_GAP_MS));
      }
      if (autoToken.current === mine) setAuto(false);
    })();
    return () => {
      autoToken.current++;
    };
    // active only seeds the start position when autoplay is switched on.
  }, [auto, refs, hear]); // eslint-disable-line react-hooks/exhaustive-deps

  const tap = (w: WordRef) => {
    if (auto) {
      setAuto(false);
      stopAudio();
    }
    if (flipped === w.id) {
      setFlipped(null);
      void hear(w);
    } else if (active === w.id && heard.has(w.id)) {
      setFlipped(w.id);
      sfx("flip");
    } else {
      setFlipped(null);
      void hear(w);
    }
  };

  return (
    <div className="learn lp-play">
      <PlayTop stage={stage} onExit={onExit}>
        <span className="learn-count">
          {heard.size}
          <small>/{refs.length}</small>
        </span>
      </PlayTop>
      <main className="learn-stage lp-learn">
        <p className="stage-label">
          <span className="dot dot-new" /> 有声画册 ·
          点一下听发音，再点一下看单词
        </p>
        <ul className="lp-book">
          {refs.map((w) => (
            <li key={w.id}>
              <button
                className={`lp-card ${active === w.id ? "is-active" : ""} ${flipped === w.id ? "is-flipped" : ""}`}
                onClick={() => tap(w)}
                aria-label={flipped === w.id ? `${w.word} ${w.zh}` : "听发音"}
              >
                <Illustration
                  src={atlas.img(w, "thumb")}
                  word={w.word}
                  topic={w.topic}
                />
                {heard.has(w.id) && flipped !== w.id && (
                  <span className="lp-heard" aria-hidden="true">
                    <Check size={14} />
                  </span>
                )}
                {flipped === w.id && (
                  <span className="lp-card-back">
                    <b lang="en">{w.word}</b>
                    {w.ipa && <span className="ipa">{w.ipa}</span>}
                    <small>{w.zh}</small>
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
        <footer className="lp-learn-actions">
          <button
            className="btn btn-ghost btn-xl"
            onClick={() => {
              if (auto) stopAudio();
              setAuto((a) => !a);
            }}
          >
            {auto ? <Pause size={18} /> : <Play size={18} />}{" "}
            {auto ? "暂停连读" : "自动连读"}
          </button>
          <button className="btn btn-primary btn-xl" onClick={onTest}>
            我学会了，开始测试 <ArrowRight size={20} />
          </button>
        </footer>
      </main>
    </div>
  );
}

/** One question; a missed word comes back once at the end of the round as a retry. */
interface Question {
  id: string;
  retry: boolean;
}
const toQueue = (words: string[]): Question[] =>
  shuffle(words).map((id) => ({ id, retry: false }));

interface Answer {
  chosen: string;
  correct: boolean;
  gained: number;
}

interface Outcome {
  stars: 0 | 1 | 2 | 3;
  score: number;
  maxCombo: number;
  correct: number;
  total: number;
  wrong: string[];
  drill: boolean;
}

function Test({
  stage,
  onExit,
  onLearn,
}: {
  stage: ListenStage;
  onExit: () => void;
  onLearn: () => void;
}) {
  const atlas = useAtlas();
  const pool = useMemo(
    () => CATEGORIES.flatMap((c) => c.words).filter((id) => atlas.byId.has(id)),
    [atlas],
  );
  // A drill repeats only the missed words; it keeps no stars.
  const [drill, setDrill] = useState(false);
  const [queue, setQueue] = useState<Question[]>(() => toQueue(stage.words));
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [score, setScore] = useState(0);
  const [combo, setCombo] = useState(0);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  // Results live in a ref so the delayed advance always sees the latest answer.
  const result = useRef({
    correct: [] as string[],
    wrong: [] as string[],
    score: 0,
    maxCombo: 0,
  });
  const advanceToken = useRef(0);
  const queueRef = useRef(queue);
  queueRef.current = queue;

  const q = queue[index];
  const target = q ? atlas.byId.get(q.id) : undefined;
  const options = useMemo(() => {
    if (!q) return [];
    // A retried word gets a fresh set of pictures.
    return shuffle([q.id, ...pickDistractors(q.id, stage.words, pool)])
      .map((id) => atlas.byId.get(id))
      .filter((w): w is WordRef => !!w);
  }, [q, index, stage.words, pool, atlas]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!target || outcome) return;
    window.scrollTo({ top: 0 });
    const t = window.setTimeout(() => void sayWord(atlas, target), 300);
    return () => window.clearTimeout(t);
  }, [index, target, outcome, atlas]);

  const finish = useCallback(() => {
    advanceToken.current++;
    stopAudio();
    const r = result.current;
    const total = queueRef.current.filter((x) => !x.retry).length;
    let stars: 0 | 1 | 2 | 3 = 0;
    store.progress((p) => {
      const applied = applyListenResult(
        p.listen,
        {
          stageId: drill ? `${REVIEW_PREFIX}drill` : stage.id,
          score: r.score,
          maxCombo: r.maxCombo,
          correctIds: r.correct,
          wrongIds: r.wrong,
          total,
        },
        dayKey(),
      );
      stars = applied.stars;
      return {
        ...p,
        listen: applied.listen,
        mistakes: [
          ...r.wrong,
          ...p.mistakes.filter((x) => !r.wrong.includes(x)),
        ].slice(0, 300),
      };
    });
    sfx("complete");
    setOutcome({
      stars,
      score: r.score,
      maxCombo: r.maxCombo,
      correct: r.correct.length,
      total,
      wrong: r.wrong,
      drill,
    });
  }, [stage, drill]);

  const next = useCallback(() => {
    advanceToken.current++;
    stopAudio();
    setAnswer(null);
    if (index + 1 < queueRef.current.length) setIndex(index + 1);
    else finish();
  }, [index, finish]);

  const pick = (w: WordRef) => {
    if (answer || !q || !target) return;
    const correct = w.id === q.id;
    const r = result.current;
    if (correct) {
      const c = combo + 1;
      const gained = q.retry ? 50 : 100 + Math.min(c * 10, 50);
      setCombo(c);
      r.maxCombo = Math.max(r.maxCombo, c);
      r.score += gained;
      setScore(r.score);
      if (!q.retry) r.correct.push(q.id);
      setAnswer({ chosen: w.id, correct, gained });
      sfx(c >= 3 ? "streak" : "correct");
      // Hear the word in a sentence, then move on by itself.
      const mine = ++advanceToken.current;
      void saySentence(atlas, target).then(() => {
        if (advanceToken.current === mine)
          window.setTimeout(
            () => advanceToken.current === mine && next(),
            NEXT_DELAY_MS,
          );
      });
    } else {
      setCombo(0);
      setAnswer({ chosen: w.id, correct, gained: 0 });
      sfx("wrong");
      if (!q.retry) {
        r.wrong.push(q.id);
        setQueue((prev) => [...prev, { id: q.id, retry: true }]);
      }
      // No auto-advance: look at the right picture, continue when ready.
      advanceToken.current++;
      void sayWord(atlas, target);
    }
  };

  const restart = (list: string[], isDrill: boolean) => {
    advanceToken.current++;
    stopAudio();
    result.current = { correct: [], wrong: [], score: 0, maxCombo: 0 };
    setDrill(isDrill);
    setQueue(toQueue(list));
    setIndex(0);
    setAnswer(null);
    setScore(0);
    setCombo(0);
    setOutcome(null);
  };

  const replay = () => target && void sayWord(atlas, target);
  useKeys(
    outcome
      ? {}
      : {
          "1": () => options[0] && pick(options[0]),
          "2": () => options[1] && pick(options[1]),
          "3": () => options[2] && pick(options[2]),
          "4": () => options[3] && pick(options[3]),
          r: replay,
          Enter: () => answer && next(),
          " ": () => (answer ? next() : replay()),
        },
  );

  if (outcome)
    return (
      <Result
        stage={stage}
        outcome={outcome}
        onExit={onExit}
        onLearn={onLearn}
        onAgain={() => restart(stage.words, false)}
        onDrill={() => restart(outcome.wrong, true)}
      />
    );
  if (!q || !target) return null;
  return (
    <div className="learn lp-play">
      <PlayTop stage={stage} onExit={onExit}>
        <div
          className="learn-progress"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={queue.length}
          aria-valuenow={index}
        >
          <span style={{ width: `${(index / queue.length) * 100}%` }} />
        </div>
        <span className="learn-count">
          {index + 1}
          <small>/{queue.length}</small>
        </span>
        <span className="lp-score" aria-label={`得分 ${score}`}>
          {score}
        </span>
      </PlayTop>
      <main
        className={`learn-stage lp-test ${answer ? (answer.correct ? "is-right" : "is-wrong") : ""}`}
        key={index}
      >
        <p className="stage-label">
          <span className={`dot ${q.retry ? "dot-retry" : "dot-review"}`} />
          {q.retry ? "回炉题 · " : ""}听，是哪张图？
          {combo >= 2 && <span className="lp-combo">{combo} 连击</span>}
        </p>
        <div className="lp-listen">
          <button className="listen-orb" onClick={replay} aria-label="再听一遍">
            <Volume2 size={40} strokeWidth={1.6} />
            <span />
          </button>
          <button
            className="link"
            onClick={() => void sayWord(atlas, target, 0.7)}
          >
            慢速再听
          </button>
        </div>
        <ul className="lp-options">
          {options.map((o, i) => {
            const isAnswer = o.id === q.id;
            const chosen = answer?.chosen === o.id;
            const cls = answer
              ? isAnswer
                ? "is-answer"
                : chosen
                  ? "is-chosen"
                  : "is-dim"
              : "";
            return (
              <li key={o.id}>
                <button
                  className={`lp-option ${cls}`}
                  onClick={() => pick(o)}
                  disabled={!!answer}
                  aria-label={answer ? o.word : `选项 ${i + 1}`}
                >
                  <Illustration
                    src={atlas.img(o)}
                    word={o.word}
                    topic={o.topic}
                    eager
                  />
                  <kbd>{i + 1}</kbd>
                  {answer && (isAnswer || chosen) && (
                    <span className="lp-option-word" lang="en">
                      {o.word}
                    </span>
                  )}
                  {answer && isAnswer && (
                    <Check size={22} className="lp-option-mark" />
                  )}
                  {answer && chosen && !isAnswer && (
                    <X size={22} className="lp-option-mark" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
        {!answer && (
          <span className="hint-keys">
            <kbd>1</kbd>–<kbd>4</kbd> 选图 · <kbd>R</kbd> 重听
          </span>
        )}
        {answer && (
          <TestFeedback
            word={target}
            answer={answer}
            retry={q.retry}
            onNext={next}
          />
        )}
      </main>
    </div>
  );
}

function TestFeedback({
  word,
  answer,
  retry,
  onNext,
}: {
  word: WordRef;
  answer: Answer;
  retry: boolean;
  onNext: () => void;
}) {
  const atlas = useAtlas();
  const { entry } = useEntry(word.id);
  const btn = useRef<HTMLButtonElement>(null);
  useEffect(() => btn.current?.focus({ preventScroll: true }), []);
  const verdict = answer.correct
    ? retry
      ? "回炉成功！"
      : `答对了 +${answer.gained}`
    : retry
      ? "还是它，再记一记"
      : "不对哦，记住这张图";
  return (
    <div
      className={`feedback ${answer.correct ? "is-right" : "is-wrong"}`}
      role="status"
    >
      <div className="feedback-inner">
        <Illustration
          src={atlas.img(word, "thumb")}
          word={word.word}
          topic={word.topic}
          className="feedback-art"
        />
        <div className="feedback-text">
          <p className="feedback-verdict">{verdict}</p>
          <p className="feedback-word">
            <b lang="en">{word.word}</b>
            <span className="ipa">{word.ipa}</span>
          </p>
          <p className="feedback-zh">{word.zh}</p>
          {entry?.ex[0] && (
            <p className="feedback-ex" lang="en">
              <Highlight text={entry.ex[0].en} word={entry.w} />
            </p>
          )}
          {!answer.correct && (
            <p className="feedback-zh">答错的词会在本轮最后再出一次。</p>
          )}
        </div>
        <button
          ref={btn}
          className={`btn btn-xl ${answer.correct ? "btn-sage" : "btn-terra"}`}
          onClick={onNext}
        >
          {answer.correct ? "下一题" : "继续"} <ArrowRight size={20} />
        </button>
      </div>
    </div>
  );
}

function Result({
  stage,
  outcome,
  onExit,
  onLearn,
  onAgain,
  onDrill,
}: {
  stage: ListenStage;
  outcome: Outcome;
  onExit: () => void;
  onLearn: () => void;
  onAgain: () => void;
  onDrill: () => void;
}) {
  const atlas = useAtlas();
  const accuracy = outcome.total
    ? Math.round((outcome.correct / outcome.total) * 100)
    : 0;
  const wrong = outcome.wrong
    .map((id) => atlas.byId.get(id))
    .filter((w): w is WordRef => !!w);
  const isReview = stage.id.startsWith(REVIEW_PREFIX) || outcome.drill;
  return (
    <div className="learn summary">
      <div className="summary-card lp-result">
        <p className="eyebrow">
          {stage.category.icon} {stageTitle(stage)} ·{" "}
          {outcome.drill ? "错词再练" : "测试完成"}
        </p>
        {!isReview && <Stars n={outcome.stars} size={34} />}
        <h1 className="display">
          {outcome.stars >= 1 || (isReview && accuracy >= 70)
            ? accuracy === 100
              ? "全部听对了。"
              : "过关了，进度已保存。"
            : "到 70% 就能拿到 1 星，再来一次。"}
        </h1>
        <dl className="mini-stats">
          <div>
            <dt>得分</dt>
            <dd>{outcome.score}</dd>
          </div>
          <div>
            <dt>正确率</dt>
            <dd>
              {accuracy}
              <small>%</small>
            </dd>
          </div>
          <div>
            <dt>最高连击</dt>
            <dd>{outcome.maxCombo}</dd>
          </div>
        </dl>
        {wrong.length > 0 && (
          <>
            <p className="lp-wrong-title">
              本轮错词 {wrong.length}{" "}
              个，点图听发音。它们已收进错词本和弱词复习。
            </p>
            <ul className="summary-words">
              {wrong.map((w) => (
                <li
                  key={w.id}
                  className="is-wrong"
                  onClick={() => void sayWord(atlas, w)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && void sayWord(atlas, w)}
                >
                  <Illustration
                    src={atlas.img(w, "thumb")}
                    word={w.word}
                    topic={w.topic}
                  />
                  <span lang="en">{w.word}</span>
                  <small>{w.zh}</small>
                </li>
              ))}
            </ul>
          </>
        )}
        <div className="summary-actions">
          <button className="btn btn-ghost" onClick={onExit}>
            返回地图
          </button>
          <button className="btn btn-ghost" onClick={onLearn}>
            <BookOpen size={18} /> 复习本关
          </button>
          {wrong.length > 0 && (
            <button className="btn btn-ghost" onClick={onDrill}>
              <RotateCcw size={18} /> 只练错词
            </button>
          )}
          <button
            className="btn btn-primary btn-xl"
            onClick={onAgain}
            ref={(b) => b?.focus({ preventScroll: true })}
          >
            <RotateCcw size={18} /> 再测一次
          </button>
        </div>
      </div>
    </div>
  );
}
