function addOne(value) {
  return value + 1;
}

function addMany(start, increments) {
  return increments.reduce((acc, inc) => acc + inc, start);
}

module.exports = { addOne, addMany };
