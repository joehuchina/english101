import categoriesJson from "./categories.json";

/** A picture category; only words whose illustration shows the thing itself are listed. */
export interface ListenCategory {
  id: string;
  zh: string;
  en: string;
  icon: string;
  words: string[];
}

export type Round = 1 | 2 | 3;

export interface ListenStage {
  id: string;
  round: Round;
  category: ListenCategory;
  /** Part number when a category is split within a round. */
  part: number;
  parts: number;
  words: string[];
}

export const CATEGORIES = categoriesJson as ListenCategory[];

export const ROUNDS: Record<
  Round,
  { title: string; desc: string; level: string }
> = {
  1: {
    title: "第一轮 · 入门词",
    desc: "A1 最常见的实物，一听就能指出来。",
    level: "A1",
  },
  2: {
    title: "第二轮 · 常用词",
    desc: "A2 生活里天天见到的东西。",
    level: "A2",
  },
  3: {
    title: "第三轮 · 进阶词",
    desc: "B1 更具体的物品，按兴趣挑着学。",
    level: "B1",
  },
};

/** Stages larger than this are split into near-equal parts. */
export const MAX_STAGE = 12;
/** A picture test needs at least this many words of its own. */
export const MIN_STAGE = 4;

/** Stage ids with this prefix are ad-hoc practice sets and keep no stars. */
export const REVIEW_PREFIX = "review-";

function chunk<T>(items: T[], max: number): T[][] {
  const n = Math.max(1, Math.ceil(items.length / max));
  const size = Math.ceil(items.length / n);
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size)
    out.push(items.slice(i, i + size));
  return out;
}

/**
 * Stages per round (A1, A2, B1) and category. A round with too few words for a
 * picture test joins the category's previous round (or the next one).
 */
export function buildStages(
  categories: ListenCategory[],
  cefrOf: (id: string) => number | undefined,
): ListenStage[] {
  const byRound: Record<Round, Map<string, string[]>> = {
    1: new Map(),
    2: new Map(),
    3: new Map(),
  };
  for (const cat of categories) {
    const groups: Record<Round, string[]> = { 1: [], 2: [], 3: [] };
    for (const id of cat.words) {
      const level = cefrOf(id);
      if (level === undefined) continue;
      groups[Math.min(3, Math.max(1, level + 1)) as Round].push(id);
    }
    for (const r of [1, 2, 3] as Round[]) {
      if (groups[r].length === 0 || groups[r].length >= MIN_STAGE) continue;
      const into = ([r - 1, r + 1, r - 2, r + 2] as number[]).find(
        (o) => o >= 1 && o <= 3 && groups[o as Round].length > 0,
      ) as Round | undefined;
      if (!into) continue;
      groups[into] =
        into < r
          ? [...groups[into], ...groups[r]]
          : [...groups[r], ...groups[into]];
      groups[r] = [];
    }
    for (const r of [1, 2, 3] as Round[])
      if (groups[r].length) byRound[r].set(cat.id, groups[r]);
  }
  const stages: ListenStage[] = [];
  for (const r of [1, 2, 3] as Round[])
    for (const cat of categories) {
      const words = byRound[r].get(cat.id);
      if (!words) continue;
      const parts = chunk(words, MAX_STAGE);
      parts.forEach((part, i) =>
        stages.push({
          id: `${r}-${cat.id}-${i + 1}`,
          round: r,
          category: cat,
          part: i + 1,
          parts: parts.length,
          words: part,
        }),
      );
    }
  return stages;
}

export const stageTitle = (
  s: Pick<ListenStage, "category" | "part" | "parts">,
) => (s.parts > 1 ? `${s.category.zh} ${s.part}` : s.category.zh);

/** Three wrong pictures: from the same stage first, then from other categories. */
export function pickDistractors(
  target: string,
  stageWords: string[],
  pool: string[],
  random = Math.random,
): string[] {
  const shuffled = (xs: string[]) =>
    xs
      .map((x) => [random(), x] as const)
      .sort((a, b) => a[0] - b[0])
      .map(([, x]) => x);
  const out = shuffled(stageWords.filter((w) => w !== target)).slice(0, 3);
  if (out.length < 3) {
    const used = new Set([target, ...out, ...stageWords]);
    out.push(
      ...shuffled(pool.filter((w) => !used.has(w))).slice(0, 3 - out.length),
    );
  }
  return out;
}

/** Stars for a test: 70% → 1, 85% → 2, 95% with a long streak → 3. */
export function computeStars(
  correct: number,
  total: number,
  maxCombo: number,
): 0 | 1 | 2 | 3 {
  const accuracy = total > 0 ? correct / total : 0;
  if (accuracy >= 0.95 && maxCombo >= Math.min(10, total)) return 3;
  if (accuracy >= 0.85) return 2;
  if (accuracy >= 0.7) return 1;
  return 0;
}
