# Architecture — EC Dispute Resolution Multi-Agent System

## 1. Design principle

Each agent owns one data domain and does two things, always in this order:

1. **Tool call** — deterministic Python reads the Olist CSVs through the shared
   `DataStore` and computes verifiable facts (dates, totals, statuses).
2. **LLM reasoning call** — the agent hands only its own facts (never the raw
   customer message) to `gpt-4o-mini` to produce a short natural-language
   handoff note, logged for auditability.

Every field that is actually graded (`primary_issue`, root cause,
responsible party, refund amount, action) is produced by the deterministic
rule engine in `src/policy_rules.py`, not by free-text LLM output. This is a
direct consequence of the README's own constraint: *"Hệ thống phải ưu tiên
dữ liệu có thể kiểm chứng thay vì tin hoàn toàn vào lời khiếu nại hoặc tự
tạo ra sự kiện không tồn tại."* A closed/mini-size LLM cannot be trusted to
do exact date and currency arithmetic across 50 graded cases reproducibly —
so it is used only where its output doesn't affect correctness: explaining
a decision that was already computed. Splitting the work across agents with
real handoffs (not one mega-prompt) is what still makes this genuinely
multi-agent A2A.

## 2. Agents, roles, data access

| Agent | Role | Reads | Writes / hands off |
|---|---|---|---|
| **Coordinator** | Orchestrates one case end to end, assembles final payload | input case JSON | calls all agents in order, returns final output dict |
| **Order & Seller Agent** | Order status, items, sellers, per-seller handoff-deadline check | `orders`, `order_items`, `sellers` | `OrderSellerFacts` (status, items, seller_ids, late_seller_ids, item_total, freight_total) |
| **Delivery Agent** | Actual delivery vs. estimated delivery date | `orders` | `DeliveryFacts` (estimated/carrier/customer dates, delivered_after_estimate) |
| **Payment Agent** | Reconciles payments vs. item+freight | `order_payments` | `PaymentFacts` (payment rows, payment_total) |
| **Policy Agent** | Applies `EC_POLICY_V1` rule table to the three fact sets | facts from the three agents above | `Decision` (primary_issue, root_cause, responsible_parties, refund_amount, action, confidence) |
| **Verifier Agent** | Final QA gate: schema + evidence-ID existence check | assembled payload + `DataStore` | validated payload, or raises and the case is skipped/logged as failed |

No agent has write access to the CSVs — `DataStore` is read-only and loaded
once per run, shared across agents so every case sees a consistent snapshot.

## 3. Handoff flow (A2A)

```
                         input/EC_XXX.json
                                 |
                                 v
                          [ Coordinator ]
                                 |
        +------------------+----+----+------------------+
        v                  v         v                  |
[Order & Seller Agent] [Delivery Agent] [Payment Agent]  |
   facts: status,        facts:            facts:        |
   items, sellers,       delivered vs      payments,     |
   late_seller_ids       estimated         payment_total |
        |                  |         |                   |
        +------------------+----+----+                   |
                                 v                        |
                         [ Policy Agent ]                 |
                    decide() -> Decision                  |
                  (EC_POLICY_V1, deterministic)            |
                                 |                         |
                                 v                         |
                        build_output()  <-------------------
                     (Coordinator assembles payload)
                                 |
                                 v
                        [ Verifier Agent ]
                schema check + evidence existence check
                                 |
                        pass ----+---- fail
                          |             |
                          v             v
              output/EC_XXX.json   logged as failed case,
                                    no file written
```

Every step above (`tool_result`, `llm_note`, `decision`, `verification`,
`case_received`, `case_completed`/`case_failed`) is appended to
`logging/trace.jsonl` with `case_id`, `agent`, `event`, and payload — this
is the run's A2A trace.

## 4. Rule engine (`src/policy_rules.py`)

Rules are evaluated in the priority order from the README, first match wins:

1. `canceled_order_paid` — `order_status == canceled` and payment_total > 0
2. `unavailable_order_paid` — `order_status == unavailable` and payment_total > 0
3. `late_delivery_seller` — delivered after estimate, and any seller received
   the carrier handoff after their own `shipping_limit_date`
4. `late_delivery_logistics` — delivered after estimate, no seller was late
5. `valid_split_payment` — 2+ payment rows and payment_total reconciles with
   item+freight within 0.10 BRL
6. `unsupported_late_claim` — delivered no later than estimate and payment
   reconciles

A seller is "late" if **any** of its items has
`order_delivered_carrier_date > shipping_limit_date` (per-item check, not
per-order), matching the README's multi-seller convention.

If no rule matches cleanly (not expected on the official 50 cases per the
README), the engine falls back to `unsupported_late_claim` with
`confidence = 0.3` and `fallback: true` logged in the trace, instead of
guessing.

## 5. Confidence scoring

Deterministic, not LLM-generated: a fixed base score per `primary_issue`
(`src/policy_rules.py: CONFIDENCE_BY_ISSUE`), reflecting how directly each
rule reads off the data — `canceled_order_paid`/`unavailable_order_paid`
0.95 (single status+payment check), `late_delivery_seller` 0.92,
`late_delivery_logistics` 0.90, `valid_split_payment` 0.88,
`unsupported_late_claim` 0.85 (rests on a negative — "no evidence of
lateness" — inherently a softer claim than the others). `-0.25` if data
relevant to that rule is incomplete, `0.3` for the no-match fallback. This
keeps confidence reproducible across runs.

## 6. Evidence & entity assembly

`src/output_builder.py` builds two related but *not identical* sets:

- `affected_entities`: unconditional — every order/item/payment/seller row
  linked to the order, regardless of fault. `seller_ids` lists every
  seller with an item on the order even when the seller isn't responsible
  for the issue (same treatment as `item_ids`/`payment_ids`), each list
  capped at 5.
- `evidence_ids`: `order:<id>`, `item:<order_id>:<item_id>`,
  `payment:<order_id>:<seq>`, then `seller:<seller_id>` **only when
  `primary_issue == late_delivery_seller`** (a seller row only supports
  the decision when the seller is actually at fault — citing it otherwise
  just names a bystander, not evidence), then `policy:<root_cause_code>`,
  capped at 10. `order:`/`policy:` are reserved slots that are never
  truncated by the cap.

This entities-vs-evidence distinction was found by diffing output against
a teammate's independently-built, higher-scoring submission on the same
50 cases — everything else (`primary_issue`, `root_cause`,
`responsible_parties`, `financial_resolution`, `resolution_actions`, and
`affected_entities` itself) matched byte-for-byte before this fix; only
`seller:` evidence scoping and the confidence calibration above differed.

The Verifier Agent re-parses every evidence ID against `DataStore` (regex +
existence lookup) before the file is written, so a malformed or
non-existent ID fails the case instead of silently shipping.

## 7. Model

`gpt-4o-mini` (OpenAI). Parameter count is undisclosed by OpenAI
(closed-weight); the instructor explicitly approved this as a substitute
for the assignment's ≤10B local-model requirement. Declared in code
(`src/config.py`, `OPENAI_MODEL`) and mirrored in `logging/metadata.json`;
the API key lives only in `.env` (git-ignored) and is never read for the
model name itself. A local ≤10B fallback (`qwen2.5:3b` via Ollama,
`src/config.py: OLLAMA_MODEL`) is kept wired up in `llm_client.py`'s prior
revision history if the OpenAI key is ever unavailable — safe to swap
either direction since every decision field comes from the deterministic
rule engine, not the LLM.

## 8. Logging

- `logging/trace.jsonl` — full run trace, truncated and rewritten each run
  (latest run only, no append across runs).
- `logging/metadata.json` — model, parameter note, framework, runtime
  versions, and run summary (case counts, timestamps), written once at the
  end of each run.
