import test from "node:test";
import assert from "node:assert/strict";
import { solution } from "./solution.ts";

test("adds one", () => {
  assert.equal(solution(1), 2);
  assert.equal(solution(10), 11);
  assert.equal(solution(-1), 0);
});
