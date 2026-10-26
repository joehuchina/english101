import assert from "node:assert/strict";
import { test } from "node:test";
import { applyListenResult, emptyListen, sanitizeListen } from "./progress";
import {
  buildStages,
  CATEGORIES,
  computeStars,
  CONFUSABLE,
  MAX_STAGE,
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

test("stages follow categories, common words first, at most 12 each", () => {
  const rank: Record<string, number> = { a: 3, b: 1, c: 2 };
  const stages = buildStages(
    [cat("x", ["a", "b", "c", "gone"])],
    (id) => rank[id],
  );
  // Words missing from the atlas are skipped.
  assert.deepEqual(
    stages.map((s) => [s.id, s.words]),
    [["x-1", ["b", "c", "a"]]],
  );
  const many = Array.from({ length: 30 }, (_, i) => `w${i}`);
  const split = buildStages([cat("y", many)], (id) => Number(id.slice(1)));
  assert.deepEqual(
    split.map((s) => [s.id, s.words.length, s.parts]),
    [
      ["y-1", 10, 3],
      ["y-2", 10, 3],
      ["y-3", 10, 3],
    ],
  );
  assert.ok(split.every((s) => s.words.length <= MAX_STAGE));
});

test("distractors come from the stage, then the pool", () => {
  const d = pickDistractors(
    "a",
    ["a", "b", "c", "d", "e"],
    ["p", "q"],
    Math.random,
    [],
  );
  assert.equal(d.length, 3);
  assert.ok(d.every((w) => ["b", "c", "d", "e"].includes(w)));
  const small = pickDistractors(
    "a",
    ["a", "b"],
    ["a", "b", "p", "q"],
    Math.random,
    [],
  );
  assert.equal(small.length, 3);
  assert.ok(small.includes("b") && !small.includes("a"));
});

test("look-alike pictures never share a question", () => {
  const groups = [["a", "b", "c"]];
  for (let i = 0; i < 20; i++) {
    const d = pickDistractors(
      "a",
      ["a", "b", "c", "d", "e"],
      ["p", "q", "r"],
      Math.random,
      groups,
    );
    assert.equal(d.length, 3);
    assert.ok(!d.includes("b") && !d.includes("c"));
  }
  // The real groups only name listed words.
  const listed = new Set(CATEGORIES.flatMap((c) => c.words));
  assert.ok(CONFUSABLE.flat().every((w) => listed.has(w)));
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
