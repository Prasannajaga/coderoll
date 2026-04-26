export function shippingFee(subtotal: number): number {
  if (subtotal < 0) throw new Error("subtotal must be >= 0");
  if (subtotal >= 100) return 0;
  if (subtotal >= 50) return 4.99;
  return 9.99;
}

export function estimateDeliveryDays(priority: boolean, inStockAll: boolean): number {
  if (!inStockAll) return 7;
  return priority ? 1 : 3;
}
