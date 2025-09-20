#!/usr/bin/env python
"""
Monitor the status of waste analysis batch processing.
"""

import os
import sys
import time
from pathlib import Path

import django
from openai import OpenAI

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import AdminSettings
from batch_generate_waste_analysis import WasteAnalysisBatchGenerator

def main():
    """Monitor batch status and process results when complete."""

    output_dir = Path('batch_waste_analysis')
    batch_id_file = output_dir / 'current_batch_id.txt'

    if not batch_id_file.exists():
        print("❌ No batch ID file found. Run batch_generate_waste_analysis.py first.")
        return

    with open(batch_id_file, 'r') as f:
        batch_id = f.read().strip()

    print(f"📊 Monitoring batch: {batch_id}")
    print("=" * 50)

    # Setup generator to use its methods
    generator = WasteAnalysisBatchGenerator()
    generator.setup()

    # Poll for completion
    completed_batch = generator.poll_batch_status(batch_id, interval=30)

    # Process results if completed
    if completed_batch.status == 'completed':
        print("\n📥 Processing results...")
        generator.process_results(completed_batch)

        # Clean up batch ID file
        batch_id_file.unlink()
        print("\n✅ Monitoring complete!")
    else:
        print(f"\n⚠️ Batch ended with status: {completed_batch.status}")

if __name__ == '__main__':
    main()