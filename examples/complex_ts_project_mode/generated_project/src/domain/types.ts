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

export interface CheckoutPlan {
  normalizedSkus: string[];
  shipping: number;
  discount: number;
  payableTotal: number;
  deliveryDays: number;
  summary: OrderSummary;
}
