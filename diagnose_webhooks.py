#!/usr/bin/env python3
"""
Diagnostic script for troubleshooting webhook issues.
Run this to check your configuration and connectivity.
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print an info message."""
    print(f"  {text}")


def check_environment_file() -> bool:
    """Check if .env file exists."""
    print_header("1. Checking Environment Configuration")

    env_path = Path(".env")
    if not env_path.exists():
        print_error(".env file not found")
        print_info("Create a .env file from .env.example")
        return False

    print_success(".env file exists")
    return True


def check_environment_variables() -> dict:
    """Check required environment variables."""
    print_header("2. Checking Environment Variables")

    load_dotenv()

    required_vars = {
        "GITHUB_APP_ID": "GitHub App ID",
        "GITHUB_WEBHOOK_SECRET": "GitHub Webhook Secret",
        "GITHUB_PRIVATE_KEY_PATH": "GitHub Private Key Path",
        "GEMINI_API_KEY": "Gemini API Key",
    }

    optional_vars = {
        "HOST": "Server Host",
        "PORT": "Server Port",
        "LOG_LEVEL": "Log Level",
    }

    results = {}
    all_good = True

    # Check required variables
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value and value.strip():
            print_success(f"{description} ({var}) is set")
            # Mask sensitive values
            if "SECRET" in var or "KEY" in var:
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            print_info(f"Value: {display_value}")
            results[var] = value
        else:
            print_error(f"{description} ({var}) is NOT set")
            all_good = False
            results[var] = None

    # Check optional variables
    print("\n" + Colors.BOLD + "Optional Variables:" + Colors.END)
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print_info(f"{description} ({var}): {value}")
            results[var] = value
        else:
            print_info(f"{description} ({var}): Not set (using default)")
            results[var] = None

    return results if all_good else {}


def check_private_key(key_path: str) -> bool:
    """Check if private key file exists and is valid."""
    print_header("3. Checking GitHub Private Key")

    if not key_path:
        print_error("Private key path not specified in .env")
        return False

    key_file = Path(key_path)
    if not key_file.exists():
        print_error(f"Private key file not found: {key_path}")
        print_info("Download your private key from GitHub App settings")
        return False

    print_success(f"Private key file exists: {key_path}")

    # Check if it's readable
    try:
        with open(key_file, 'r') as f:
            content = f.read()
            if "BEGIN RSA PRIVATE KEY" in content or "BEGIN PRIVATE KEY" in content:
                print_success("Private key file format is valid")
                return True
            else:
                print_error("Private key file doesn't appear to be a valid PEM file")
                return False
    except Exception as e:
        print_error(f"Cannot read private key file: {e}")
        return False


def check_application_running() -> dict:
    """Check if the application is running."""
    print_header("4. Checking Application Status")

    host = os.getenv("HOST", "localhost")
    port = os.getenv("PORT", "8000")

    # Try localhost first
    base_url = f"http://localhost:{port}"

    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"Application is running at {base_url}")
            data = response.json()
            print_info(f"Status: {data.get('status')}")
            print_info(f"Version: {data.get('version')}")
            print_info(f"GitHub configured: {data.get('github_app_configured')}")
            print_info(f"Gemini configured: {data.get('gemini_configured')}")
            return data
        else:
            print_error(f"Application responded with status {response.status_code}")
            return {}
    except requests.exceptions.ConnectionError:
        print_error(f"Cannot connect to application at {base_url}")
        print_info("Make sure the application is running:")
        print_info("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        return {}
    except Exception as e:
        print_error(f"Error checking application: {e}")
        return {}


def check_webhook_endpoint() -> bool:
    """Check if webhook endpoint is accessible."""
    print_header("5. Checking Webhook Endpoint")

    port = os.getenv("PORT", "8000")
    base_url = f"http://localhost:{port}"

    try:
        response = requests.get(f"{base_url}/webhooks/github", timeout=5)
        if response.status_code == 200:
            print_success("Webhook endpoint is accessible")
            data = response.json()
            print_info(f"Endpoint: {data.get('endpoint')}")
            print_info(f"Method: {data.get('method')}")
            print_info(f"Description: {data.get('description')}")
            return True
        else:
            print_error(f"Webhook endpoint responded with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot access webhook endpoint: {e}")
        return False


def check_ngrok() -> str:
    """Check if ngrok is running."""
    print_header("6. Checking ngrok Tunnel")

    try:
        # Try to get ngrok API (default port 4040)
        response = requests.get("http://localhost:4040/api/tunnels", timeout=2)
        if response.status_code == 200:
            data = response.json()
            tunnels = data.get("tunnels", [])

            if tunnels:
                print_success("ngrok is running")
                for tunnel in tunnels:
                    public_url = tunnel.get("public_url")
                    if public_url.startswith("https"):
                        print_info(f"Public URL: {public_url}")
                        return public_url
                return tunnels[0].get("public_url", "")
            else:
                print_warning("ngrok is running but no tunnels found")
                return ""
        else:
            print_warning("ngrok API responded with unexpected status")
            return ""
    except requests.exceptions.ConnectionError:
        print_error("ngrok is NOT running")
        print_info("Start ngrok with: ngrok http 8000")
        return ""
    except Exception as e:
        print_error(f"Error checking ngrok: {e}")
        return ""


def check_ngrok_webhook(ngrok_url: str) -> bool:
    """Check if webhook endpoint is accessible via ngrok."""
    print_header("7. Checking ngrok Webhook Access")

    if not ngrok_url:
        print_error("No ngrok URL available to test")
        return False

    webhook_url = f"{ngrok_url}/webhooks/github"

    try:
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            print_success(f"Webhook is accessible via ngrok")
            print_info(f"URL: {webhook_url}")
            print_info("Use this URL in GitHub App webhook settings")
            return True
        else:
            print_error(f"Webhook responded with status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Cannot access webhook via ngrok: {e}")
        return False


def print_github_instructions(ngrok_url: str, webhook_secret: str) -> None:
    """Print instructions for GitHub configuration."""
    print_header("8. GitHub Configuration Instructions")

    if not ngrok_url:
        print_warning("ngrok URL not available")
        print_info("Start ngrok first: ngrok http 8000")
        return

    webhook_url = f"{ngrok_url}/webhooks/github"

    print(f"{Colors.BOLD}Configure your GitHub App webhook:{Colors.END}")
    print()
    print("1. Go to: https://github.com/settings/apps")
    print("2. Click on your app")
    print("3. Scroll to 'Webhook' section")
    print()
    print(f"   {Colors.BOLD}Webhook URL:{Colors.END} {Colors.GREEN}{webhook_url}{Colors.END}")
    print(f"   {Colors.BOLD}Webhook Secret:{Colors.END} {webhook_secret[:16]}... (from your .env)")
    print(f"   {Colors.BOLD}Content type:{Colors.END} application/json")
    print(f"   {Colors.BOLD}SSL verification:{Colors.END} Enable SSL verification")
    print(f"   {Colors.BOLD}Active:{Colors.END} ✓ Checked")
    print()
    print("4. Subscribe to these events:")
    print("   - Pull requests")
    print("   - Issue comments")
    print("   - Pull request review comments")
    print()
    print("5. Save changes")
    print()
    print(f"{Colors.BOLD}Then install the app on your repository:{Colors.END}")
    print("1. Go to: https://github.com/settings/installations")
    print("2. Click on your app")
    print("3. Select repository access")
    print("4. Save")


def check_metrics() -> None:
    """Check application metrics."""
    print_header("9. Checking Application Metrics")

    port = os.getenv("PORT", "8000")
    base_url = f"http://localhost:{port}"

    try:
        response = requests.get(f"{base_url}/webhooks/metrics", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print_success("Metrics endpoint is accessible")
            print()
            print(f"  Total webhooks received:       {data.get('total_webhooks', 0)}")
            print(f"  Pull request events:           {data.get('pull_request_events', 0)}")
            print(f"  Issue comment events:          {data.get('issue_comment_events', 0)}")
            print(f"  Review comment events:         {data.get('review_comment_events', 0)}")
            print(f"  Commands processed:            {data.get('commands_processed', 0)}")
            print(f"  Reviews triggered:             {data.get('reviews_triggered', 0)}")
            print()

            if data.get('total_webhooks', 0) == 0:
                print_warning("No webhooks received yet")
                print_info("Try posting a comment on a PR to test")
            else:
                print_success(f"{data.get('total_webhooks')} webhooks received")
        else:
            print_error(f"Metrics endpoint responded with status {response.status_code}")
    except Exception as e:
        print_error(f"Cannot access metrics endpoint: {e}")


def print_summary(checks: dict) -> None:
    """Print summary of checks."""
    print_header("Summary")

    passed = sum(1 for v in checks.values() if v)
    total = len(checks)

    print(f"Checks passed: {passed}/{total}")
    print()

    if passed == total:
        print_success("All checks passed! Your setup looks good.")
        print()
        print(f"{Colors.BOLD}Next steps:{Colors.END}")
        print("1. Post a comment on a PR: /help")
        print("2. Check the FastAPI terminal for logs")
        print("3. Check the GitHub PR for bot response")
    else:
        print_error("Some checks failed. Review the output above.")
        print()
        print(f"{Colors.BOLD}Common fixes:{Colors.END}")

        if not checks.get("env_file"):
            print("• Create .env file from .env.example")
        if not checks.get("env_vars"):
            print("• Fill in all required environment variables in .env")
        if not checks.get("private_key"):
            print("• Download and place GitHub App private key")
        if not checks.get("app_running"):
            print("• Start the application: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        if not checks.get("ngrok"):
            print("• Start ngrok: ngrok http 8000")
        if not checks.get("ngrok_webhook"):
            print("• Update GitHub webhook URL with current ngrok URL")


def main() -> None:
    """Run all diagnostic checks."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║            RepoAuditor AI - Webhook Diagnostics Tool              ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    checks = {}

    # Run checks
    checks["env_file"] = check_environment_file()

    env_vars = check_environment_variables()
    checks["env_vars"] = bool(env_vars)

    if env_vars.get("GITHUB_PRIVATE_KEY_PATH"):
        checks["private_key"] = check_private_key(env_vars["GITHUB_PRIVATE_KEY_PATH"])
    else:
        checks["private_key"] = False

    app_data = check_application_running()
    checks["app_running"] = bool(app_data)

    if checks["app_running"]:
        checks["webhook_endpoint"] = check_webhook_endpoint()
    else:
        checks["webhook_endpoint"] = False

    ngrok_url = check_ngrok()
    checks["ngrok"] = bool(ngrok_url)

    if ngrok_url and checks["app_running"]:
        checks["ngrok_webhook"] = check_ngrok_webhook(ngrok_url)
    else:
        checks["ngrok_webhook"] = False

    if checks["app_running"]:
        check_metrics()

    if ngrok_url and env_vars.get("GITHUB_WEBHOOK_SECRET"):
        print_github_instructions(ngrok_url, env_vars["GITHUB_WEBHOOK_SECRET"])

    # Print summary
    print_summary(checks)

    # Exit code
    if all(checks.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Diagnostic cancelled by user{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.END}")
        sys.exit(1)
