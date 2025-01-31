#!/usr/bin/env python3
"""Monitor the Federal Register API for new Executive Orders."""

import json
import os
import sys
import time
from datetime import datetime
from typing import Dict

import requests

CACHE_FILE = "seen_eos.json"
BASE_URL = "https://www.federalregister.gov/api/v1"
POLL_INTERVALS = [1, 5, 10, 30, 60]  # seconds between API calls with backoff
USER_AGENT = "executiveordermonitor/1.0.3 (https://github.com/wakamex/executiveordermonitor)"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries on error


def load_seen_eos() -> Dict[str, dict]:
    """Load the set of seen EO document numbers from cache file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_seen_eos(seen_eos: Dict[str, dict]) -> None:
    """Save the set of seen EO document numbers to cache file."""
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_eos, f, indent=2)


def check_eos() -> bool:
    """Query the Federal Register API for new Executive Orders.

    Returns:
        bool: True if successful, False if error occurred
    """
    seen_eos = load_seen_eos()

    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            }
            response = requests.get(
                f"{BASE_URL}/documents",
                params={
                    "conditions[type]": "PRESDOCU",
                    "conditions[presidential_document_type]": "executive_order",
                    "per_page": 20,
                    "order": "newest",
                },
                headers=headers,
                timeout=10,
            )

            # Check for rate limit headers if they exist
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 10:
                print(f"Warning: Only {remaining} API calls remaining")
                time.sleep(5)  # Back off a bit

            response.raise_for_status()
            data = response.json()

            found_new = False
            for result in data.get('results', []):
                doc_num = result.get('document_number')
                if not doc_num or doc_num in seen_eos:
                    continue

                # Get full document details
                doc_response = requests.get(
                    f"{BASE_URL}/documents/{doc_num}",
                    headers=headers,
                    timeout=10,
                )
                doc_response.raise_for_status()
                doc = doc_response.json()
                
                # Store all relevant fields
                eo_data = {
                    "title": doc.get("title"),
                    "executive_order_number": doc.get("executive_order_number"),
                    "document_number": doc_num,
                    "signing_date": doc.get("signing_date"),
                    "publication_date": doc.get("publication_date"),
                    "html_url": doc.get("html_url"),
                    "pdf_url": doc.get("pdf_url"),
                    "raw_text_url": doc.get("raw_text_url"),
                    "body_html_url": doc.get("body_html_url"),
                }

                # Display to user
                print("\nNew Executive Order found!")
                print(f"Title: {eo_data['title']}")
                print(f"EO Number: {eo_data['executive_order_number']}")
                print(f"Document Number: {eo_data['document_number']}")
                print(f"Signing Date: {eo_data['signing_date']}")
                print(f"Publication Date: {eo_data['publication_date']}")
                print("\nURLs:")
                print(f"Web Page: {eo_data['html_url']}")
                print(f"PDF: {eo_data['pdf_url']}")
                print(f"Plain Text: {eo_data['raw_text_url']}")
                print(f"Full HTML: {eo_data['body_html_url']}")
                print("-" * 80)

                seen_eos[doc_num] = eo_data
                found_new = True

            if found_new:
                save_seen_eos(seen_eos)
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error querying API (attempt {attempt+1}/{MAX_RETRIES}): {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)  # Short delay on error before retry
            else:
                print("Failed after maximum retries")
                return False


def main():
    """Run the main monitoring loop."""
    print("Starting EO monitor...")
    print("Checking with backoff intervals: 1s → 5s → 10s → 30s → 60s")
    print("-" * 80)

    interval_index = 0
    consecutive_errors = 0

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        interval = POLL_INTERVALS[interval_index]
        print(f"\rChecking for new EOs at {current_time} (interval: {interval}s)", end="", flush=True)

        if check_eos():
            # Success - decrease interval if possible
            if consecutive_errors > 0:
                consecutive_errors = 0
                if interval_index > 0:
                    interval_index -= 1
        else:
            # Error - increase interval
            consecutive_errors += 1
            if interval_index < len(POLL_INTERVALS) - 1:
                interval_index += 1

        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        sys.exit(0)
