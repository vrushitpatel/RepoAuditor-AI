"""Check server status and webhook connectivity.

This script helps diagnose why the FastAPI server isn't responding.

Run with: python scripts/check_server_status.py
"""

import sys
import socket
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def check_port(host: str, port: int) -> bool:
    """Check if a port is open."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def main():
    """Check server status."""
    print_section("FastAPI Server Status Check")

    # Check .env configuration
    print("Step 1: Checking Configuration")
    print()

    try:
        from app.config import get_settings

        settings = get_settings()

        print(f"[INFO] Host: {settings.server.host}")
        print(f"[INFO] Port: {settings.server.port}")
        print(f"[INFO] Debug Mode: {settings.server.debug}")
        print(f"[INFO] Log Level: {settings.server.log_level}")
        print()

        # Check if port is in use
        print("Step 2: Checking Port Availability")
        print()

        port_open = check_port(settings.server.host, settings.server.port)

        if port_open:
            print(f"[OK] Port {settings.server.port} is OPEN (server might be running)")
            print()
            print("Try accessing:")
            print(f"  http://localhost:{settings.server.port}/")
            print(f"  http://localhost:{settings.server.port}/health")
        else:
            print(f"[ERROR] Port {settings.server.port} is CLOSED (server NOT running)")
            print()
            print("The server is not running!")
            print()
            print("To start the server:")
            print("  python -m uvicorn app.main:app --reload")

        print()

        # Check GitHub configuration
        print("Step 3: Checking GitHub Configuration")
        print()

        if settings.github.app_id:
            print(f"[OK] GitHub App ID: {settings.github.app_id}")
        else:
            print("[ERROR] GitHub App ID not configured")

        if settings.github.webhook_secret:
            masked = settings.github.webhook_secret[:4] + "****" + settings.github.webhook_secret[-4:]
            print(f"[OK] Webhook Secret: {masked}")
        else:
            print("[ERROR] Webhook Secret not configured")

        if settings.github.private_key_path.exists():
            print(f"[OK] Private Key: {settings.github.private_key_path}")
        else:
            print(f"[ERROR] Private Key not found: {settings.github.private_key_path}")

        print()

        # Check Gemini configuration
        print("Step 4: Checking Gemini Configuration")
        print()

        if settings.gemini.api_key:
            masked = settings.gemini.api_key[:4] + "****" + settings.gemini.api_key[-4:]
            print(f"[OK] Gemini API Key: {masked}")
        else:
            print("[ERROR] Gemini API Key not configured")

        print()

        # Instructions
        print_section("Next Steps")

        if not port_open:
            print("SERVER NOT RUNNING!")
            print()
            print("To start the server:")
            print()
            print("  1. Open a terminal/command prompt")
            print("  2. Navigate to project directory:")
            print(f"     cd \"{project_root}\"")
            print()
            print("  3. Start the server:")
            print("     python -m uvicorn app.main:app --reload")
            print()
            print("  4. You should see:")
            print("     INFO:     Uvicorn running on http://0.0.0.0:8000")
            print("     INFO:     Application startup complete.")
            print()
            print("  5. Keep this terminal open!")
        else:
            print("Server appears to be running.")
            print()
            print("For local development with GitHub webhooks:")
            print()
            print("  1. Install ngrok: https://ngrok.com/download")
            print()
            print("  2. Start ngrok in a NEW terminal:")
            print(f"     ngrok http {settings.server.port}")
            print()
            print("  3. Copy the HTTPS forwarding URL (e.g., https://abc123.ngrok.io)")
            print()
            print("  4. Go to GitHub App Settings:")
            print("     https://github.com/settings/apps/YOUR_APP_NAME")
            print()
            print("  5. Update Webhook URL:")
            print("     https://abc123.ngrok.io/webhook")
            print()
            print("  6. Test by commenting on a PR")

        print()
        print_section("Troubleshooting")

        print("If webhooks still don't work:")
        print()
        print("1. Check ngrok is running:")
        print("   - You should see a dashboard at http://127.0.0.1:4040")
        print("   - Shows incoming requests in real-time")
        print()
        print("2. Check GitHub webhook deliveries:")
        print("   - Go to GitHub App Settings > Advanced")
        print("   - Check 'Recent Deliveries'")
        print("   - Should show green checkmarks for successful deliveries")
        print()
        print("3. Check FastAPI logs:")
        print("   - Look at the terminal where you ran uvicorn")
        print("   - Should see webhook events being received")
        print()
        print("4. Verify webhook secret:")
        print("   - GitHub App Settings > Webhook secret")
        print("   - Should match GITHUB_WEBHOOK_SECRET in .env")
        print()
        print("5. Check firewall/antivirus:")
        print("   - May be blocking ngrok or FastAPI")

    except Exception as e:
        print(f"[ERROR] Failed to check configuration: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Check interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Check failed: {e}")
        import traceback
        traceback.print_exc()
