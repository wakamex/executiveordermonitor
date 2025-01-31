#!/usr/bin/env python3

import json
import os
import time
from datetime import datetime, timedelta
from typing import Set

import requests

API_URL = "https://www.federalregister.gov/api/v1/documents.json"
PARAMS = {
    "conditions[correction]": "0",
    "conditions[president]": "donald-trump",
    "conditions[presidential_document_type]": "executive_order",
    "conditions[signing_date][gte]": (datetime.now() - timedelta(days=30)).strftime("%m/%d/%Y"),
    "conditions[signing_date][lte]": datetime.now().strftime("%m/%d/%Y"),
    "conditions[type][]": "PRESDOCU",
    "fields[]": [
        "citation", "document_number", "html_url", "signing_date",
        "title", "executive_order_number"
    ],
    "per_page": "10000",
    "order": "executive_order"
}

CACHE_FILE = "seen_eos.json"
POLL_INTERVALS = [1, 5, 10, 30, 60]  # seconds between API calls with backoff
USER_AGENT = "ExecutiveOrderMonitor/1.0 (https://github.com/wakamex/ExecutiveOrderMonitor)"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds between retries on error

def load_seen_eos() -> Set[str]:
    """Load previously seen EO document numbers from cache file."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_seen_eos(seen_eos: Set[str]) -> None:
    """Save seen EO document numbers to cache file."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(seen_eos), f)

def check_eos() -> bool:
    """Query the Federal Register API and check for new EOs.
    Returns True if the check was successful, False if there was an error."""
    seen_eos = load_seen_eos()
    
    for attempt in range(MAX_RETRIES):
        try:
            headers = {
                "User-Agent": USER_AGENT,
                "Accept": "application/json"
            }
            response = requests.get(API_URL, params=PARAMS, headers=headers, timeout=10)
            
            # Check for rate limit headers if they exist
            remaining = response.headers.get('X-RateLimit-Remaining')
            if remaining and int(remaining) < 10:
                print(f"Warning: Only {remaining} API calls remaining")
                time.sleep(5)  # Back off a bit
            
            response.raise_for_status()
            data = response.json()
            
            for doc in data.get('results', []):
                doc_num = doc.get('document_number')
                if not doc_num or doc_num in seen_eos:
                    continue
                    
                # New EO found
                seen_eos.add(doc_num)
                
                # Print details about the new EO
                print("\nNew Executive Order Found!")
                print(f"Title: {doc.get('title')}")
                print(f"EO Number: {doc.get('executive_order_number')}")
                print(f"Signing Date: {doc.get('signing_date')}")
                print(f"URL: {doc.get('html_url')}")
                print("-" * 80)
            
            save_seen_eos(seen_eos)
            return True
        
        except requests.exceptions.RequestException as e:
            print(f"Error querying API (attempt {attempt+1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)  # Short delay on error before retry
            else:
                print("Failed after maximum retries")
                return False

def main():
    print("Starting EO monitor...")
    print("Checking with backoff intervals: 1s → 5s → 10s → 30s → 60s")
    print("-" * 80)
    
    interval_index = 0
    consecutive_errors = 0
    
    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        interval = POLL_INTERVALS[interval_index]
        print(f"\nChecking for new EOs at {current_time} (interval: {interval}s)")
        
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
    main()
