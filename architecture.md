# Multi-Agent E-commerce Dispute Resolution

## Agent topology

```text
Case JSON -> Coordinator
               |-- Order & Seller Agent
               |-- Payment Agent
               |-- Delivery Agent --------+
               |-- Policy Agent            | structured handoffs
               +---------------------------+
                             |
                          Verifier -> output/EC_NNN.json
```

## Roles and access

| Agent | Responsibility | Read access | Write/handoff |
|---|---|---|---|
| Coordinator | Dispatch case and merge specialist results | `input/` | Specialist requests, output draft |
| Order & Seller | Order state, items and seller ownership | orders, items, sellers CSV | Order/seller facts |
| Payment | Reconcile payment with item and freight totals | payments, items CSV | Payment facts |
| **Delivery** | Compare delivery with estimate and carrier handoff with item deadlines | orders and items CSV (read-only) | `DeliveryHandoff` |
| Policy | Apply `EC_POLICY_V1` in priority order | Specialist handoffs | Issue, refund and action proposal |
| Verifier | Validate schema, evidence and financial totals | CSV data and output draft | Approved output JSON or validation errors |

## Delivery Agent contract

The Delivery Agent is implemented in `delivery_agent.py`. It receives `case_id`
and `order_id`, and returns a structured handoff containing delivery status,
late-delivery flags, violating items/sellers, verifiable evidence IDs, source
timestamps, and a suggested cause code. It does not decide the refund; Policy
Agent retains that authority so that business-rule priority remains centralized.

Decision flow:

1. If the actual customer delivery date is later than the estimated date, the
   delivery is late.
2. For a late order, compare the carrier handoff timestamp with every item's
   `shipping_limit_date`.
3. A handoff after an item deadline suggests `SELLER_HANDOFF_AFTER_LIMIT` and
   identifies that item's seller. Otherwise it suggests
   `CARRIER_DELIVERED_AFTER_ESTIMATE`.
4. A delivery on or before the estimate suggests `DELIVERY_WITHIN_ESTIMATE`.
5. Missing delivery dates are reported as unknown; the agent does not invent facts.

## Trace and security

Every completed Delivery Agent investigation writes one JSON object to
`logging/trace.jsonl`. A full run starts with `--reset-trace` so only the newest
run remains. Trace records contain case/order facts and handoffs, never API keys.
Secrets are read by provider integration from an uncommitted `.env`; the model
name is a source constant and is repeated in `logging/metadata.json`.
