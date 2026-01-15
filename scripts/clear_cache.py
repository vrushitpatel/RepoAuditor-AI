"""Clear finding cache.

This script deletes all cached findings so you can start fresh.

Run with: python scripts/clear_cache.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """Clear finding cache."""
    print("=" * 70)
    print("  Clear Finding Cache")
    print("=" * 70)
    print()

    # Find cache directory
    cache_dir = project_root / "data" / "finding_cache"

    if not cache_dir.exists():
        print("[INFO] Cache directory does not exist - nothing to clear")
        return

    # List cache files
    cache_files = list(cache_dir.glob("*.json"))

    if not cache_files:
        print("[INFO] No cache files found - cache is already empty")
        return

    print(f"[INFO] Found {len(cache_files)} cache file(s):")
    for f in cache_files:
        print(f"  - {f.name}")
    print()

    # Confirm deletion
    response = input("Delete all cache files? (yes/no): ").strip().lower()

    if response not in ["yes", "y"]:
        print("[INFO] Operation cancelled")
        return

    # Delete files
    deleted_count = 0
    failed_count = 0

    for cache_file in cache_files:
        try:
            cache_file.unlink()
            print(f"[OK] Deleted: {cache_file.name}")
            deleted_count += 1
        except Exception as e:
            print(f"[ERROR] Failed to delete {cache_file.name}: {e}")
            failed_count += 1

    print()
    print("=" * 70)
    print(f"  Deleted: {deleted_count} file(s)")
    if failed_count > 0:
        print(f"  Failed: {failed_count} file(s)")
    print("=" * 70)
    print()

    if deleted_count > 0:
        print("[OK] Cache cleared successfully!")
        print()
        print("Next steps:")
        print("  1. Restart the application")
        print("  2. Run /review on a PR")
        print("  3. Run /jira to create tickets")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Operation cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Failed to clear cache: {e}")
        import traceback
        traceback.print_exc()
