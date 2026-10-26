import categoriesJson from "./categories.json";
import confusableJson from "./confusable.json";

/** A picture category; look-alike pictures are grouped in confusable.json. */
export interface ListenCategory {
  id: string;
  zh: string;
  en: string;
  icon: string;
  words: string[];
}

export interface ListenStage {
  id: string;
  category: ListenCategory;
  /** Part number when a category is split into several stages. */
  part: number;
  parts: number;
  words: string[];
}

export const CATEGORIES = categoriesJson as ListenCategory[];

/** Groups of words whose pictures look alike; they never share a question. */
export const CONFUSABLE = confusableJson as string[][];

/** Stages larger than this are split into near-equal parts. */
export const MAX_STAGE = 12;

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
 * Stages per category, common words first. `rank` orders words (lower is more
 * common) and returns undefined for words missing from the atlas.
 */
export function buildStages(
  categories: ListenCategory[],
  rank: (id: string) => number | undefined,
): ListenStage[] {
  const stages: ListenStage[] = [];
  for (const cat of categories) {
    const words = cat.words
      .map((id) => [id, rank(id)] as const)
      .filter((x): x is readonly [string, number] => x[1] !== undefined)
      .sort((a, b) => a[1] - b[1])
      .map(([id]) => id);
    if (!words.length) continue;
    const parts = chunk(words, MAX_STAGE);
    parts.forEach((part, i) =>
      stages.push({
        id: `${cat.id}-${i + 1}`,
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

/** Words whose pictures could be mistaken for the target's. */
export function lookAlikes(target: string, groups = CONFUSABLE): Set<string> {
  const out = new Set<string>();
  for (const g of groups) if (g.includes(target)) g.forEach((w) => out.add(w));
  return out;
}

/**
 * Three wrong pictures: from the same stage first, then from other categories,
 * never one that looks like the target.
 */
export function pickDistractors(
  target: string,
  stageWords: string[],
  pool: string[],
  random = Math.random,
  groups = CONFUSABLE,
): string[] {
  const shuffled = (xs: string[]) =>
    xs
      .map((x) => [random(), x] as const)
      .sort((a, b) => a[0] - b[0])
      .map(([, x]) => x);
  const blocked = lookAlikes(target, groups);
  blocked.add(target);
  const out = shuffled(stageWords.filter((w) => !blocked.has(w))).slice(0, 3);
  if (out.length < 3) {
    const used = new Set([...blocked, ...out, ...stageWords]);
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
