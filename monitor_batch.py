#!/usr/bin/env python
"""
Monitor and resume batch processing for process details generation.
"""

import os
import sys
import django
from pathlib import Path
from openai import OpenAI

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import AdminSettings
from batch_generate_process_details import ProcessDetailsBatchGenerator

def main():
    # Check for batch ID file
    batch_id_file = Path('batch_process_details/current_batch_id.txt')
    
    if not batch_id_file.exists():
        print("❌ No batch ID file found. Run batch_generate_process_details.py first.")
        return
    
    with open(batch_id_file, 'r') as f:
        batch_id = f.read().strip()
    
    print(f"📊 Monitoring batch: {batch_id}")
    
    # Setup OpenAI client
    api_key = AdminSettings.get_setting('openai_api_key')
    if not api_key:
        print("❌ OpenAI API key not found in admin settings")
        return
    
    client = OpenAI(api_key=api_key)
    
    # Get batch status
    try:
        batch = client.batches.retrieve(batch_id)
        
        print(f"\n📈 Batch Status:")
        print(f"   ID: {batch.id}")
        print(f"   Status: {batch.status}")
        print(f"   Created: {batch.created_at}")
        
        if batch.request_counts:
            print(f"   Total requests: {batch.request_counts.total}")
            print(f"   Completed: {batch.request_counts.completed}")
            print(f"   Failed: {batch.request_counts.failed}")
            
            if batch.request_counts.total > 0:
                progress = (batch.request_counts.completed / batch.request_counts.total) * 100
                print(f"   Progress: {progress:.1f}%")
        
        if batch.status == 'completed':
            print("\n✅ Batch is complete!")
            
            # Ask if user wants to process results
            response = input("\nProcess results now? (y/n): ")
            if response.lower() == 'y':
                generator = ProcessDetailsBatchGenerator(model_key='apqc_pcf')
                generator.setup()
                generator.process_results(batch)
        elif batch.status in ['failed', 'expired', 'cancelled']:
            print(f"\n❌ Batch {batch.status}")
            if batch.errors:
                print(f"   Errors: {batch.errors}")
        else:
            print(f"\n⏳ Batch is still processing...")
            print("   Run this script again later to check progress.")
            
    except Exception as e:
        print(f"❌ Error retrieving batch: {str(e)}")

if __name__ == '__main__':
    main()