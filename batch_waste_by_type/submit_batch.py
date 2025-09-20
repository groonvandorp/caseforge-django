#!/usr/bin/env python
"""
Submit the prepared test batch file directly to OpenAI for processing.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for Django imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force SQLite for testing - prevent .env file from being loaded
import tempfile
temp_env_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
temp_env_file.write("# Empty env file for testing with SQLite\n")
temp_env_file.close()

# Override the .env file path before any imports
os.environ['DOTENV_PATH'] = temp_env_file.name

import django
from openai import OpenAI

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

# Clean up temp file
os.unlink(temp_env_file.name)

from core.models import AdminSettings

def submit_batch():
    """Submit the prepared test batch file to OpenAI."""

    # Find the corrected batch file (prefer CORRECTED over TEST)
    output_dir = Path('batch_waste_analysis')
    corrected_files = list(output_dir.glob('CORRECTED_batch_input_*.jsonl'))
    test_files = list(output_dir.glob('TEST_batch_input_*.jsonl'))

    if corrected_files:
        # Use the most recent corrected file
        input_file = sorted(corrected_files)[-1]
        print("🔧 Using corrected batch file with complete metadata")
    elif test_files:
        # Fall back to test file
        input_file = sorted(test_files)[-1]
        print("🧪 Using test batch file")
    else:
        print("❌ No batch file found!")
        return
    print(f"🚀 Submitting batch file: {input_file}")

    # Get OpenAI API key
    try:
        api_key = AdminSettings.get_setting('openai_api_key')
        if not api_key:
            print("❌ OpenAI API key not found in admin settings!")
            print("   Please set the API key in Django admin first.")
            return

        print("✅ OpenAI API key found")
    except Exception as e:
        print(f"❌ Error getting API key: {e}")
        return

    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)

    try:
        # Count requests in file
        with open(input_file, 'r') as f:
            request_count = sum(1 for line in f)

        print(f"📊 Batch file contains {request_count} requests")

        # Upload file to OpenAI
        print("📤 Uploading file to OpenAI...")
        with open(input_file, 'rb') as f:
            batch_file = client.files.create(
                file=f,
                purpose='batch'
            )

        print(f"✅ File uploaded: {batch_file.id}")

        # Submit batch job
        print("🚀 Submitting batch job...")
        batch = client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "description": "TIMWOOD+ Waste Analysis Test Batch",
                "process_count": str(request_count),
                "submitted_at": datetime.now().isoformat()
            }
        )

        print(f"✅ Batch submitted successfully!")
        print(f"   Batch ID: {batch.id}")
        print(f"   Status: {batch.status}")
        print(f"   Created: {batch.created_at}")
        print(f"   Completion window: {batch.completion_window}")

        # Save batch ID for monitoring
        batch_id_file = output_dir / 'current_batch_id.txt'
        with open(batch_id_file, 'w') as f:
            f.write(batch.id)

        print(f"💾 Batch ID saved to: {batch_id_file}")

        # Show monitoring instructions
        print(f"\n🎯 Next steps:")
        print(f"   1. Monitor progress: python batch_waste_by_type/monitor_waste_batch.py")
        print(f"   2. Check status manually: batch ID {batch.id}")
        print(f"   3. Expected completion: 24 hours (typically much faster)")
        print(f"   4. Results will be processed automatically when complete")

        return batch

    except Exception as e:
        print(f"❌ Error submitting batch: {e}")
        return None

if __name__ == '__main__':
    print("🚀 Submitting waste analysis batch to OpenAI...")
    print("=" * 60)
    submit_batch()