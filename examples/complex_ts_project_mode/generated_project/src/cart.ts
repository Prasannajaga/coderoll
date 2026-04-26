export interface CartItem {
  sku: string;
  qty: number;
  unitPrice: number;
}

export interface OrderSummary {
  subtotal: number;
  tax: number;
  shipping: number;
  total: number;
}

export function normalizeSku(raw: string): string {
  return raw.trim().toUpperCase();
}

export function lineTotal(item: CartItem): number {
  if (item.qty < 0) throw new Error("qty must be >= 0");
  if (item.unitPrice < 0) throw new Error("unitPrice must be >= 0");
  return Number((item.qty * item.unitPrice).toFixed(2));
}

export function subtotal(items: CartItem[]): number {
  return Number(items.reduce((acc, item) => acc + lineTotal(item), 0).toFixed(2));
}

export function summarizeOrder(
  items: CartItem[],
  taxRate: number,
  shipping: number,
): OrderSummary {
  if (taxRate < 0) throw new Error("taxRate must be >= 0");
  if (shipping < 0) throw new Error("shipping must be >= 0");

  const sub = subtotal(items);
  const tax = Number((sub * taxRate).toFixed(2));
  const total = Number((sub + tax + shipping).toFixed(2));

  return {
    subtotal: sub,
    tax,
    shipping: Number(shipping.toFixed(2)),
    total,
  };
}
