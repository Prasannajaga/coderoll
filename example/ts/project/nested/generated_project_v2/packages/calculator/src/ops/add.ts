export function addOne(value: number): number {
  return value + 1;
}

export function addMany(start: number, increments: number[]): number {
  return increments.reduce((acc, item) => acc + item, start);
}
