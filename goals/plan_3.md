# Plan 3: CAP Protocol Integration
**DataScout — CROO Agent Hackathon**

---

## Overview

Integration with CROO Agent Protocol (CAP) for the transaction flow: Negotiation → Lock → Deliver → Clear. This is the bridge between the DataScout agent and the CROO Network ecosystem.

**Dependency:** plan_1 (Project Setup), plan_2 (AI Query Parser)

---

## CAP Flow Recap

```
1. NEGOTIATION — Agent lists services + pricing
2. LOCK — Buyer agrees, funds escrowed on-chain
3. DELIVER — Agent executes task, submits proof
4. CLEAR — Verification, payment release, reputation update
```

---

## Deliverables

1. **CAP Client** — `src/cap/client.py` — WebSocket connection to CAP API
2. **CAP Models** — `src/models/cap.py` — Order, Delivery, Settlement models
3. **Negotiation Handler** — `src/cap/negotiation.py` — Price estimation based on query complexity
4. **Deliver Formatter** — `src/cap/deliver.py` — Format output per CAP delivery schema
5. **Clear Handler** — `src/cap/clear.py` — Settlement + proof-of-work hash generation

---

## CAP API Endpoints

```
Base URL: https://api.croo.network
WebSocket: wss://api.croo.network/ws

- POST /api/agents — Register agent
- GET /api/agents/{id} — Get agent info
- POST /api/capabilities — List capabilities (services)
- POST /api/orders — Create order
- GET /api/orders/{id} — Get order status
- WS /ws — Real-time order events
```

---

## Price Estimation Logic

```python
def estimate_price(parsed_query: ParsedQuery) -> float:
    """Estimate price in USDC based on query complexity."""
    base_price = 0.01
    sources_count = 15 if not parsed_query.region else 8
    extras = 0
    if parsed_query.min_rows:
        extras += 0.005
    if parsed_query.time_range:
        extras += 0.005
    if parsed_query.license != "any":
        extras += 0.005
    return base_price + (sources_count * 0.002) + extras
```

---

## Implementation Steps

1. [ ] Create `src/models/cap.py` — CapOrder, CapDelivery, CapSettlement models
2. [ ] Create `src/cap/client.py` — WebSocket client wrapper
3. [ ] Create `src/cap/negotiation.py` — Price estimation
4. [ ] Create `src/cap/deliver.py` — Output formatting for CAP delivery
5. [ ] Create `src/cap/clear.py` — Settlement + hash proof generation
6. [ ] Add order listener + status endpoints to main.py
7. [ ] Write tests for price estimation and delivery formatting

---

## Acceptance Criteria

- [ ] Agent can register with CAP network
- [ ] Price estimation works for various query complexities
- [ ] WebSocket connection to CAP API can be established
- [ ] Delivery output matches CAP schema
- [ ] Hash proof of work is generated correctly
- [ ] All price estimation tests pass
