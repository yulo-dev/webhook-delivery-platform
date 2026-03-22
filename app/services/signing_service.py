import hashlib
import hmac
import secrets
import time


def generate_secret() -> str:
    """Generate a webhook signing secret."""
    return "whsec_" + secrets.token_hex(16)


def sign_payload(payload: str, secret: str, timestamp: int | None = None) -> dict:
    """
    Sign a webhook payload using HMAC-SHA256.
    Returns headers to include in the webhook delivery.
    """
    ts = timestamp or int(time.time())
    signed_content = f"{ts}.{payload}"
    signature = hmac.new(
        secret.encode("utf-8"),
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return {
        "X-Webhook-Timestamp": str(ts),
        "X-Webhook-Signature": f"sha256={signature}",
    }


def verify_signature(payload: str, secret: str, timestamp: str, signature: str) -> bool:
    """
    Verify that a webhook payload signature is valid.
    Used by the receiver to authenticate the sender.
    """
    signed_content = f"{timestamp}.{payload}"
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
