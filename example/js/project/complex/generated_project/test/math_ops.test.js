const test = require("node:test");
const assert = require("node:assert/strict");
const { add, addMany } = require("../src/index");

test("add uses default step", () => {
  assert.equal(add(7), 8);
});

test("addMany folds increments", () => {
  assert.equal(addMany(1, [2, 3, 4]), 10);
});
