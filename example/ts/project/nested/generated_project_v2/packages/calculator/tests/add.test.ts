import test from "node:test";
import assert from "node:assert/strict";
import { addOne, addMany } from "../src/ops/add.js";

test("addOne increments", () => {
  assert.equal(addOne(9), 10);
});

test("addMany sums values", () => {
  assert.equal(addMany(3, [1, 2, 3]), 9);
});
