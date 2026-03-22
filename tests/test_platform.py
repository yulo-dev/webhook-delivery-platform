import pytest
import json
from fastapi.testclient import TestClient
from app.main import app
from app.db.database import init_db, engine, Base
from app.services.signing_service import generate_secret, sign_payload, verify_signature


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ── Signing Service Tests ──

class TestSigningService:
    def test_generate_secret(self):
        secret = generate_secret()
        assert secret.startswith("whsec_")
        assert len(secret) > 10

    def test_sign_and_verify(self):
        secret = generate_secret()
        payload = json.dumps({"event": "invoice.paid", "amount": 100})
        headers = sign_payload(payload, secret)

        assert "X-Webhook-Timestamp" in headers
        assert headers["X-Webhook-Signature"].startswith("sha256=")

        # Verify
        valid = verify_signature(
            payload, secret,
            headers["X-Webhook-Timestamp"],
            headers["X-Webhook-Signature"],
        )
        assert valid is True

    def test_verify_fails_with_wrong_secret(self):
        secret = generate_secret()
        payload = '{"test": true}'
        headers = sign_payload(payload, secret)

        valid = verify_signature(
            payload, "wrong_secret",
            headers["X-Webhook-Timestamp"],
            headers["X-Webhook-Signature"],
        )
        assert valid is False

    def test_verify_fails_with_tampered_payload(self):
        secret = generate_secret()
        headers = sign_payload('{"amount": 100}', secret)

        valid = verify_signature(
            '{"amount": 999}', secret,
            headers["X-Webhook-Timestamp"],
            headers["X-Webhook-Signature"],
        )
        assert valid is False


# ── Webhook API Tests ──

class TestWebhookAPI:
    def test_register_endpoint(self):
        resp = client.post("/v1/webhook", json={
            "user_id": "usr_test",
            "event_type": "invoice.paid",
            "endpoint": "https://example.com/hooks",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["user_id"] == "usr_test"
        assert data["event_type"] == "invoice.paid"
        assert data["endpoint_url"] == "https://example.com/hooks"
        assert data["status"] == "active"
        assert data["secret"].startswith("whsec_")

    def test_list_endpoints(self):
        # Register two
        client.post("/v1/webhook", json={
            "user_id": "usr_a", "event_type": "order.placed",
            "endpoint": "https://a.com/hook",
        })
        client.post("/v1/webhook", json={
            "user_id": "usr_b", "event_type": "order.shipped",
            "endpoint": "https://b.com/hook",
        })

        resp = client.get("/v1/webhook")
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_list_endpoints_filter_by_user(self):
        client.post("/v1/webhook", json={
            "user_id": "usr_filter", "event_type": "user.signup",
            "endpoint": "https://filter.com/hook",
        })
        resp = client.get("/v1/webhook", params={"user_id": "usr_filter"})
        assert resp.status_code == 200
        for ep in resp.json():
            assert ep["user_id"] == "usr_filter"

    def test_get_endpoint(self):
        resp = client.post("/v1/webhook", json={
            "user_id": "usr_get", "event_type": "payment.success",
            "endpoint": "https://get.com/hook",
        })
        ep_id = resp.json()["id"]

        resp = client.get(f"/v1/webhook/{ep_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == ep_id

    def test_get_endpoint_not_found(self):
        resp = client.get("/v1/webhook/ep_nonexistent")
        assert resp.status_code == 404

    def test_update_endpoint(self):
        resp = client.post("/v1/webhook", json={
            "user_id": "usr_upd", "event_type": "user.updated",
            "endpoint": "https://old.com/hook",
        })
        ep_id = resp.json()["id"]

        resp = client.put(f"/v1/webhook/{ep_id}", json={
            "endpoint": "https://new.com/hook",
        })
        assert resp.status_code == 200
        assert resp.json()["endpoint_url"] == "https://new.com/hook"

    def test_deactivate_endpoint(self):
        resp = client.post("/v1/webhook", json={
            "user_id": "usr_deact", "event_type": "user.deleted",
            "endpoint": "https://deact.com/hook",
        })
        ep_id = resp.json()["id"]

        resp = client.put(f"/v1/webhook/{ep_id}", json={"status": "inactive"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "inactive"

    def test_delete_endpoint(self):
        resp = client.post("/v1/webhook", json={
            "user_id": "usr_del", "event_type": "subscription.renewed",
            "endpoint": "https://del.com/hook",
        })
        ep_id = resp.json()["id"]

        resp = client.delete(f"/v1/webhook/{ep_id}")
        assert resp.status_code == 200

        resp = client.get(f"/v1/webhook/{ep_id}")
        assert resp.status_code == 404

    def test_delete_not_found(self):
        resp = client.delete("/v1/webhook/ep_nope")
        assert resp.status_code == 404


# ── Delivery API Tests ──

class TestDeliveryAPI:
    def test_stats_empty(self):
        resp = client.get("/v1/deliveries/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_attempts"] == 0

    def test_dlq_empty(self):
        resp = client.get("/v1/deliveries/dlq")
        assert resp.status_code == 200
        assert resp.json() == []
