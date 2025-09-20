#!/usr/bin/env python
"""
Simple script to check the status of the submitted batch without Django dependencies.
"""

import os
import sys
from pathlib import Path
from openai import OpenAI

def check_batch_status():
    """Check the status of the submitted batch."""

    output_dir = Path('batch_waste_analysis')
    batch_id_file = output_dir / 'current_batch_id.txt'

    if not batch_id_file.exists():
        print("❌ No batch ID file found. No batch appears to be running.")
        return

    with open(batch_id_file, 'r') as f:
        batch_id = f.read().strip()

    print(f"📊 Checking batch: {batch_id}")
    print("=" * 50)

    # You'll need to set your OpenAI API key
    # For now, let's just show the batch ID and instructions
    print(f"Batch ID: {batch_id}")
    print(f"")
    print("To check status manually:")
    print("1. Visit OpenAI Platform Dashboard")
    print("2. Go to Batch API section")
    print(f"3. Look for batch ID: {batch_id}")
    print("")
    print("Expected statuses:")
    print("- validating: OpenAI is validating the batch")
    print("- in_progress: Processing your requests")
    print("- finalizing: Almost complete")
    print("- completed: Ready for download")
    print("- failed: Check for errors")

    # Try to check with API if key is available
    try:
        # Try to get API key from environment or settings
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("\n⚠️  Set OPENAI_API_KEY environment variable to check status automatically")
            return

        client = OpenAI(api_key=api_key)
        batch = client.batches.retrieve(batch_id)

        print(f"\n📈 Current Status: {batch.status}")
        print(f"   Created: {batch.created_at}")
        print(f"   Completion window: {batch.completion_window}")
        print(f"   Total requests: {batch.request_counts.total if hasattr(batch.request_counts, 'total') else 'N/A'}")

        if batch.status == 'completed':
            print("🎉 Batch completed! Ready to process results.")
        elif batch.status == 'failed':
            print("❌ Batch failed. Check errors.")
        elif batch.status == 'in_progress':
            print("⏳ Processing in progress...")
        else:
            print(f"📊 Status: {batch.status}")

    except Exception as e:
        print(f"\n❌ Could not check status automatically: {e}")
        print("Check manually in OpenAI dashboard")

if __name__ == '__main__':
    check_batch_status()