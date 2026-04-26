import test from "node:test";
import assert from "node:assert/strict";
import { addOne } from "../dist/mathUtils.js";

test("addOne increments integers", () => {
  assert.equal(addOne(1), 2);
  assert.equal(addOne(10), 11);
  assert.equal(addOne(-1), 0);
});
