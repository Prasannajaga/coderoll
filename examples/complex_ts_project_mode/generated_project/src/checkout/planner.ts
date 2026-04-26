import type { CartItem, CheckoutPlan } from "../domain/types.js";
import { summarizeOrder } from "../pricing/calculations.js";
import { clampNonNegative, toMoney } from "../pricing/rounding.js";
import { bulkUnitsDiscount, loyaltyDiscount } from "../rules/discounts.js";
import { estimateDeliveryDays, shippingFee } from "../shipping.js";

export function planCheckout(
  items: CartItem[],
  taxRate: number,
  priority: boolean,
  isLoyalCustomer: boolean,
): CheckoutPlan {
  const normalizedSkus = items.map((item) => item.sku.trim().toUpperCase()).sort();
  const totalUnits = items.reduce((acc, item) => acc + item.qty, 0);

  const sub = items.reduce((acc, item) => acc + item.qty * item.unitPrice, 0);
  const shipping = shippingFee(sub);
  const discount = toMoney(
    loyaltyDiscount(sub, isLoyalCustomer) + bulkUnitsDiscount(totalUnits),
  );

  const summary = summarizeOrder(items, taxRate, shipping);
  const payableTotal = clampNonNegative(toMoney(summary.total - discount));

  return {
    normalizedSkus,
    shipping,
    discount,
    payableTotal,
    deliveryDays: estimateDeliveryDays(priority, true),
    summary,
  };
}
