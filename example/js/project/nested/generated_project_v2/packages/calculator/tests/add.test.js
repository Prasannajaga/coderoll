const test = require("node:test");
const assert = require("node:assert/strict");
const { addOne, addMany } = require("../src/ops/add");

test("addOne increments", () => {
  assert.equal(addOne(9), 10);
});

test("addMany sums a list", () => {
  assert.equal(addMany(3, [1, 2, 3]), 9);
});
