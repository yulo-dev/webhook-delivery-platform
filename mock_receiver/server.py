"""
Mock Webhook Receiver
======================
Simulates a customer's endpoint. Configurable failure rate
for testing retry and DLQ behavior.

Run: python -m mock_receiver.server
"""
import json
import random
import logging
from fastapi import FastAPI, Request, Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [RECEIVER] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Mock Webhook Receiver")

# Configurable failure rate (0.0 = always succeed, 1.0 = always fail)
FAILURE_RATE = 0.4
request_count = 0


@app.post("/webhooks")
async def receive_webhook(request: Request):
    global request_count
    request_count += 1

    body = await request.body()
    sig = request.headers.get("X-Webhook-Signature", "none")
    ts = request.headers.get("X-Webhook-Timestamp", "none")

    logger.info(
        f"📥 Received webhook #{request_count} | "
        f"sig={sig[:30]}... | ts={ts}"
    )

    # Simulate failures
    if random.random() < FAILURE_RATE:
        code = random.choice([500, 502, 503, 429])
        logger.warning(f"💥 Simulating failure: HTTP {code}")
        return Response(
            content=json.dumps({"error": f"Simulated {code}"}),
            status_code=code,
        )

    try:
        payload = json.loads(body)
        logger.info(f"✅ Processed: {json.dumps(payload)[:100]}")
    except Exception:
        logger.info(f"✅ Processed raw: {body[:100]}")

    return {"status": "received", "request_number": request_count}


@app.get("/health")
async def health():
    return {"status": "ok", "requests_received": request_count}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
