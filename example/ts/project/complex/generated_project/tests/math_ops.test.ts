import test from "node:test";
import assert from "node:assert/strict";
import { add, addMany } from "../src/index.js";

test("add uses default step", () => {
  assert.equal(add(7), 8);
});

test("addMany folds increments", () => {
  assert.equal(addMany(1, [2, 3, 4]), 10);
});
