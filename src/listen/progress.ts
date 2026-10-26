import { computeStars, REVIEW_PREFIX } from "./stages";

/** A word counts as mastered after correct first answers on this many different days. */
export const MASTERY_DAYS = 2;

export interface ListenStageRecord {
  stars: 0 | 1 | 2 | 3;
  best: number;
  plays: number;
}

export interface ListenWordStat {
  /** Recent days with a correct first answer (yyyy-mm-dd). */
  days: string[];
  wrong: number;
}

export interface ListenProgress {
  stages: Record<string, ListenStageRecord>;
  words: Record<string, ListenWordStat>;
  /** Missed and not yet mastered again, newest first. */
  weak: string[];
  mastered: string[];
}

export const emptyListen = (): ListenProgress => ({
  stages: {},
  words: {},
  weak: [],
  mastered: [],
});

const isObj = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const count = (v: unknown, hi = 1e9) =>
  typeof v === "number" && Number.isInteger(v) && v >= 0 && v <= hi;
const ids = (v: unknown, max: number) =>
  Array.isArray(v)
    ? v.filter((x): x is string => typeof x === "string").slice(0, max)
    : [];

export function sanitizeListen(v: unknown): ListenProgress {
  const out = emptyListen();
  if (!isObj(v)) return out;
  if (isObj(v.stages))
    for (const [k, s] of Object.entries(v.stages))
      if (isObj(s) && count(s.stars, 3) && count(s.best) && count(s.plays))
        out.stages[k] = {
          stars: s.stars as 0 | 1 | 2 | 3,
          best: s.best as number,
          plays: s.plays as number,
        };
  if (isObj(v.words))
    for (const [k, w] of Object.entries(v.words))
      if (isObj(w) && count(w.wrong))
        out.words[k] = {
          days: ids(w.days, MASTERY_DAYS).filter((d) =>
            /^\d{4}-\d{2}-\d{2}$/.test(d),
          ),
          wrong: w.wrong as number,
        };
  out.weak = ids(v.weak, 2000);
  out.mastered = ids(v.mastered, 5000);
  return out;
}

export interface ListenResult {
  stageId: string;
  score: number;
  maxCombo: number;
  /** First attempts only; retries never count. */
  correctIds: string[];
  wrongIds: string[];
  total: number;
}

/** Pure update after a test: stage stars (not for review sets) and per-word memory. */
export function applyListenResult(
  p: ListenProgress,
  r: ListenResult,
  today: string,
): { listen: ListenProgress; stars: 0 | 1 | 2 | 3 } {
  const stars = computeStars(r.correctIds.length, r.total, r.maxCombo);
  const stages = { ...p.stages };
  if (!r.stageId.startsWith(REVIEW_PREFIX)) {
    const old = stages[r.stageId] ?? { stars: 0, best: 0, plays: 0 };
    stages[r.stageId] = {
      stars: Math.max(old.stars, stars) as 0 | 1 | 2 | 3,
      best: Math.max(old.best, r.score),
      plays: old.plays + 1,
    };
  }
  const words = { ...p.words };
  const wrong = new Set(r.wrongIds);
  // Missed words move to the front of the weak list.
  const weak = new Set([...wrong, ...p.weak]);
  const mastered = new Set(p.mastered);
  for (const id of wrong) {
    words[id] = { days: [], wrong: (words[id]?.wrong ?? 0) + 1 };
    mastered.delete(id);
  }
  for (const id of r.correctIds) {
    if (wrong.has(id)) continue;
    const s = words[id] ?? { days: [], wrong: 0 };
    const days = s.days.includes(today)
      ? s.days
      : [...s.days, today].slice(-MASTERY_DAYS);
    words[id] = { ...s, days };
    if (days.length >= MASTERY_DAYS) {
      mastered.add(id);
      weak.delete(id);
    }
  }
  return {
    listen: { stages, words, weak: [...weak], mastered: [...mastered] },
    stars,
  };
}
