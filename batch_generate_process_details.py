#!/usr/bin/env python
"""
Batch generation of process details for all leaf nodes using OpenAI Batch API.

This script:
1. Prepares a JSONL file with all requests
2. Submits to OpenAI batch API
3. Polls for completion
4. Stores results in database as NodeDocument records
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

class ProcessDetailsBatchGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.admin_user = None
        self.model_version = None
        self.openai_model = None  # Will be set from admin settings
        self.output_dir = Path('batch_process_details')
        self.output_dir.mkdir(exist_ok=True)
        
    def setup(self):
        """Setup OpenAI client and get model version."""
        # Get OpenAI API key from admin settings
        api_key = AdminSettings.get_setting('openai_api_key')
        if not api_key:
            raise ValueError("OpenAI API key not found in admin settings")
        
        self.client = OpenAI(api_key=api_key)
        
        # Get OpenAI model from admin settings (default to gpt-5 for high quality)
        self.openai_model = AdminSettings.get_setting('openai_model', 'gpt-5')
        
        # Get temperature (defaults to 1.0 for GPT-5 if not specified)
        self.temperature = float(AdminSettings.get_setting('openai_temperature', '1.0'))
        
        # Get admin user for document creation
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
        print(f"   Admin user: {self.admin_user.email}")
        
    def get_leaf_nodes(self):
        """Get all leaf nodes for the model."""
        all_nodes = ProcessNode.objects.filter(model_version=self.model_version)
        leaf_nodes = [node for node in all_nodes if node.is_leaf]
        print(f"✅ Found {len(leaf_nodes)} leaf nodes")
        return leaf_nodes
    
    def build_hierarchical_context(self, node):
        """Build the hierarchical context for a node."""
        context_parts = []
        current = node
        hierarchy = []
        
        # Build hierarchy from node up to root
        while current:
            hierarchy.insert(0, {
                'level': current.level,
                'code': current.code,
                'name': current.name,
                'description': current.description
            })
            current = current.parent
            
        # Format hierarchy for context
        for item in hierarchy[:-1]:  # Exclude the leaf node itself
            indent = "  " * (item['level'] - 1)
            context_parts.append(f"{indent}[{item['code']}] {item['name']}")
            if item['description']:
                context_parts.append(f"{indent}    {item['description'][:200]}")
        
        return "\n".join(context_parts)
    
    def create_prompt(self, node):
        """Create the prompt for generating process details."""
        hierarchy_context = self.build_hierarchical_context(node)
        
        prompt = f"""Generate comprehensive process details for the following business process node.

Process Hierarchy:
{hierarchy_context}

Current Process:
[{node.code}] {node.name}
Level: {node.level}
Description: {node.description or 'No description provided'}

Please provide a detailed markdown document covering:

## Overview
Provide a comprehensive overview of this process, its purpose, and its role in the organization.

## Key Activities
List and describe the main activities involved in this process.

## Inputs and Prerequisites
- Required inputs to begin this process
- Prerequisites that must be met
- Dependencies on other processes

## Process Steps
Provide a detailed step-by-step breakdown of how this process is executed.

## Outputs and Deliverables
- Expected outputs from this process
- Deliverables produced
- Success criteria

## Roles and Responsibilities
Identify key roles involved and their responsibilities in this process.

## Best Practices
List industry best practices and recommendations for this process.

## Common Challenges
Identify common challenges and potential solutions.

## Performance Metrics
Suggest KPIs and metrics to measure process effectiveness.

## Technology and Tools
Identify relevant technologies, tools, or systems that support this process.

Generate detailed, actionable content that would be valuable for process documentation and improvement initiatives."""

        return prompt
    
    def prepare_batch_file(self, leaf_nodes):
        """Prepare the JSONL batch file for OpenAI."""
        batch_file_path = self.output_dir / f'batch_input_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
        with open(batch_file_path, 'w') as f:
            for i, node in enumerate(leaf_nodes):
                prompt = self.create_prompt(node)
                
                # Create the batch request object
                request = {
                    "custom_id": f"node_{node.id}_{node.code}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a business process expert helping to document and analyze business processes. Generate detailed, actionable process documentation."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_completion_tokens": 8000
                    }
                }
                
                f.write(json.dumps(request) + '\n')
                
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(leaf_nodes)} nodes...")
        
        print(f"✅ Batch file created: {batch_file_path}")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """Submit the batch to OpenAI."""
        print("\n🚀 Submitting batch to OpenAI...")
        
        with open(batch_file_path, 'rb') as f:
            batch_file = self.client.files.create(
                file=f,
                purpose="batch"
            )
        
        batch = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={
                "model_key": self.model_key,
                "type": "process_details_generation"
            }
        )
        
        print(f"✅ Batch submitted")
        print(f"   Batch ID: {batch.id}")
        print(f"   Status: {batch.status}")
        
        return batch
    
    def poll_batch_status(self, batch_id, check_interval=60):
        """Poll for batch completion."""
        print(f"\n⏳ Polling batch status (checking every {check_interval} seconds)...")
        
        while True:
            batch = self.client.batches.retrieve(batch_id)
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Status: {batch.status}", end="")
            
            if batch.request_counts:
                print(f" | Completed: {batch.request_counts.completed}/{batch.request_counts.total}", end="")
            
            print()  # New line
            
            if batch.status == 'completed':
                print("\n✅ Batch completed!")
                return batch
            elif batch.status in ['failed', 'expired', 'cancelled']:
                print(f"\n❌ Batch {batch.status}")
                return None
            
            time.sleep(check_interval)
    
    def process_results(self, batch):
        """Process the batch results and store in database."""
        print("\n📥 Processing results...")
        
        # Download the output file
        output_file = self.client.files.content(batch.output_file_id)
        output_path = self.output_dir / f'batch_output_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
        with open(output_path, 'wb') as f:
            f.write(output_file.read())
        
        print(f"✅ Results downloaded to: {output_path}")
        
        # Process each result
        success_count = 0
        error_count = 0
        
        with open(output_path, 'r') as f:
            for line in f:
                result = json.loads(line)
                custom_id = result['custom_id']
                
                # Extract node ID from custom_id and OpenAI request ID
                node_id = int(custom_id.split('_')[1])
                request_id = result['response'].get('request_id')
                
                try:
                    if result['response']['status_code'] == 200:
                        content = result['response']['body']['choices'][0]['message']['content']
                        
                        # Get the node
                        node = ProcessNode.objects.get(id=node_id)
                        
                        # Delete existing process_details document if exists
                        NodeDocument.objects.filter(
                            node=node,
                            document_type='process_details'
                        ).delete()
                        
                        # Create new document
                        NodeDocument.objects.create(
                            node=node,
                            document_type='process_details',
                            title=f"Process Details - {node.name}",
                            content=content,
                            user=self.admin_user,
                            meta_json={
                                'generated_by': 'batch_api',
                                'model': self.openai_model,
                                'temperature': self.temperature,
                                'model_type': self.model_key,  # Store process model type (e.g., 'apqc_pcf')
                                'timestamp': datetime.now().isoformat(),
                                'batch_id': batch.id,
                                'request_id': request_id  # OpenAI request ID for each individual request
                            }
                        )
                        
                        success_count += 1
                    else:
                        print(f"  ❌ Error for node {node_id}: {result['response']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to process node {node_id}: {str(e)}")
                    error_count += 1
                
                if (success_count + error_count) % 100 == 0:
                    print(f"  Progress: {success_count + error_count} processed ({success_count} success, {error_count} errors)")
        
        print(f"\n✅ Processing complete!")
        print(f"   Successfully created: {success_count} documents")
        print(f"   Errors: {error_count}")
        
        return success_count, error_count
    
    def run(self, test_mode=False, test_count=5):
        """Run the batch generation process."""
        print("="*60)
        print("BATCH PROCESS DETAILS GENERATION")
        print("="*60)
        
        # Setup
        self.setup()
        
        # Get leaf nodes
        leaf_nodes = self.get_leaf_nodes()
        
        if test_mode:
            # In test mode, only process specified number of nodes
            leaf_nodes = leaf_nodes[:test_count]
            print(f"⚠️  TEST MODE: Only processing {len(leaf_nodes)} nodes")
            print("   Test nodes:")
            for node in leaf_nodes:
                print(f"     [{node.code}] {node.name} (Level {node.level})")
        
        # Prepare batch file
        batch_file_path = self.prepare_batch_file(leaf_nodes)
        
        # Confirm before submitting
        print(f"\n📊 Ready to submit batch:")
        print(f"   Nodes: {len(leaf_nodes)}")
        print(f"   Estimated cost: ${len(leaf_nodes) * 1500 / 1_000_000 * 3.125:.2f}")
        print(f"   Processing time: ~24 hours")
        
        if test_mode:
            print("\n✅ Auto-proceeding in test mode...")
        else:
            response = input("\nProceed with batch submission? (y/n): ")
            if response.lower() != 'y':
                print("❌ Batch submission cancelled")
                return
        
        # Submit batch
        batch = self.submit_batch(batch_file_path)
        
        if not batch:
            print("❌ Failed to submit batch")
            return
        
        # Save batch ID for reference
        batch_id_file = self.output_dir / 'current_batch_id.txt'
        with open(batch_id_file, 'w') as f:
            f.write(batch.id)
        print(f"💾 Batch ID saved to: {batch_id_file}")
        
        # Poll for completion
        completed_batch = self.poll_batch_status(batch.id)
        
        if completed_batch:
            # Process results
            self.process_results(completed_batch)
        
        print("\n✅ Batch generation complete!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch generate process details')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--count', type=int, default=5, help='Number of nodes to process in test mode')
    
    args = parser.parse_args()
    
    generator = ProcessDetailsBatchGenerator(model_key='apqc_pcf')
    
    if args.test:
        generator.run(test_mode=True, test_count=args.count)
    else:
        generator.run(test_mode=False)