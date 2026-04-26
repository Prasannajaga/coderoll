export function toMoney(value: number): number {
  return Number(value.toFixed(2));
}

export function clampNonNegative(value: number): number {
  return value < 0 ? 0 : value;
}
