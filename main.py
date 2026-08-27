import argparse
import sys
from controller import run_task


def main():
    parser = argparse.ArgumentParser(
        description="Personal Search Assistant Agent - Step 1 Extractor"
    )
    parser.add_argument(
        "--url",
        type=str,
        required=True,
        help="Target URL to crawl (e.g. https://example.com/events)",
    )
    parser.add_argument(
        "--goal",
        type=str,
        required=True,
        help="Task goal / instructions (e.g. 'find meetups about AI agents')",
    )

    args = parser.parse_args()

    try:
        result = run_task(url=args.url, goal=args.goal)
        print("=== EXTRACTION RESULT ===")
        print(result)
    except Exception as e:
        print(f"Task Failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
