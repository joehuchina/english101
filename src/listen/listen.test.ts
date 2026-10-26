import assert from "node:assert/strict";
import { test } from "node:test";
import { applyListenResult, emptyListen, sanitizeListen } from "./progress";
import {
  buildStages,
  CATEGORIES,
  computeStars,
  MAX_STAGE,
  MIN_STAGE,
  pickDistractors,
  type ListenCategory,
} from "./stages";

const cat = (id: string, words: string[]): ListenCategory => ({
  id,
  zh: id,
  en: id,
  icon: "",
  words,
});

test("categories list each word once", () => {
  const all = CATEGORIES.flatMap((c) => c.words);
  assert.equal(new Set(all).size, all.length);
});

test("stages follow CEFR rounds and stay within size limits", () => {
  const level: Record<string, number> = {
    a: 0,
    b: 0,
    c: 0,
    d: 0,
    e: 1,
    f: 1,
    g: 1,
    h: 1,
    i: 2,
  };
  const stages = buildStages([cat("x", Object.keys(level))], (id) => level[id]);
  assert.deepEqual(
    stages.map((s) => [s.id, s.words]),
    [
      ["1-x-1", ["a", "b", "c", "d"]],
      // A lone B1 word joins A2 so the test still has four pictures of its own.
      ["2-x-1", ["e", "f", "g", "h", "i"]],
    ],
  );
  const many = Array.from({ length: 30 }, (_, i) => `w${i}`);
  const split = buildStages([cat("y", many)], () => 0);
  assert.equal(split.length, 3);
  assert.ok(
    split.every(
      (s) =>
        s.words.length <= MAX_STAGE &&
        s.words.length >= MIN_STAGE &&
        s.parts === 3,
    ),
  );
});

test("words missing from the atlas are skipped", () => {
  assert.deepEqual(
    buildStages([cat("z", ["a", "gone"])], (id) =>
      id === "a" ? 0 : undefined,
    )[0].words,
    ["a"],
  );
});

test("distractors come from the stage, then the pool", () => {
  const d = pickDistractors("a", ["a", "b", "c", "d", "e"], ["p", "q"]);
  assert.equal(d.length, 3);
  assert.ok(d.every((w) => ["b", "c", "d", "e"].includes(w)));
  const small = pickDistractors("a", ["a", "b"], ["a", "b", "p", "q"]);
  assert.equal(small.length, 3);
  assert.ok(small.includes("b") && !small.includes("a"));
});

test("stars", () => {
  assert.equal(computeStars(6, 10, 3), 0);
  assert.equal(computeStars(7, 10, 3), 1);
  assert.equal(computeStars(9, 10, 3), 2);
  assert.equal(computeStars(10, 10, 9), 2);
  assert.equal(computeStars(10, 10, 10), 3);
});

test("results update stars, weak and mastered words", () => {
  const r1 = applyListenResult(
    emptyListen(),
    {
      stageId: "1-x-1",
      score: 500,
      maxCombo: 2,
      correctIds: ["a", "b"],
      wrongIds: ["c"],
      total: 3,
    },
    "2026-10-25",
  );
  assert.equal(r1.stars, 0);
  assert.deepEqual(r1.listen.stages["1-x-1"], {
    stars: 0,
    best: 500,
    plays: 1,
  });
  assert.deepEqual(r1.listen.weak, ["c"]);
  const r2 = applyListenResult(
    r1.listen,
    {
      stageId: "review-weak",
      score: 100,
      maxCombo: 3,
      correctIds: ["a", "c"],
      wrongIds: [],
      total: 2,
    },
    "2026-10-26",
  );
  assert.equal(r2.listen.stages["review-weak"], undefined);
  assert.deepEqual(r2.listen.mastered, ["a"]);
  // c was missed yesterday, so one good day is not enough yet.
  assert.deepEqual(r2.listen.weak, ["c"]);
  const r3 = applyListenResult(
    r2.listen,
    {
      stageId: "review-weak",
      score: 100,
      maxCombo: 1,
      correctIds: ["c"],
      wrongIds: [],
      total: 1,
    },
    "2026-10-27",
  );
  assert.deepEqual(r3.listen.weak, []);
});

test("sanitize drops malformed listen data", () => {
  const l = sanitizeListen({
    stages: {
      ok: { stars: 2, best: 10, plays: 1 },
      bad: { stars: 9, best: 1, plays: 1 },
    },
    words: { a: { days: ["2026-10-25", "x"], wrong: 1 } },
    weak: ["a", 3],
  });
  assert.deepEqual(Object.keys(l.stages), ["ok"]);
  assert.deepEqual(l.words.a, { days: ["2026-10-25"], wrong: 1 });
  assert.deepEqual(l.weak, ["a"]);
  assert.deepEqual(sanitizeListen("nope"), emptyListen());
});
