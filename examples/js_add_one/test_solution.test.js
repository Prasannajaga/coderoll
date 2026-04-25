const test = require("node:test");
const assert = require("node:assert/strict");
const { solution } = require("./solution.js");

test("adds one", () => {
  assert.equal(solution(1), 2);
  assert.equal(solution(10), 11);
  assert.equal(solution(-1), 0);
});
