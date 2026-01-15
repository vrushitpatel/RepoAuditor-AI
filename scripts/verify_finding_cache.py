"""Verify finding cache contents.

This script helps debug finding cache issues by showing:
- All cached PR findings
- Finding IDs and severities
- Cache file locations
- Expiration times

Run with: python scripts/verify_finding_cache.py
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def print_success(message: str):
    """Print success message."""
    print(f"[OK] {message}")


def print_error(message: str):
    """Print error message."""
    print(f"[ERROR] {message}")


def print_info(message: str):
    """Print info message."""
    print(f"[INFO] {message}")


def main():
    """Verify finding cache."""
    print_section("Finding Cache Verification")

    # Find cache directory
    cache_dir = project_root / "data" / "finding_cache"

    if not cache_dir.exists():
        print_error("Cache directory does not exist")
        print_info(f"Expected location: {cache_dir}")
        print_info("No findings have been cached yet.")
        return

    print_success(f"Cache directory: {cache_dir}")
    print()

    # List all cache files
    cache_files = list(cache_dir.glob("*.json"))

    if not cache_files:
        print_error("No cache files found")
        print_info("Run /review on a PR first to generate findings.")
        return

    print_success(f"Found {len(cache_files)} cache file(s)")
    print()

    # Process each cache file
    for cache_file in cache_files:
        print_section(f"Cache File: {cache_file.name}")

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Basic info
            repo_name = data.get("repo_name", "unknown")
            pr_number = data.get("pr_number", 0)
            created_at = data.get("created_at", "unknown")
            expires_at = data.get("expires_at", "unknown")
            findings = data.get("findings", [])

            print(f"Repository: {repo_name}")
            print(f"PR Number: #{pr_number}")
            print(f"Total Findings: {len(findings)}")
            print(f"Created: {created_at}")
            print(f"Expires: {expires_at}")
            print()

            # Check expiration
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                now = datetime.now(timezone.utc)

                if now > expires_dt:
                    print_error("Cache has EXPIRED")
                else:
                    time_left = expires_dt - now
                    hours_left = time_left.total_seconds() / 3600
                    print_success(f"Cache is VALID (expires in {hours_left:.1f} hours)")
            except Exception:
                print_info("Could not check expiration time")

            print()

            # Check if repo_name/pr_number look correct
            if repo_name == "unknown" or pr_number == 0:
                print_error("WARNING: Cache was saved with default values!")
                print_info("This means the cache won't be retrievable by /jira command")
                print_info("The bug has been fixed in nodes_legacy.py")
                print_info("Next /review will cache with correct repo/PR info")
                print()

            # Show findings summary
            if findings:
                print("Findings Summary:")
                print()

                # Count by severity
                severity_counts = {}
                for cached_finding in findings:
                    finding_data = cached_finding.get("finding_data", {})
                    severity = finding_data.get("severity", "UNKNOWN")
                    severity_counts[severity] = severity_counts.get(severity, 0) + 1

                # Show counts
                for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]:
                    count = severity_counts.get(severity, 0)
                    if count > 0:
                        prefix = {
                            "CRITICAL": "[CRIT]",
                            "HIGH": "[HIGH]",
                            "MEDIUM": "[MED ]",
                            "LOW": "[LOW ]",
                            "INFO": "[INFO]",
                        }.get(severity, "[????]")
                        print(f"  {prefix} {count} {severity}")

                print()

                # Show individual findings
                print("Individual Findings:")
                print()

                for cached_finding in findings:
                    finding_id = cached_finding.get("finding_id", "?")
                    finding_data = cached_finding.get("finding_data", {})

                    severity = finding_data.get("severity", "UNKNOWN")
                    finding_type = finding_data.get("type", "Unknown")
                    title = finding_data.get("title", "No title")

                    location = finding_data.get("location", {})
                    if location:
                        file_path = location.get("file_path", "unknown")
                        line_start = location.get("line_start", "?")
                        location_str = f"{file_path}:{line_start}"
                    else:
                        location_str = "No location"

                    print(f"  #{finding_id}: [{severity}] {title}")
                    print(f"         Type: {finding_type}")
                    print(f"         Location: {location_str}")
                    print()

                # Test get_latest_critical_finding logic
                print_section("Testing CRITICAL/HIGH Retrieval")

                critical_or_high_found = False
                for idx, cached_finding in enumerate(findings, start=1):
                    finding_data = cached_finding.get("finding_data", {})
                    severity = finding_data.get("severity", "")

                    if severity in ["CRITICAL", "HIGH"]:
                        print_success(f"Found CRITICAL/HIGH finding at index {idx}")
                        print(f"  Severity: {severity}")
                        print(f"  Title: {finding_data.get('title', 'No title')}")
                        critical_or_high_found = True
                        break

                if not critical_or_high_found:
                    print_info("No CRITICAL or HIGH severity findings found")
                    print_info("The /jira command will report no critical findings")

        except Exception as e:
            print_error(f"Failed to read cache file: {e}")

    # Final summary
    print_section("Summary")

    print("Next steps:")
    print()
    print("1. If cache has wrong repo/PR (unknown/0):")
    print("   - The bug is now fixed in nodes_legacy.py")
    print("   - Run a new /review to create correct cache")
    print()
    print("2. To test /jira command:")
    print("   - Make sure a cache file exists with correct repo/PR")
    print("   - Make sure at least one CRITICAL or HIGH finding exists")
    print("   - Run: /jira")
    print()
    print("3. To clear old cache files:")
    print("   - Delete: data/finding_cache/*.json")
    print("   - Run /review again to regenerate")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] Verification interrupted by user")
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        import traceback
        traceback.print_exc()
