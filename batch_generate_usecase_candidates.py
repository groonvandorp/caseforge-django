#!/usr/bin/env python
"""
Batch generation of AI usecase candidates for all leaf nodes using OpenAI Batch API.

This script:
1. Uses existing process details documents as context
2. Prepares a JSONL file with all requests
3. Submits to OpenAI batch API
4. Polls for completion
5. Stores results in database as NodeUsecaseCandidate records

Prerequisites: Process details must exist for nodes (run batch_generate_process_details.py first)
"""

import os
import sys
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import django
from openai import OpenAI

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from core.models import ProcessNode, ProcessModelVersion, NodeDocument, NodeUsecaseCandidate, AdminSettings
from django.contrib.auth import get_user_model

User = get_user_model()

class UsecaseCandidatesBatchGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.admin_user = None
        self.model_version = None
        self.openai_model = None
        self.output_dir = Path('batch_usecase_candidates')
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
        
        # Get temperature (defaults to 1.0 for GPT-5 if not specified)
        self.temperature = float(AdminSettings.get_setting('openai_temperature', '1.0'))
        
        # Get gruhno user for document creation
        self.admin_user = User.objects.filter(username='gruhno').first()
        if not self.admin_user:
            raise ValueError("User 'gruhno' not found")
        
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
        
    def get_nodes_with_process_details(self):
        """Get all leaf nodes that have process details documents."""
        all_nodes = ProcessNode.objects.filter(model_version=self.model_version)
        
        nodes_with_details = []
        nodes_without_details = []
        
        for node in all_nodes:
            if node.is_leaf:
                # Check if node has process details
                process_details = NodeDocument.objects.filter(
                    node=node,
                    document_type='process_details'
                ).first()
                
                if process_details:
                    nodes_with_details.append((node, process_details))
                else:
                    nodes_without_details.append(node)
        
        print(f"✅ Found {len(nodes_with_details)} leaf nodes with process details")
        if nodes_without_details:
            print(f"⚠️  {len(nodes_without_details)} leaf nodes without process details (will be skipped)")
            print("   Run batch_generate_process_details.py first for complete coverage")
        
        return nodes_with_details
    
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
    
    def create_usecase_prompt(self, node, process_details_doc):
        """Create the prompt for generating usecase candidates."""
        hierarchy_context = self.build_hierarchical_context(node)
        
        prompt = f"""Based on the detailed process documentation below, generate innovative use case candidates for process improvement, automation, and optimization.

Process Hierarchy:
{hierarchy_context}

Current Process:
[{node.code}] {node.name}
Level: {node.level}

Process Details:
{process_details_doc.content}

Generate 6-10 diverse use case candidates that could improve this process. For each use case candidate, provide:

## Use Case Title
A clear, actionable title (max 80 characters)

## Description  
Comprehensive description of the use case (300-500 words) covering:
- What the solution does and how it works
- Key features and capabilities
- How it integrates with existing processes and systems
- Step-by-step workflow or user experience
- Expected outcomes and benefits for stakeholders

## Impact Assessment
- Process efficiency improvements
- Cost reduction potential
- Quality improvements
- Risk mitigation
- Customer experience enhancements

## Implementation Complexity
Rate as Low/Medium/High and explain key complexity factors

## Technology Requirements
List key technologies, tools, or systems needed

## Success Metrics
Specific KPIs to measure success

## Implementation Timeline
Estimated timeline and key milestones

Format as JSON array with this structure:
```json
[
  {{
    "title": "Use Case Title",
    "description": "Detailed description...",
    "impact_assessment": "Impact details...",
    "complexity_score": "Medium",
    "complexity_details": "Complexity factors...",
    "technology_requirements": "Technology details...",
    "success_metrics": "KPIs and metrics...",
    "implementation_timeline": "Timeline details...",
    "category": "automation|optimization|digitization|analytics|integration",
    "estimated_roi": "High|Medium|Low",
    "risk_level": "Low|Medium|High"
  }}
]
```

Focus on practical, implementable use cases that align with modern business process improvement trends such as:
- Process automation and AI integration
- Digital transformation initiatives  
- Data analytics and insights
- Customer experience optimization
- Operational efficiency gains
- Risk reduction and compliance
- Cost optimization strategies

IMPORTANT WRITING GUIDELINES:
- When using technical abbreviations or acronyms, define them on first use (e.g., "Project Portfolio Management (PPM)" instead of just "PPM")
- Write descriptions that are accessible to business stakeholders, not just technical experts
- Use clear, professional language that explains concepts rather than assuming technical knowledge
- For commonly used business terms, provide brief context where helpful
"""

        return prompt
    
    def prepare_batch_file(self, nodes_with_details):
        """Prepare the JSONL batch file for OpenAI."""
        batch_file_path = self.output_dir / f'batch_input_usecases_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
        with open(batch_file_path, 'w') as f:
            for i, (node, process_details_doc) in enumerate(nodes_with_details):
                prompt = self.create_usecase_prompt(node, process_details_doc)
                
                # Create the batch request object
                request = {
                    "custom_id": f"usecases_node_{node.id}_{node.code}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a business process improvement expert specializing in identifying automation opportunities, digital transformation initiatives, and operational optimization use cases. Generate practical, implementable use case candidates with clear business value."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_completion_tokens": 15000,   # Increased to handle longer process docs
                        "response_format": {"type": "json_object"}  # Ensure JSON response
                    }
                }
                
                f.write(json.dumps(request) + '\n')
                
                if (i + 1) % 100 == 0:
                    print(f"  Processed {i + 1}/{len(nodes_with_details)} nodes...")
        
        print(f"✅ Batch file created: {batch_file_path}")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """Submit the batch to OpenAI."""
        print("\n🚀 Submitting usecase candidates batch to OpenAI...")
        
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
                "type": "usecase_candidates_generation"
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
        print("\n📥 Processing usecase candidates results...")
        
        # Download the output file
        output_file = self.client.files.content(batch.output_file_id)
        output_path = self.output_dir / f'batch_output_usecases_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
        with open(output_path, 'wb') as f:
            f.write(output_file.read())
        
        print(f"✅ Results downloaded to: {output_path}")
        
        # Process each result
        success_count = 0
        error_count = 0
        total_usecases_created = 0
        
        with open(output_path, 'r') as f:
            for line in f:
                result = json.loads(line)
                custom_id = result['custom_id']
                
                # Extract node ID from custom_id and OpenAI request ID
                node_id = int(custom_id.split('_')[2])
                request_id = result['response'].get('request_id')
                
                try:
                    if result['response']['status_code'] == 200:
                        content = result['response']['body']['choices'][0]['message']['content']
                        
                        # Parse JSON response
                        try:
                            usecases_data = json.loads(content)
                        except json.JSONDecodeError:
                            print(f"  ❌ Invalid JSON response for node {node_id}")
                            error_count += 1
                            continue
                        
                        # Get the node
                        node = ProcessNode.objects.get(id=node_id)
                        
                        # Delete existing AI-generated usecase candidates for this node
                        NodeUsecaseCandidate.objects.filter(
                            node=node,
                            meta_json__generated_by='batch_api'
                        ).delete()
                        
                        # Create usecase candidates
                        node_usecases_count = 0
                        # Extract use_cases array from the response
                        use_cases = usecases_data.get('use_cases', usecases_data)  # Fallback if it's already an array
                        if not isinstance(use_cases, list):
                            print(f"  ❌ Invalid use_cases format for node {node_id}: expected array")
                            error_count += 1
                            continue
                        
                        for i, usecase_data in enumerate(use_cases, 1):
                            try:
                                # Generate readable candidate_uid (e.g., 1.3.5-UC01)
                                candidate_uid = f"{node.code}-UC{i:02d}"
                                
                                NodeUsecaseCandidate.objects.create(
                                    node=node,
                                    candidate_uid=candidate_uid,
                                    title=usecase_data.get('title', 'Untitled Use Case')[:200],
                                    description=usecase_data.get('description', ''),
                                    impact_assessment=usecase_data.get('impact_assessment', ''),
                                    complexity_score=self.map_complexity(usecase_data.get('complexity_score', 'Medium')),
                                    user=self.admin_user,
                                    meta_json={
                                        'generated_by': 'batch_api',
                                        'model': self.openai_model,
                                        'temperature': self.temperature,
                                        'model_type': self.model_key,  # Store process model type (e.g., 'apqc_pcf')
                                        'timestamp': datetime.now().isoformat(),
                                        'batch_id': batch.id,
                                        'request_id': request_id,  # OpenAI request ID for each individual request
                                        'complexity_details': usecase_data.get('complexity_details', ''),
                                        'technology_requirements': usecase_data.get('technology_requirements', ''),
                                        'success_metrics': usecase_data.get('success_metrics', ''),
                                        'implementation_timeline': usecase_data.get('implementation_timeline', ''),
                                        'category': usecase_data.get('category', 'optimization'),
                                        'estimated_roi': usecase_data.get('estimated_roi', 'Medium'),
                                        'risk_level': usecase_data.get('risk_level', 'Medium')
                                    }
                                )
                                node_usecases_count += 1
                                total_usecases_created += 1
                                
                            except Exception as e:
                                print(f"    ❌ Failed to create usecase for node {node_id}: {str(e)}")
                                continue
                        
                        print(f"  ✅ Node {node.code}: Created {node_usecases_count} use cases")
                        success_count += 1
                        
                    else:
                        print(f"  ❌ API Error for node {node_id}: {result['response']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to process node {node_id}: {str(e)}")
                    error_count += 1
                
                if (success_count + error_count) % 50 == 0:
                    print(f"  Progress: {success_count + error_count} processed ({success_count} success, {error_count} errors)")
        
        print(f"\n✅ Processing complete!")
        print(f"   Successfully processed: {success_count} nodes")
        print(f"   Total use cases created: {total_usecases_created}")
        print(f"   Errors: {error_count}")
        print(f"   Average use cases per node: {total_usecases_created/success_count:.1f}" if success_count > 0 else "")
        
        return success_count, error_count, total_usecases_created
    
    def map_complexity(self, complexity_str):
        """Map complexity string to numeric score."""
        complexity_map = {
            'Low': 1,
            'Medium': 2,
            'High': 3
        }
        return complexity_map.get(complexity_str, 2)
    
    def run(self, test_mode=False, test_count=3):
        """Run the batch usecase candidates generation process."""
        print("="*70)
        print("BATCH USECASE CANDIDATES GENERATION")
        print("="*70)
        
        # Setup
        self.setup()
        
        # Get nodes with process details
        nodes_with_details = self.get_nodes_with_process_details()
        
        if not nodes_with_details:
            print("\n❌ No nodes with process details found!")
            print("   Run batch_generate_process_details.py first to generate process details.")
            return
        
        if test_mode:
            # In test mode, only process specified number of nodes
            nodes_with_details = nodes_with_details[:test_count]
            print(f"\n⚠️  TEST MODE: Only processing {len(nodes_with_details)} nodes")
            print("   Test nodes:")
            for node, _ in nodes_with_details:
                print(f"     [{node.code}] {node.name} (Level {node.level})")
        
        # Prepare batch file
        batch_file_path = self.prepare_batch_file(nodes_with_details)
        
        # Confirm before submitting
        estimated_usecases = len(nodes_with_details) * 6  # Average 6 use cases per node
        estimated_cost = len(nodes_with_details) * 2500 / 1_000_000 * 10.0  # Rough estimate
        
        print(f"\n📊 Ready to submit usecase candidates batch:")
        print(f"   Nodes: {len(nodes_with_details)}")
        print(f"   Estimated use cases: ~{estimated_usecases}")
        print(f"   Estimated cost: ${estimated_cost:.2f}")
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
        
        print("\n✅ Usecase candidates batch generation complete!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch generate usecase candidates')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--count', type=int, default=3, help='Number of nodes to process in test mode')
    
    args = parser.parse_args()
    
    generator = UsecaseCandidatesBatchGenerator(model_key='apqc_pcf')
    
    if args.test:
        generator.run(test_mode=True, test_count=args.count)
    else:
        generator.run(test_mode=False)