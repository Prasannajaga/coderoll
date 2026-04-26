import type { CartItem, OrderSummary } from "../domain/types.js";
import { clampNonNegative, toMoney } from "./rounding.js";

export function normalizeSku(raw: string): string {
  return raw.trim().toUpperCase();
}

export function lineTotal(item: CartItem): number {
  if (item.qty < 0) throw new Error("qty must be >= 0");
  if (item.unitPrice < 0) throw new Error("unitPrice must be >= 0");
  return toMoney(item.qty * item.unitPrice);
}

export function subtotal(items: CartItem[]): number {
  return toMoney(items.reduce((acc, item) => acc + lineTotal(item), 0));
}

export function summarizeOrder(
  items: CartItem[],
  taxRate: number,
  shipping: number,
): OrderSummary {
  if (taxRate < 0) throw new Error("taxRate must be >= 0");
  if (shipping < 0) throw new Error("shipping must be >= 0");

  const sub = subtotal(items);
  const tax = toMoney(sub * taxRate);
  const total = clampNonNegative(toMoney(sub + tax + shipping));

  return {
    subtotal: sub,
    tax,
    shipping: toMoney(shipping),
    total,
  };
}
