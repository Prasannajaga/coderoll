import test from "node:test";
import assert from "node:assert/strict";
import { addOne } from "./solution.js";

test("addOne increments", () => {
  assert.equal(addOne(0), 1);
  assert.equal(addOne(10), 11);
});
