const test = require("node:test");
const assert = require("node:assert/strict");
const { addOne } = require("./solution");

test("addOne increments a number", () => {
  assert.equal(addOne(0), 1);
  assert.equal(addOne(10), 11);
});
