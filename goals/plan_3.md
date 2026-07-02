# Plan 3: CAP Protocol Integration
**DataScout — CROO Agent Hackathon**

---

## Overview

Integrasi dengan CROO Agent Protocol (CAP) untuk alur transaksi: Negotiation → Lock → Deliver → Clear. Ini adalah jembatan antara DataScout agent dengan ekosistem CROO Network.

**Dependensi:** plan_1 (Project Setup)

---

## CAP Flow Recap

```
1. NEGOTIATION — Agent listing services + pricing
2. LOCK — Buyer agrees, funds di-escrow on-chain
3. DELIVER — Agent executes task, submits proof
4. CLEAR — Verification, payment release, reputation update
```

---

## Deliverables

1. **CAP Client** — `src/cap/client.py` — WebSocket connection ke CAP API
2. **Negotiation Handler** — `src/cap/negotiation.py` — Estimasi harga berdasar query complexity
3. **Order Listener** — Listen for incoming orders via WebSocket
4. **Deliver Formatter** — Format output sesuai CAP delivery schema
5. **Clear Handler** — Handle settlement + hash bukti pengerjaan

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
    """Estimasi harga dalam USDC berdasar kompleksitas query."""
    base_price = 0.01  # Harga dasar per query
    
    # Tambahan berdasar jumlah sumber yang perlu dicari
    source_multiplier = {"any": 15, "specific": 5}
    sources_count = 15 if not parsed_query.region else 8
    
    # Tambahan untuk fitur lanjutan
    extras = 0
    if parsed_query.min_rows:
        extras += 0.005  # Filter ukuran
    if parsed_query.time_range:
        extras += 0.005  # Filter waktu
    if parsed_query.license != "any":
        extras += 0.005  # Filter lisensi
    
    return base_price + (sources_count * 0.002) + extras
```

---

## Implementation Steps

1. [ ] Create `src/cap/__init__.py`
2. [ ] Create `src/models/cap.py` — Order, Delivery, Settlement models
3. [ ] Create `src/cap/client.py` — WebSocket client wrapper
4. [ ] Create `src/cap/negotiation.py` — Price estimation
5. [ ] Create `src/cap/deliver.py` — Output formatting for CAP
6. [ ] Create `src/cap/clear.py` — Settlement handler
7. [ ] Add order listener endpoint
8. [ ] Test with CAP sandbox

---

## Acceptance Criteria

- [ ] Agent can register with CAP network
- [ ] Price estimation works for various query complexities
- [ ] WebSocket connection to CAP API established
- [ ] Order events received in real-time
- [ ] Delivery output matches CAP schema
- [ ] Hash bukti pengerjaan generated correctly
