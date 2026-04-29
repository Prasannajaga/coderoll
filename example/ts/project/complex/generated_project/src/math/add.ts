export function add(value: number, step = 1): number {
  return value + step;
}

export function addMany(start: number, deltas: number[]): number {
  return deltas.reduce((acc, item) => add(acc, item), start);
}
