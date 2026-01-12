#!/usr/bin/env python3
"""
Script to monitor incoming webhook events in real-time.
Run this to see what events are being received.
"""

import requests
import time
import sys

def check_metrics():
    """Check webhook metrics."""
    try:
        response = requests.get("http://localhost:8000/webhooks/metrics", timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error: Status {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to application at http://localhost:8000")
        print("   Make sure the application is running.")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    """Monitor webhook events."""
    print("\n" + "="*70)
    print("  RepoAuditor AI - Webhook Event Monitor")
    print("="*70 + "\n")
    print("Monitoring webhook events... (Press Ctrl+C to stop)\n")

    previous_metrics = None

    try:
        while True:
            metrics = check_metrics()

            if metrics:
                # Show current totals
                print(f"\r[{time.strftime('%H:%M:%S')}] "
                      f"Total: {metrics['total_webhooks']} | "
                      f"PR: {metrics['pull_request_events']} | "
                      f"Comments: {metrics['issue_comment_events']} | "
                      f"Review Comments: {metrics['review_comment_events']} | "
                      f"Commands: {metrics['commands_processed']}",
                      end='', flush=True)

                # Detect new events
                if previous_metrics:
                    if metrics['total_webhooks'] > previous_metrics['total_webhooks']:
                        print()  # New line for new events

                        if metrics['pull_request_events'] > previous_metrics['pull_request_events']:
                            print(f"  ✓ New pull_request event received!")

                        if metrics['issue_comment_events'] > previous_metrics['issue_comment_events']:
                            print(f"  ✓ New issue_comment event received!")

                        if metrics['review_comment_events'] > previous_metrics['review_comment_events']:
                            print(f"  ✓ New review_comment event received!")

                        if metrics['commands_processed'] > previous_metrics['commands_processed']:
                            commands_delta = metrics['commands_processed'] - previous_metrics['commands_processed']
                            print(f"  ✓ {commands_delta} new command(s) processed!")

                previous_metrics = metrics

            time.sleep(2)  # Check every 2 seconds

    except KeyboardInterrupt:
        print("\n\n" + "="*70)
        print("  Monitoring stopped")
        print("="*70)

        if previous_metrics:
            print(f"\nFinal counts:")
            print(f"  Total webhooks:        {previous_metrics['total_webhooks']}")
            print(f"  Pull request events:   {previous_metrics['pull_request_events']}")
            print(f"  Issue comment events:  {previous_metrics['issue_comment_events']}")
            print(f"  Review comments:       {previous_metrics['review_comment_events']}")
            print(f"  Commands processed:    {previous_metrics['commands_processed']}")
            print(f"  Reviews triggered:     {previous_metrics['reviews_triggered']}")

            if previous_metrics['issue_comment_events'] == 0:
                print("\n⚠️  WARNING: No issue_comment events received!")
                print("   This means GitHub is not sending comment events.")
                print("   Check GitHub App settings → Subscribe to events → Issue comment")

        sys.exit(0)

if __name__ == "__main__":
    main()
