import test from "node:test";
import assert from "node:assert/strict";
import {
  bulkUnitsDiscount,
  estimateDeliveryDays,
  lineTotal,
  normalizeSku,
  planCheckout,
  shippingFee,
  summarizeOrder,
} from "../dist/index.js";

test("normalizeSku trims and uppercases", () => {
  assert.equal(normalizeSku("  abc-1  "), "ABC-1");
});

test("lineTotal handles decimal prices", () => {
  assert.equal(lineTotal({ sku: "A", qty: 3, unitPrice: 19.995 }), 59.98);
});

test("summarizeOrder computes totals", () => {
  const summary = summarizeOrder(
    [
      { sku: "A", qty: 2, unitPrice: 20 },
      { sku: "B", qty: 1, unitPrice: 10 },
    ],
    0.1,
    4.99,
  );

  assert.deepEqual(summary, {
    subtotal: 50,
    tax: 5,
    shipping: 4.99,
    total: 59.99,
  });
});

test("shippingFee tiers", () => {
  assert.equal(shippingFee(10), 9.99);
  assert.equal(shippingFee(60), 4.99);
  assert.equal(shippingFee(120), 0);
});

test("estimateDeliveryDays respects stock and priority", () => {
  assert.equal(estimateDeliveryDays(true, true), 1);
  assert.equal(estimateDeliveryDays(false, true), 3);
  assert.equal(estimateDeliveryDays(true, false), 7);
});

test("planCheckout composes nested pricing + rules + shipping", () => {
  const plan = planCheckout(
    [
      { sku: " sku-a ", qty: 12, unitPrice: 10 },
      { sku: "sku-b", qty: 3, unitPrice: 5 },
    ],
    0.1,
    true,
    true,
  );

  assert.deepEqual(plan, {
    normalizedSkus: ["SKU-A", "SKU-B"],
    shipping: 0,
    discount: 10.75,
    payableTotal: 139.25,
    deliveryDays: 1,
    summary: {
      subtotal: 135,
      tax: 13.5,
      shipping: 0,
      total: 148.5,
    },
  });
});

test("bulkUnitsDiscount tiers", () => {
  assert.equal(bulkUnitsDiscount(5), 0);
  assert.equal(bulkUnitsDiscount(10), 4);
  assert.equal(bulkUnitsDiscount(25), 10);
});

test("negative qty throws", () => {
  assert.throws(() => lineTotal({ sku: "A", qty: -1, unitPrice: 2 }));
});
