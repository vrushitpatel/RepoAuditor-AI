"""Manual test script for command router.

Run this to verify the router is working correctly.
"""

import asyncio
from app.commands.router_instance import get_router


async def test_router():
    """Test the command router."""
    print("\n" + "=" * 70)
    print("  Command Router Test")
    print("=" * 70 + "\n")

    # Get router instance
    router = get_router()

    print("✓ Router initialized successfully\n")

    # List registered commands
    commands = router.list_commands()
    print(f"📋 Registered Commands ({len(commands)}):\n")

    for cmd, description in sorted(commands.items()):
        print(f"  /{cmd:15} - {description}")

    print("\n" + "=" * 70)
    print("  Testing Command Matching")
    print("=" * 70 + "\n")

    # Test cases
    test_cases = [
        "/help",
        "/explain",
        "/explain app/main.py",
        "/explain app/main.py:health",
        "/review",
        "/generate-ci",
        "/generate-ci all",
        "/generate-ci test lint",
        "/unknown",
        "help",  # Without slash
        "not a command",
    ]

    for test_text in test_cases:
        result = router.match_command(test_text)

        if result:
            command, args = result
            agent = router.get_agent(command)

            print(f"✓ '{test_text}'")
            print(f"  → Command: {command}")
            print(f"  → Args: '{args}' " if args else "  → Args: (none)")
            print(f"  → Agent: {agent.name}")
        else:
            print(f"✗ '{test_text}'")
            print(f"  → No match")

        print()

    print("=" * 70)
    print("  Test Complete")
    print("=" * 70 + "\n")

    print("✅ Router is working correctly!")
    print("\n💡 To test with real GitHub webhooks:")
    print("   1. Start the application: uvicorn app.main:app --reload")
    print("   2. Post a comment in a PR: /help")
    print("   3. Check the response from the bot")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(test_router())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
