#!/usr/bin/env python3
"""
Demo Script
============
Walks through the full webhook platform flow:
1. Register an endpoint
2. Publish an event
3. Check delivery status
4. View DLQ

Usage:
  python demo.py                  # default: API at localhost:8000
  python demo.py http://localhost:8000
"""
import sys
import time
import httpx
import json

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
c = httpx.Client(base_url=BASE, timeout=10)

def heading(text):
    print(f"\n{'='*60}\n  {text}\n{'='*60}")

def pp(data):
    print(json.dumps(data, indent=2, default=str))


# ── 1. Register endpoint ──
heading("1. Register Webhook Endpoint")
resp = c.post("/v1/webhook", json={
    "user_id": "usr_demo",
    "event_type": "invoice.paid",
    "endpoint": "http://mock_receiver:9000/webhooks",
})
ep = resp.json()
pp(ep)
ep_id = ep["id"]
secret = ep["secret"]
print(f"\n→ Endpoint ID: {ep_id}")
print(f"→ Secret: {secret}")


# ── 2. Publish event ──
heading("2. Publish Event (simulating internal service)")
resp = c.post("/v1/events", json={
    "user_id": "usr_demo",
    "event_type": "invoice.paid",
    "payload": {
        "invoice_id": "inv_12345",
        "amount": 9900,
        "currency": "usd",
        "customer": "cus_acme",
    },
})
event_result = resp.json()
pp(event_result)
event_id = event_result.get("event_id")


# ── 3. Wait for delivery ──
heading("3. Waiting for Delivery Worker...")
for i in range(10):
    time.sleep(2)
    resp = c.get("/v1/deliveries", params={"event_id": event_id})
    deliveries = resp.json()
    if deliveries:
        latest = deliveries[0]
        status = latest["status"]
        attempts = latest["attempt_count"]
        print(f"  [{i*2}s] status={status}  attempts={attempts}")
        if status in ("delivered", "failed"):
            break
    else:
        print(f"  [{i*2}s] waiting...")


# ── 4. Delivery log ──
heading("4. Delivery Attempts")
resp = c.get("/v1/deliveries", params={"event_id": event_id})
pp(resp.json())


# ── 5. Stats ──
heading("5. Platform Stats")
resp = c.get("/v1/deliveries/stats")
pp(resp.json())


# ── 6. DLQ ──
heading("6. Dead Letter Queue")
resp = c.get("/v1/deliveries/dlq")
dlq = resp.json()
if dlq:
    pp(dlq)
else:
    print("  (empty — all events delivered successfully)")


# ── 7. List all endpoints ──
heading("7. All Registered Endpoints")
resp = c.get("/v1/webhook")
pp(resp.json())

print(f"\n{'='*60}")
print("  Demo complete! Visit {BASE}/docs for Swagger UI")
print(f"{'='*60}\n")
