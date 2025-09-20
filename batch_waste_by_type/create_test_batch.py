#!/usr/bin/env python
"""
Create a test JSON batch file for waste analysis on 10 process nodes.
This allows us to inspect the batch requests before submitting to OpenAI.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path for Django imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import django
from openai import OpenAI

# Force SQLite for testing - prevent .env file from being loaded
import tempfile
temp_env_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
temp_env_file.write("# Empty env file for testing with SQLite\n")
temp_env_file.close()

# Override the .env file path before any imports
os.environ['DOTENV_PATH'] = temp_env_file.name

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

# Clean up temp file
os.unlink(temp_env_file.name)

from core.models import ProcessNode, ProcessModelVersion, NodeDocument, AdminSettings
from django.contrib.auth import get_user_model

User = get_user_model()

class TestBatchGenerator:
    def __init__(self, model_key='apqc_pcf', limit=10):
        self.model_key = model_key
        self.limit = limit
        self.model_version = None
        self.openai_model = "gpt-4o-mini"  # Default model
        self.temperature = 0.1
        self.output_dir = Path('batch_waste_analysis')
        self.output_dir.mkdir(exist_ok=True)

    def setup(self):
        """Setup model version."""
        # Get process model version
        try:
            self.model_version = ProcessModelVersion.objects.filter(
                model__model_key=self.model_key,
                is_current=True
            ).first()

            if not self.model_version:
                raise ValueError(f"No active model version found for key: {self.model_key}")

            print(f"✅ Model: {self.model_version.model.name}")
            print(f"   Version: {self.model_version.version_label}")

            # Try to get OpenAI model from settings
            try:
                model_setting = AdminSettings.get_setting('openai_model')
                if model_setting:
                    self.openai_model = model_setting
                    print(f"   OpenAI Model: {self.openai_model}")
            except:
                print(f"   OpenAI Model: {self.openai_model} (default)")

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False

        return True

    def get_test_nodes(self):
        """Get 10 nodes with process details for testing."""
        # Get nodes that have process details documents
        nodes_with_details = []

        nodes = ProcessNode.objects.filter(
            model_version=self.model_version,
            level__gte=4  # Focus on leaf or near-leaf nodes
        ).prefetch_related('documents').order_by('code')

        print(f"🔍 Searching for nodes with process details...")

        for node in nodes:
            # Check if node has process details
            process_details = node.documents.filter(
                document_type='process_details'
            ).first()

            if process_details:
                nodes_with_details.append((node, process_details))
                print(f"   ✅ Found: [{node.code}] {node.name[:60]}...")

                if len(nodes_with_details) >= self.limit:
                    break

        print(f"📊 Found {len(nodes_with_details)} nodes with process details")
        return nodes_with_details

    def build_waste_analysis_prompt(self, node, process_details):
        """Build the prompt for waste analysis (same as main script)."""

        # Build hierarchy context
        hierarchy = []
        current = node
        while current:
            hierarchy.insert(0, f"[{current.code}] {current.name}")
            current = current.parent
        hierarchy_text = "\n  ".join(hierarchy[:-1])  # Exclude the current node

        prompt = f"""Analyze the following business process for waste using the TIMWOOD framework and modern extensions.

Process Hierarchy:
{hierarchy_text}

Current Process:
[{node.code}] {node.name}
Level: {node.level}
Description: {node.description or 'N/A'}

Process Details:
{process_details.content}

Please provide a comprehensive waste analysis covering:

## 🚛 Transportation Waste
Analyze unnecessary movement of materials, information, or outputs between steps.
- Physical movement of documents/materials
- Digital file transfers between systems
- Handoffs between departments
Consider: Are items/data moving more than necessary? Can steps be co-located?

## 📦 Inventory Waste
Identify excess work-in-progress, queued items, or stored materials/data.
- Backlog accumulation
- Buffer stocks
- Incomplete work items
Consider: What's sitting idle? What's being produced before needed?

## 🏃 Motion Waste
Examine unnecessary movement of people or excessive navigation.
- Physical movement to access resources
- System/application switching
- Searching for information
Consider: Can workspace/systems be optimized to reduce movement?

## ⏳ Waiting Waste
Identify delays and idle time in the process.
- Approval delays
- System response times
- Dependency bottlenecks
- Decision-making delays
Consider: Where do things get stuck? What causes delays?

## ⚙️ Overprocessing Waste
Find unnecessary steps, excessive quality, or redundant activities.
- Multiple approvals
- Duplicate data entry
- Over-documentation
- Gold-plating
Consider: What steps don't add value? What could be simplified?

## 📈 Overproduction Waste
Detect producing more, earlier, or faster than required.
- Reports nobody reads
- Features nobody uses
- Premature work
Consider: What's being created that isn't immediately needed?

## ❌ Defects Waste
Identify rework, corrections, and quality issues.
- Error rates
- Rework cycles
- Customer complaints
- Data quality issues
Consider: What gets sent back? What needs correction?

## 🧠 Skills Underutilization
Examine if people's capabilities are fully leveraged.
- Routine work for skilled personnel
- Limited decision authority
- Underused expertise
- Poor task-skill matching
Consider: Are people working below their capability level?

## 🌱 Environmental Waste
Assess environmental impact and sustainability issues.
- Resource consumption
- Energy usage
- Waste generation
- Carbon footprint
Consider: What environmental impact can be reduced?

## 📱 Digital Waste
Analyze inefficiencies in digital processes and technology.
- System redundancies
- Manual data entry
- Legacy system dependencies
- Integration gaps
Consider: How can digital processes be optimized?

## 🤝 Social Waste
Evaluate human and social factors that create inefficiency.
- Poor communication
- Organizational silos
- Unclear roles
- Conflict resolution
Consider: What social factors impede efficiency?

## 🎯 Systemic Waste
Examine broader organizational and process design issues.
- Misaligned incentives
- Policy conflicts
- Structural inefficiencies
- Process boundaries
Consider: What system-level changes would improve efficiency?

For each waste type, provide:
1. **Identification**: What specific wastes are present?
2. **Impact**: How significant is each waste (High/Medium/Low)?
3. **Root Causes**: Why does this waste occur?
4. **Recommendations**: Specific, actionable improvement suggestions
5. **Metrics**: How could you measure improvement?

Format your response as structured analysis with clear sections for each waste type.
Focus on practical, implementable recommendations that could realistically improve this process."""

        return prompt

    def create_test_batch_file(self, nodes_with_details):
        """Create JSONL file for testing (without submitting to OpenAI)."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = self.output_dir / f'TEST_batch_input_waste_{self.model_key}_{timestamp}.jsonl'

        requests = []
        for i, (node, process_details) in enumerate(nodes_with_details):
            prompt = self.build_waste_analysis_prompt(node, process_details)

            request = {
                "custom_id": f"node_{node.id}_{node.code}",
                "method": "POST",
                "url": "/v1/chat/completions",
                "body": {
                    "model": self.openai_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a Lean Six Sigma expert specializing in waste identification and process optimization. Provide detailed, actionable analysis of process waste using TIMWOOD and modern frameworks."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": self.temperature,
                    "max_completion_tokens": 6000
                }
            }
            requests.append(request)

        # Write JSONL file
        with open(input_file, 'w', encoding='utf-8') as f:
            for request in requests:
                f.write(json.dumps(request, ensure_ascii=False) + '\n')

        print(f"\n✅ Created TEST batch input file: {input_file}")
        print(f"   Total requests: {len(requests)}")
        print(f"   File size: {input_file.stat().st_size:,} bytes")

        # Show first request structure
        if requests:
            print(f"\n📋 Sample request structure:")
            print(f"   Custom ID: {requests[0]['custom_id']}")
            print(f"   Model: {requests[0]['body']['model']}")
            print(f"   Max tokens: {requests[0]['body']['max_completion_tokens']}")
            print(f"   Temperature: {requests[0]['body']['temperature']}")
            print(f"   Prompt length: {len(requests[0]['body']['messages'][1]['content']):,} chars")

        return input_file

def main():
    """Create test batch file for waste analysis."""
    print("🧪 Creating test batch file for waste analysis...")
    print("=" * 60)

    generator = TestBatchGenerator(limit=10)

    if not generator.setup():
        return

    # Get test nodes
    nodes_with_details = generator.get_test_nodes()

    if not nodes_with_details:
        print("❌ No nodes with process details found!")
        return

    # Create test batch file
    input_file = generator.create_test_batch_file(nodes_with_details)

    print(f"\n🎯 Next steps:")
    print(f"   1. Review the file: {input_file}")
    print(f"   2. Check the JSON structure and prompts")
    print(f"   3. If satisfied, use the main script to submit to OpenAI")
    print(f"   4. Monitor with: python monitor_waste_batch.py")

if __name__ == '__main__':
    main()