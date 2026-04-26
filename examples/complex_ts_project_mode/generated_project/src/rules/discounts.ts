import { toMoney } from "../pricing/rounding.js";

export function loyaltyDiscount(subtotal: number, isLoyalCustomer: boolean): number {
  if (!isLoyalCustomer) return 0;
  return toMoney(Math.min(subtotal * 0.05, 25));
}

export function bulkUnitsDiscount(totalUnits: number): number {
  if (totalUnits >= 20) return 10;
  if (totalUnits >= 10) return 4;
  return 0;
}
