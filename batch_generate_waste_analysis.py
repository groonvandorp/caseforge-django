#!/usr/bin/env python
"""
Batch generation of waste analysis (TIMWOOD+) for processes using OpenAI Batch API.

This script:
1. Loads all nodes with existing process_details documents
2. Analyzes each process for various types of waste
3. Generates structured waste identification and recommendations
4. Stores results in database as NodeDocument records

Prerequisites: Process details must exist for nodes (run batch_generate_process_details.py first)
"""

import os
import sys
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path

import django
from openai import OpenAI

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, ProcessModelVersion, NodeDocument, AdminSettings
from django.contrib.auth import get_user_model

User = get_user_model()

class WasteAnalysisBatchGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.admin_user = None
        self.model_version = None
        self.openai_model = None
        self.output_dir = Path('batch_waste_analysis')
        self.output_dir.mkdir(exist_ok=True)

    def setup(self):
        """Setup OpenAI client and get model version."""
        # Get OpenAI API key from admin settings
        api_key = AdminSettings.get_setting('openai_api_key')
        if not api_key:
            raise ValueError("OpenAI API key not found in admin settings")

        self.client = OpenAI(api_key=api_key)

        # Get OpenAI model from admin settings
        self.openai_model = AdminSettings.get_setting('openai_model', 'gpt-5')

        # Get temperature
        self.temperature = float(AdminSettings.get_setting('openai_temperature', '0.7'))

        # Get gruhno user for document creation
        self.admin_user = User.objects.filter(username='gruhno').first()
        if not self.admin_user:
            # Fallback to admin user
            self.admin_user = User.objects.filter(is_superuser=True).first()
            if not self.admin_user:
                raise ValueError("No admin user found")

        # Get model version
        self.model_version = ProcessModelVersion.objects.filter(
            model__model_key=self.model_key,
            is_current=True
        ).first()

        if not self.model_version:
            raise ValueError(f"Model {self.model_key} not found")

        print(f"✅ Setup complete")
        print(f"   Process Model: {self.model_version.model.name}")
        print(f"   OpenAI Model: {self.openai_model}")
        print(f"   Temperature: {self.temperature}")
        print(f"   User: {self.admin_user.email}")

    def get_nodes_with_process_details(self):
        """Get all nodes that have process details documents."""
        all_nodes = ProcessNode.objects.filter(model_version=self.model_version)

        nodes_with_details = []
        nodes_without_details = []

        for node in all_nodes:
            # Check if node has process details
            process_details = NodeDocument.objects.filter(
                node=node,
                document_type='process_details'
            ).first()

            if process_details:
                # Check if waste analysis already exists
                existing_waste = NodeDocument.objects.filter(
                    node=node,
                    document_type='waste_analysis'
                ).first()

                if not existing_waste:
                    nodes_with_details.append((node, process_details))
            else:
                nodes_without_details.append(node)

        print(f"✅ Found {len(nodes_with_details)} nodes with process details (no waste analysis yet)")
        if nodes_without_details:
            print(f"⚠️  {len(nodes_without_details)} nodes without process details (skipping)")

        return nodes_with_details

    def build_waste_analysis_prompt(self, node, process_details):
        """Build the prompt for waste analysis."""

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
- Manual work that could be automated
- Senior staff doing junior tasks
- Unused employee knowledge
Consider: Are the right people doing the right work?

## 💻 Digital Waste
Modern digital and technology-related inefficiencies.
- System incompatibilities
- Manual data transfers
- Outdated technology
- Poor user interfaces
Consider: How is technology creating waste?

## 📚 Knowledge Waste
Information and learning inefficiencies.
- Repeated problem-solving
- Lost institutional knowledge
- Poor knowledge sharing
- Training gaps
Consider: Is knowledge being captured and shared effectively?

## 📋 Compliance Waste
Regulatory and policy-related inefficiencies.
- Excessive controls
- Redundant audits
- Over-compliance
- Outdated policies
Consider: Are compliance activities proportional to risk?

## 💬 Communication Waste
Information flow and collaboration inefficiencies.
- Unnecessary meetings
- Email overload
- Unclear instructions
- Missing feedback loops
Consider: How can communication be streamlined?

For each waste category:
1. Identify specific examples from this process
2. Rate the impact (High/Medium/Low/None)
3. Suggest practical improvements
4. Distinguish quick wins from strategic initiatives

Format your response as structured markdown with clear sections and actionable insights."""

        return prompt

    def prepare_batch_file(self, nodes_with_details):
        """Prepare JSONL file for batch processing."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        input_file = self.output_dir / f'batch_input_waste_{self.model_key}_{timestamp}.jsonl'

        requests = []
        for node, process_details in nodes_with_details:
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
        with open(input_file, 'w') as f:
            for request in requests:
                f.write(json.dumps(request) + '\n')

        print(f"✅ Created batch input file: {input_file}")
        print(f"   Total requests: {len(requests)}")

        return input_file

    def submit_batch(self, input_file):
        """Submit batch to OpenAI API."""
        with open(input_file, 'rb') as f:
            batch_file = self.client.files.create(
                file=f,
                purpose='batch'
            )

        batch = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "description": f"Waste analysis for {self.model_key}",
                "type": "waste_analysis",
                "timestamp": datetime.now().isoformat()
            }
        )

        print(f"✅ Batch submitted")
        print(f"   Batch ID: {batch.id}")
        print(f"   Status: {batch.status}")

        # Save batch ID for monitoring
        batch_id_file = self.output_dir / 'current_batch_id.txt'
        with open(batch_id_file, 'w') as f:
            f.write(batch.id)

        return batch

    def poll_batch_status(self, batch_id, interval=60):
        """Poll batch status until completion."""
        while True:
            batch = self.client.batches.retrieve(batch_id)

            print(f"\r⏳ Status: {batch.status} | Progress: {batch.request_counts.completed}/{batch.request_counts.total}", end='')

            if batch.status == 'completed':
                print(f"\n✅ Batch completed!")
                print(f"   Completed: {batch.request_counts.completed}")
                print(f"   Failed: {batch.request_counts.failed}")
                return batch
            elif batch.status == 'failed':
                print(f"\n❌ Batch failed!")
                print(f"   Error: {batch.errors}")
                return batch
            elif batch.status == 'cancelled':
                print(f"\n⚠️ Batch cancelled")
                return batch

            time.sleep(interval)

    def process_results(self, batch):
        """Download and process batch results."""
        if batch.status != 'completed':
            print("❌ Batch not completed, cannot process results")
            return

        # Download result file
        output_file_id = batch.output_file_id
        output_file = self.client.files.content(output_file_id)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = self.output_dir / f'batch_output_waste_{self.model_key}_{timestamp}.jsonl'

        with open(output_path, 'wb') as f:
            f.write(output_file.content)

        print(f"✅ Downloaded results to: {output_path}")

        # Process each result
        success_count = 0
        error_count = 0
        failed_nodes = []

        with open(output_path, 'r') as f:
            for line in f:
                result = json.loads(line)
                custom_id = result['custom_id']

                if result.get('error'):
                    error_count += 1
                    node_id = custom_id.split('_')[1]
                    failed_nodes.append(node_id)
                    print(f"❌ Error for {custom_id}: {result['error']}")
                    continue

                # Extract node ID from custom_id
                node_id = int(custom_id.split('_')[1])

                # Get the response content
                response = result['response']
                if response['status_code'] == 200:
                    content = response['body']['choices'][0]['message']['content']

                    # Store in database
                    node = ProcessNode.objects.get(id=node_id)

                    # Check if waste analysis already exists
                    existing = NodeDocument.objects.filter(
                        node=node,
                        document_type='waste_analysis'
                    ).first()

                    if existing:
                        # Update existing document
                        existing.content = content
                        existing.updated_at = datetime.now()
                        existing.meta_json = {
                            'generated_by': 'batch_api',
                            'model': self.openai_model,
                            'temperature': self.temperature,
                            'batch_id': batch.id,
                            'request_id': result.get('id'),
                            'timestamp': datetime.now().isoformat()
                        }
                        existing.save()
                        print(f"📝 Updated waste analysis for: {node.code} - {node.name}")
                    else:
                        # Create new document
                        NodeDocument.objects.create(
                            node=node,
                            document_type='waste_analysis',
                            title=f"Waste Analysis (TIMWOOD+) - {node.name}",
                            content=content,
                            user=self.admin_user,
                            meta_json={
                                'generated_by': 'batch_api',
                                'model': self.openai_model,
                                'temperature': self.temperature,
                                'batch_id': batch.id,
                                'request_id': result.get('id'),
                                'timestamp': datetime.now().isoformat()
                            }
                        )
                        print(f"✅ Created waste analysis for: {node.code} - {node.name}")

                    success_count += 1
                else:
                    error_count += 1
                    node_id = custom_id.split('_')[1]
                    failed_nodes.append(node_id)
                    print(f"❌ HTTP error for {custom_id}: {response['status_code']}")

        # Save failed nodes for retry
        if failed_nodes:
            failed_file = self.output_dir / 'failed_node_ids.txt'
            with open(failed_file, 'w') as f:
                for node_id in failed_nodes:
                    f.write(f"{node_id}\n")
            print(f"⚠️  Saved {len(failed_nodes)} failed node IDs to: {failed_file}")

        print(f"\n📊 Final Statistics:")
        print(f"   Success: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"   Total processed: {success_count + error_count}")

        return success_count, error_count

    def run(self, auto_poll=True):
        """Main execution method."""
        print("🚀 Starting Waste Analysis Batch Generation")
        print("=" * 50)

        # Setup
        self.setup()

        # Get nodes with process details
        nodes_with_details = self.get_nodes_with_process_details()

        if not nodes_with_details:
            print("⚠️  No nodes found for processing")
            return

        # Ask for confirmation
        response = input(f"\nGenerate waste analysis for {len(nodes_with_details)} nodes? (y/n): ")
        if response.lower() != 'y':
            print("❌ Cancelled")
            return

        # Prepare batch file
        input_file = self.prepare_batch_file(nodes_with_details)

        # Submit batch
        batch = self.submit_batch(input_file)

        if auto_poll:
            # Poll for completion
            print("\n⏳ Polling for batch completion...")
            completed_batch = self.poll_batch_status(batch.id)

            # Process results
            if completed_batch.status == 'completed':
                print("\n📥 Processing results...")
                self.process_results(completed_batch)
        else:
            print(f"\n💡 Batch submitted. Run monitor script to check status:")
            print(f"   python monitor_waste_batch.py")

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate waste analysis for processes')
    parser.add_argument('--model', default='apqc_pcf', help='Model key (default: apqc_pcf)')
    parser.add_argument('--no-poll', action='store_true', help='Submit without polling')

    args = parser.parse_args()

    generator = WasteAnalysisBatchGenerator(model_key=args.model)
    generator.run(auto_poll=not args.no_poll)

if __name__ == '__main__':
    main()