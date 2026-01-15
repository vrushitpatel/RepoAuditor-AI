"""Test JIRA connection and diagnose issues.

This script helps diagnose JIRA integration problems by testing:
1. Environment variable loading
2. Base URL format
3. Authentication
4. Project access

Run with: python scripts/test_jira_connection.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import get_settings
from app.models.jira_models import JIRAConfig
from app.integrations.jira_client import (
    JIRAClient,
    JIRAError,
    JIRAAuthenticationError,
)


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_success(message: str):
    """Print success message."""
    print(f"✅ {message}")


def print_error(message: str):
    """Print error message."""
    print(f"❌ {message}")


def print_info(message: str):
    """Print info message."""
    print(f"ℹ️  {message}")


def print_warning(message: str):
    """Print warning message."""
    print(f"⚠️  {message}")


async def main():
    """Run JIRA connection diagnostics."""
    print_section("JIRA Integration Diagnostics")

    # Step 1: Check environment variables
    print_section("Step 1: Environment Variables")

    settings = get_settings()

    print("Checking .env file configuration:")
    print()

    # Check base URL
    if settings.jira.base_url:
        print_success(f"JIRA_BASE_URL: {settings.jira.base_url}")

        # Validate format
        if not settings.jira.base_url.startswith(("http://", "https://")):
            print_error("Base URL must start with http:// or https://")
            print_info("Correct format: https://your-company.atlassian.net")
            return

        if "/rest/api" in settings.jira.base_url:
            print_warning("Base URL should NOT include /rest/api/3")
            print_info("Remove /rest/api/3 from your JIRA_BASE_URL")
            print_info(f"Use: {settings.jira.base_url.split('/rest')[0]}")
            return

        if settings.jira.base_url.endswith("/"):
            print_warning("Base URL has trailing slash (will be removed automatically)")
    else:
        print_error("JIRA_BASE_URL is not set")
        print_info("Add to .env: JIRA_BASE_URL=https://your-company.atlassian.net")
        return

    # Check email
    if settings.jira.email:
        print_success(f"JIRA_EMAIL: {settings.jira.email}")
    else:
        print_error("JIRA_EMAIL is not set")
        print_info("Add to .env: JIRA_EMAIL=your.email@company.com")
        return

    # Check API token
    if settings.jira.api_token:
        # Mask the token for security
        masked_token = settings.jira.api_token[:4] + "*" * (len(settings.jira.api_token) - 8) + settings.jira.api_token[-4:]
        print_success(f"JIRA_API_TOKEN: {masked_token}")

        # Check for quotes in token (common mistake)
        if settings.jira.api_token.startswith(("'", '"')) or settings.jira.api_token.endswith(("'", '"')):
            print_error("API token has quotes around it!")
            print_info("Remove quotes from JIRA_API_TOKEN in .env file")
            print_info("Should be: JIRA_API_TOKEN=your_token_here")
            print_info("NOT: JIRA_API_TOKEN='your_token_here'")
            return
    else:
        print_error("JIRA_API_TOKEN is not set")
        print_info("Generate token at: https://id.atlassian.com/manage-profile/security/api-tokens")
        print_info("Add to .env: JIRA_API_TOKEN=your_token_here")
        return

    # Check default project
    if settings.jira.default_project_key:
        print_success(f"JIRA_DEFAULT_PROJECT_KEY: {settings.jira.default_project_key}")
    else:
        print_warning("JIRA_DEFAULT_PROJECT_KEY is not set (optional)")

    print()
    print_info("All environment variables are set correctly!")

    # Step 2: Test authentication
    print_section("Step 2: Authentication Test")

    config = JIRAConfig(
        base_url=settings.jira.base_url,
        email=settings.jira.email,
        api_token=settings.jira.api_token,
    )

    print(f"Testing connection to: {config.base_url}")
    print(f"API endpoint: {config.base_url}/rest/api/3")
    print()

    try:
        async with JIRAClient(config) as jira:
            print("Attempting to authenticate...")
            await jira.validate_config()
            print_success("Authentication successful!")
            print_info("Your credentials are correct.")

            # Step 3: Test project access
            print_section("Step 3: Project Access Test")

            if settings.jira.default_project_key:
                project_key = settings.jira.default_project_key
                print(f"Testing access to project: {project_key}")
                print()

                try:
                    project = await jira.get_project(project_key)
                    print_success(f"Project found: {project.get('name')}")
                    print_info(f"Key: {project.get('key')}")
                    print_info(f"Description: {project.get('description', 'N/A')}")
                    print()

                    # Get issue types
                    issue_types = await jira.get_issue_types(project_key)
                    print_success("Available issue types:")
                    for issue_type in issue_types:
                        print(f"  - {issue_type.get('name')}")

                except JIRAError as e:
                    print_error(f"Cannot access project: {e.message}")
                    if e.status_code == 404:
                        print_info(f"Project '{project_key}' not found or you don't have access")
                        print_info("Check that:")
                        print_info("  1. The project key is correct (usually all uppercase)")
                        print_info("  2. The project exists in your JIRA instance")
                        print_info("  3. Your account has permission to view the project")
                        print()
                        print_info("To see all projects, log in to JIRA web interface:")
                        print_info(f"  {config.base_url}/jira/projects")
            else:
                print_info("No default project configured (JIRA_DEFAULT_PROJECT_KEY)")
                print_info("Skipping project access test")

            # Final summary
            print_section("Summary")
            print_success("JIRA integration is working correctly!")
            print()
            print("✨ You can now use the /jira command to create tickets.")
            print()
            print("Next steps:")
            print("  1. Run /review on a Pull Request")
            print("  2. Use /jira to create tickets from findings")
            print()

    except JIRAAuthenticationError as e:
        print_error(f"Authentication failed: {e.message}")
        print()
        print("Common causes:")
        print("  1. ❌ Invalid API token")
        print("  2. ❌ Incorrect email address")
        print("  3. ❌ Expired API token")
        print("  4. ❌ Quotes around API token in .env file")
        print()
        print("How to fix:")
        print("  1. Generate a new API token:")
        print("     https://id.atlassian.com/manage-profile/security/api-tokens")
        print("  2. Update .env file:")
        print(f"     JIRA_API_TOKEN=your_new_token_here")
        print("  3. Make sure there are NO QUOTES around the token")
        print("  4. Restart the application")

    except JIRAError as e:
        print_error(f"JIRA Error: {e.message}")
        print()

        if e.status_code == 404:
            print("❌ 404 Not Found Error")
            print()
            print("This usually means:")
            print("  1. ❌ The JIRA base URL is incorrect")
            print("  2. ❌ You included /rest/api/3 in the base URL (don't do this)")
            print("  3. ❌ The JIRA instance doesn't exist")
            print()
            print("Your current base URL:")
            print(f"  {settings.jira.base_url}")
            print()
            print("Correct format examples:")
            print("  ✅ https://your-company.atlassian.net")
            print("  ✅ https://jira.your-company.com")
            print()
            print("WRONG format examples:")
            print("  ❌ https://your-company.atlassian.net/rest/api/3")
            print("  ❌ http://your-company.atlassian.net (missing https)")
            print("  ❌ your-company.atlassian.net (missing https://)")
            print()
            print("To fix:")
            print("  1. Update .env file with correct base URL")
            print("  2. Remove /rest/api/3 if present")
            print("  3. Make sure it starts with https://")
            print("  4. Restart the application")

        elif e.status_code == 401:
            print("❌ 401 Unauthorized - Check your credentials")

        elif e.status_code == 403:
            print("❌ 403 Forbidden - Your account doesn't have permission")

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        print()
        print("This might be a network issue or configuration problem.")
        print("Check your .env file and network connection.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
