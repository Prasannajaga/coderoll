function add(value, step = 1) {
  return value + step;
}

function addMany(start, deltas) {
  return deltas.reduce((acc, item) => add(acc, item), start);
}

module.exports = { add, addMany };
