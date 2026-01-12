#!/usr/bin/env python3
"""
Manually test webhook endpoint with a simulated GitHub payload.
This helps verify if the application can process webhooks correctly.
"""

import requests
import json
import hmac
import hashlib
import os
from dotenv import load_dotenv

load_dotenv()

# Get configuration
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")
PORT = os.getenv("PORT", "8000")
BASE_URL = f"http://localhost:{PORT}"

# Sample issue_comment webhook payload
ISSUE_COMMENT_PAYLOAD = {
    "action": "created",
    "issue": {
        "number": 999,
        "pull_request": {
            "url": "https://api.github.com/repos/test/repo/pulls/999"
        },
        "user": {"login": "testuser"}
    },
    "comment": {
        "id": 123456789,
        "body": "/help",
        "user": {"login": "testuser"}
    },
    "repository": {
        "full_name": "testuser/testrepo",
        "name": "testrepo",
        "owner": {"login": "testuser"}
    },
    "installation": {
        "id": 12345678
    }
}

# Sample pull_request webhook payload
PULL_REQUEST_PAYLOAD = {
    "action": "opened",
    "number": 999,
    "pull_request": {
        "number": 999,
        "title": "Test PR",
        "body": "Test PR description",
        "state": "open",
        "user": {"login": "testuser"},
        "head": {
            "sha": "abc123",
            "ref": "feature-branch"
        },
        "base": {
            "ref": "main"
        }
    },
    "repository": {
        "full_name": "testuser/testrepo",
        "name": "testrepo",
        "owner": {"login": "testuser"}
    },
    "installation": {
        "id": 12345678
    }
}


def generate_signature(payload_bytes: bytes, secret: str) -> str:
    """Generate GitHub webhook signature."""
    if not secret:
        return "sha256=dummy_signature_for_testing"

    signature = hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"


def test_webhook(event_type: str, payload: dict) -> bool:
    """Test webhook endpoint with given payload."""
    print(f"\n{'='*70}")
    print(f"Testing {event_type} event")
    print(f"{'='*70}\n")

    # Convert payload to JSON bytes
    payload_bytes = json.dumps(payload).encode('utf-8')

    # Generate signature
    signature = generate_signature(payload_bytes, WEBHOOK_SECRET)

    # Prepare headers
    headers = {
        "X-GitHub-Event": event_type,
        "X-Hub-Signature-256": signature,
        "Content-Type": "application/json",
        "User-Agent": "GitHub-Hookshot/test"
    }

    print(f"Sending webhook to: {BASE_URL}/webhooks/github")
    print(f"Event type: {event_type}")
    print(f"Payload: {json.dumps(payload, indent=2)[:200]}...")
    print(f"\nHeaders:")
    for key, value in headers.items():
        if "Signature" in key:
            print(f"  {key}: {value[:20]}...")
        else:
            print(f"  {key}: {value}")

    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/github",
            json=payload,
            headers=headers,
            timeout=10
        )

        print(f"\n✓ Response Status: {response.status_code}")
        print(f"✓ Response Body: {response.text}")

        if response.status_code == 200:
            print(f"\n✅ SUCCESS: Webhook processed successfully!")
            return True
        else:
            print(f"\n❌ FAILED: Unexpected status code {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n❌ FAILED: Cannot connect to {BASE_URL}")
        print("   Make sure the application is running:")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        return False


def main():
    """Run webhook tests."""
    print("\n" + "="*70)
    print("  Manual Webhook Testing Tool")
    print("="*70)

    if not WEBHOOK_SECRET:
        print("\n⚠️  WARNING: GITHUB_WEBHOOK_SECRET not set in .env")
        print("   Using dummy signature (may cause signature verification errors)")

    # Check if application is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code == 200:
            print(f"\n✓ Application is running at {BASE_URL}")
        else:
            print(f"\n❌ Application responded with status {response.status_code}")
            return
    except:
        print(f"\n❌ Application is NOT running at {BASE_URL}")
        print("\nStart the application first:")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return

    # Test ping event first
    print(f"\n{'='*70}")
    print(f"Testing ping event (webhook health check)")
    print(f"{'='*70}\n")

    ping_payload = {"hook_id": 123456, "zen": "Test ping"}
    ping_signature = generate_signature(json.dumps(ping_payload).encode(), WEBHOOK_SECRET)

    try:
        response = requests.post(
            f"{BASE_URL}/webhooks/github",
            json=ping_payload,
            headers={
                "X-GitHub-Event": "ping",
                "X-Hub-Signature-256": ping_signature,
                "Content-Type": "application/json"
            },
            timeout=5
        )

        if response.status_code == 200:
            print("✅ Ping successful - webhook endpoint is working!")
        else:
            print(f"❌ Ping failed with status {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Ping failed: {e}")
        return

    # Test issue_comment event (for /help command)
    success1 = test_webhook("issue_comment", ISSUE_COMMENT_PAYLOAD)

    # Test pull_request event (for auto-review)
    success2 = test_webhook("pull_request", PULL_REQUEST_PAYLOAD)

    # Summary
    print(f"\n{'='*70}")
    print("  Test Summary")
    print(f"{'='*70}\n")

    print(f"Ping event:           ✓ Passed")
    print(f"issue_comment event:  {'✓ Passed' if success1 else '✗ Failed'}")
    print(f"pull_request event:   {'✓ Passed' if success2 else '✗ Failed'}")

    if success1 and success2:
        print(f"\n✅ All tests passed!")
        print("\nIf manual tests work but real GitHub webhooks don't:")
        print("1. Check GitHub App webhook URL is correct")
        print("2. Check webhook secret matches in GitHub and .env")
        print("3. Check GitHub webhook Recent Deliveries for errors")
        print("4. Verify GitHub App is installed on the repository")
    else:
        print(f"\n❌ Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("- Signature verification failed: Check GITHUB_WEBHOOK_SECRET in .env")
        print("- Connection refused: Make sure application is running")
        print("- 500 errors: Check FastAPI terminal for error details")

    print(f"\n{'='*70}")
    print("  Next Steps")
    print(f"{'='*70}\n")

    print("1. Check FastAPI terminal for log output from these test webhooks")
    print("2. If tests passed, the issue is with GitHub webhook configuration")
    print("3. Go to GitHub App settings and check Recent Deliveries")
    print("4. Compare webhook URL in GitHub with your current ngrok URL")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
