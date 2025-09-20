#!/usr/bin/env python
"""
Create corrected JSON batch file with 12 separate waste type requests per process.
This creates 120 total requests (10 processes × 12 waste types).
"""

import os
import sys
import json
import tempfile
from datetime import datetime
from pathlib import Path

# Add parent directory to path for Django imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force SQLite for testing - prevent .env file from being loaded
temp_env_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
temp_env_file.write("# Empty env file for testing with SQLite\n")
temp_env_file.close()
os.environ['DOTENV_PATH'] = temp_env_file.name

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()
os.unlink(temp_env_file.name)

from core.models import ProcessNode, ProcessModelVersion, NodeDocument, AdminSettings, NodeAttribute

class CorrectedWasteBatchGenerator:
    def __init__(self, model_key='apqc_pcf', limit=10):
        self.model_key = model_key
        self.limit = limit
        self.model_version = None
        self.openai_model = "gpt-5"  # Match successful batches
        self.output_dir = Path('batch_waste_analysis')
        self.output_dir.mkdir(exist_ok=True)

        # Define the 12 waste types
        self.waste_types = {
            'transportation': {
                'emoji': '🚛',
                'name': 'Transportation Waste',
                'description': 'Unnecessary movement of materials, information, or outputs between steps'
            },
            'inventory': {
                'emoji': '📦',
                'name': 'Inventory Waste',
                'description': 'Excess work-in-progress, queued items, or stored materials/data'
            },
            'motion': {
                'emoji': '🏃',
                'name': 'Motion Waste',
                'description': 'Unnecessary movement of people or excessive navigation'
            },
            'waiting': {
                'emoji': '⏳',
                'name': 'Waiting Waste',
                'description': 'Delays and idle time in the process'
            },
            'overprocessing': {
                'emoji': '⚙️',
                'name': 'Overprocessing Waste',
                'description': 'Unnecessary steps, excessive quality, or redundant activities'
            },
            'overproduction': {
                'emoji': '📈',
                'name': 'Overproduction Waste',
                'description': 'Producing more, earlier, or faster than required'
            },
            'defects': {
                'emoji': '❌',
                'name': 'Defects Waste',
                'description': 'Rework, corrections, and quality issues'
            },
            'skills': {
                'emoji': '🧠',
                'name': 'Skills Underutilization',
                'description': 'Underused human capabilities and expertise'
            },
            'environmental': {
                'emoji': '🌱',
                'name': 'Environmental Waste',
                'description': 'Environmental impact and sustainability issues'
            },
            'digital': {
                'emoji': '📱',
                'name': 'Digital Waste',
                'description': 'Inefficiencies in digital processes and technology'
            },
            'social': {
                'emoji': '🤝',
                'name': 'Social Waste',
                'description': 'Human and social factors that create inefficiency'
            },
            'systemic': {
                'emoji': '🎯',
                'name': 'Systemic Waste',
                'description': 'Broader organizational and process design issues'
            }
        }

    def setup(self):
        """Setup model version."""
        try:
            self.model_version = ProcessModelVersion.objects.filter(
                model__model_key=self.model_key,
                is_current=True
            ).first()

            if not self.model_version:
                raise ValueError(f"No active model version found for key: {self.model_key}")

            print(f"✅ Model: {self.model_version.model.name}")
            print(f"   Version: {self.model_version.version_label}")
            print(f"   OpenAI Model: {self.openai_model}")

        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False

        return True

    def get_pcf_id(self, node):
        """Get PCF ID for a node."""
        try:
            pcf_id_attr = NodeAttribute.objects.filter(
                node=node,
                key__in=['PCF_ID', 'pcf_id', 'PCF ID']
            ).first()
            return pcf_id_attr.value if pcf_id_attr else None
        except:
            return None

    def get_test_nodes(self):
        """Get nodes with process details for testing."""
        nodes_with_details = []

        nodes = ProcessNode.objects.filter(
            model_version=self.model_version,
            level__gte=4
        ).prefetch_related('documents').order_by('code')

        print(f"🔍 Searching for nodes with process details...")

        for node in nodes:
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

    def build_waste_prompt(self, node, process_details, waste_type, waste_info):
        """Build prompt for a specific waste type analysis."""

        # Build hierarchy context
        hierarchy = []
        current = node
        while current:
            hierarchy.insert(0, f"[{current.code}] {current.name}")
            current = current.parent
        hierarchy_text = "\n  ".join(hierarchy[:-1])

        # Create focused prompt for the specific waste type
        prompt = f"""Analyze the following business process for {waste_info['name']} using Lean Six Sigma methodology.

Process Hierarchy:
{hierarchy_text}

Current Process:
[{node.code}] {node.name}
Level: {node.level}
Description: {node.description or 'N/A'}

Process Details:
{process_details.content}

## {waste_info['emoji']} {waste_info['name']} Analysis

Focus specifically on **{waste_info['name']}**: {waste_info['description']}.

Please provide a detailed markdown analysis covering:

### 1. Waste Identification
- What specific {waste_info['name'].lower()} instances are present in this process?
- Where exactly do these waste patterns occur?
- What evidence supports these identifications?

### 2. Impact Assessment
- Rate the significance of each identified waste (High/Medium/Low)
- Estimate the impact on process efficiency, cost, and quality
- Quantify where possible (time, cost, resources affected)

### 3. Root Cause Analysis
- Why does this waste occur in this process?
- What underlying factors contribute to this waste?
- Are there systemic causes vs. operational causes?

### 4. Improvement Recommendations
- Specific, actionable recommendations to eliminate or reduce this waste
- Prioritize recommendations by impact and feasibility
- Consider both quick wins and strategic improvements

### 5. Success Metrics
- How would you measure reduction of this waste type?
- What KPIs or metrics would track improvement?
- How would you monitor ongoing performance?

### 6. Implementation Considerations
- What resources would be needed for implementation?
- What potential obstacles or resistance might arise?
- How would you sequence the improvements?

**Format your response as a detailed markdown document with clear sections and bullet points.**
**Focus exclusively on {waste_info['name']} - do not cover other waste types.**
**Provide specific, actionable insights that could realistically improve this process.**"""

        return prompt

    def create_corrected_batch_file(self, nodes_with_details):
        """Create corrected JSONL file with 12 requests per process."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = self.output_dir / f'CORRECTED_batch_input_waste_{self.model_key}_{timestamp}.jsonl'

        requests = []

        for node, process_details in nodes_with_details:
            # Get PCF ID for this node
            pcf_id = self.get_pcf_id(node)

            # Create 12 requests for each node (one per waste type)
            for waste_key, waste_info in self.waste_types.items():
                prompt = self.build_waste_prompt(node, process_details, waste_key, waste_info)

                request = {
                    "custom_id": f"node_{node.id}_{node.code}_{waste_key}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": f"You are a Lean Six Sigma expert specializing in {waste_info['name']} identification and elimination. Provide detailed, actionable analysis in markdown format."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_completion_tokens": 4000,
                        "metadata": {
                            "node_id": str(node.id),
                            "node_code": node.code,
                            "pcf_id": pcf_id,
                            "model_id": str(self.model_version.model.id),
                            "model_name": self.model_version.model.name,
                            "model_version": self.model_version.version_label,
                            "waste_type": waste_key,
                            "waste_name": waste_info['name'],
                            "process_name": node.name[:100]
                        }
                    }
                }
                requests.append(request)

        # Write JSONL file
        with open(input_file, 'w', encoding='utf-8') as f:
            for request in requests:
                f.write(json.dumps(request, ensure_ascii=False) + '\n')

        print(f"\n✅ Created CORRECTED batch input file: {input_file}")
        print(f"   Total requests: {len(requests)}")
        print(f"   Processes: {len(nodes_with_details)}")
        print(f"   Waste types per process: {len(self.waste_types)}")
        print(f"   File size: {input_file.stat().st_size:,} bytes")

        # Show structure breakdown
        print(f"\n📋 Request structure:")
        print(f"   Custom ID format: node_{{id}}_{{code}}_{{waste_type}}")
        print(f"   Model: {self.openai_model}")
        print(f"   Max tokens: 4000")
        print(f"   Format: Markdown")
        print(f"   Metadata includes: node_id, node_code, pcf_id, model_id, model_name, model_version, waste_type, waste_name, process_name")

        if requests:
            print(f"\n🔍 Sample custom IDs:")
            for i in range(min(3, len(requests))):
                print(f"   - {requests[i]['custom_id']}")
            if len(requests) > 3:
                print(f"   - ... and {len(requests) - 3} more")

        return input_file

def main():
    """Create corrected batch file with 12 waste types per process."""
    print("🔧 Creating CORRECTED waste analysis batch file...")
    print("   - 12 separate requests per process (one per waste type)")
    print("   - Explicit markdown format")
    print("   - Waste type in metadata")
    print("   - Focused analysis per waste type")
    print("=" * 70)

    generator = CorrectedWasteBatchGenerator(limit=10)

    if not generator.setup():
        return

    # Get test nodes
    nodes_with_details = generator.get_test_nodes()

    if not nodes_with_details:
        print("❌ No nodes with process details found!")
        return

    # Create corrected batch file
    input_file = generator.create_corrected_batch_file(nodes_with_details)

    print(f"\n🎯 Corrected batch ready:")
    print(f"   File: {input_file}")
    print(f"   Structure: 12 focused waste analysis requests per process")
    print(f"   Format: Markdown with clear sections")
    print(f"   Metadata: Proper waste type tracking")
    print(f"\n🚀 Ready for submission to OpenAI!")

if __name__ == '__main__':
    main()