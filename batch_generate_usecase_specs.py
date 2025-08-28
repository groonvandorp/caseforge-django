#!/usr/bin/env python
"""
Batch generation of detailed use case specifications using OpenAI Batch API.

This script:
1. Uses existing process details and usecase candidates as comprehensive context
2. Prepares a JSONL file with all requests for detailed specifications
3. Submits to OpenAI batch API
4. Polls for completion
5. Stores results in database as NodeDocument records with document_type='usecase_spec'

Prerequisites: 
- Process details must exist (from batch_generate_process_details.py)
- Usecase candidates must exist (from batch_generate_usecase_candidates.py)
"""

import os
import sys
import json
import time
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

class UsecaseSpecsBatchGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.admin_user = None
        self.model_version = None
        self.openai_model = None
        self.output_dir = Path('batch_usecase_specs')
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
    
    def get_nodes_with_full_context(self):
        """Get nodes that have both process details and usecase candidates."""
        all_nodes = ProcessNode.objects.filter(model_version=self.model_version)
        
        nodes_with_full_context = []
        nodes_missing_context = []
        
        for node in all_nodes:
            if node.is_leaf:
                # Check for process details
                process_details = NodeDocument.objects.filter(
                    node=node,
                    document_type='process_details'
                ).first()
                
                # Check for usecase candidates
                usecase_candidates = NodeUsecaseCandidate.objects.filter(node=node)
                
                if process_details and usecase_candidates.exists():
                    nodes_with_full_context.append({
                        'node': node,
                        'process_details': process_details,
                        'usecase_candidates': list(usecase_candidates)
                    })
                else:
                    missing = []
                    if not process_details:
                        missing.append("process_details")
                    if not usecase_candidates.exists():
                        missing.append("usecase_candidates")
                    nodes_missing_context.append({
                        'node': node,
                        'missing': missing
                    })
        
        print(f"✅ Found {len(nodes_with_full_context)} nodes with complete context")
        if nodes_missing_context:
            print(f"⚠️  {len(nodes_missing_context)} nodes missing context:")
            missing_details = sum(1 for n in nodes_missing_context if 'process_details' in n['missing'])
            missing_candidates = sum(1 for n in nodes_missing_context if 'usecase_candidates' in n['missing'])
            print(f"   - Missing process details: {missing_details}")
            print(f"   - Missing usecase candidates: {missing_candidates}")
        
        return nodes_with_full_context
    
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
    
    def create_usecase_spec_prompt(self, node_data):
        """Create the prompt for generating detailed use case specifications."""
        node = node_data['node']
        process_details = node_data['process_details']
        usecase_candidates = node_data['usecase_candidates']
        
        hierarchy_context = self.build_hierarchical_context(node)
        
        # Format usecase candidates
        candidates_text = ""
        for i, candidate in enumerate(usecase_candidates, 1):
            candidates_text += f"\n## Use Case Candidate {i}: {candidate.title}\n"
            candidates_text += f"Description: {candidate.description}\n"
            candidates_text += f"Impact Assessment: {candidate.impact_assessment}\n"
            candidates_text += f"Complexity: {candidate.get_complexity_display()}\n"
            
            # Add metadata if available
            if candidate.meta_json:
                meta = candidate.meta_json
                if 'technology_requirements' in meta:
                    candidates_text += f"Technology: {meta['technology_requirements']}\n"
                if 'success_metrics' in meta:
                    candidates_text += f"Success Metrics: {meta['success_metrics']}\n"
                if 'implementation_timeline' in meta:
                    candidates_text += f"Timeline: {meta['implementation_timeline']}\n"
                if 'category' in meta:
                    candidates_text += f"Category: {meta['category']}\n"
        
        prompt = f"""Based on the comprehensive process documentation and use case candidates below, create a detailed use case specification document that synthesizes the best opportunities into actionable implementation plans.

Process Hierarchy:
{hierarchy_context}

Current Process:
[{node.code}] {node.name}
Level: {node.level}

Process Details:
{process_details.content}

Use Case Candidates:
{candidates_text}

Create a comprehensive use case specification document in markdown format that includes:

# Use Case Specification: {node.name}

## Executive Summary
- Brief overview of the process optimization opportunity
- Key business drivers and strategic alignment
- Expected outcomes and value proposition

## Process Context
- Current state analysis based on the process details
- Key stakeholders and their roles
- Process pain points and improvement opportunities
- Integration points with other processes

## Recommended Use Cases
Select and detail the 2-3 most promising use case candidates, providing for each:

### Use Case 1: [Title]
**Priority:** High/Medium/Low
**Category:** Automation/Optimization/Digitization/Analytics/Integration

**Business Case:**
- Problem statement
- Proposed solution approach
- Business value and ROI potential
- Risk assessment and mitigation

**Functional Requirements:**
- Detailed functional specifications
- User stories and acceptance criteria
- Data requirements and flow
- Integration requirements

**Technical Approach:**
- Technology stack recommendations
- Architecture considerations
- Security and compliance requirements
- Scalability considerations

**Implementation Plan:**
- Phase-by-phase delivery approach
- Resource requirements
- Timeline and milestones
- Dependencies and prerequisites

**Success Criteria:**
- Key performance indicators (KPIs)
- Success metrics and targets
- Measurement approach
- Benefits realization timeline

## Implementation Considerations
- Organizational change management
- Training and adoption requirements
- Governance and oversight
- Risk management approach

## Roadmap and Next Steps
- Immediate next actions
- Short-term milestones (0-6 months)
- Medium-term objectives (6-18 months)
- Long-term vision (18+ months)

## Appendices
- Stakeholder analysis
- Cost-benefit analysis summary
- Technical reference materials

Focus on creating actionable, enterprise-ready specifications that could be handed directly to implementation teams. Ensure business value is clearly articulated and technical approaches are practical and well-defined."""

        return prompt
    
    def prepare_batch_file(self, nodes_with_context):
        """Prepare the JSONL batch file for OpenAI."""
        batch_file_path = self.output_dir / f'batch_input_specs_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
        with open(batch_file_path, 'w') as f:
            for i, node_data in enumerate(nodes_with_context):
                node = node_data['node']
                prompt = self.create_usecase_spec_prompt(node_data)
                
                # Create the batch request object
                request = {
                    "custom_id": f"spec_node_{node.id}_{node.code}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a senior business analyst and solution architect specializing in digital transformation and process improvement. Create comprehensive, enterprise-grade use case specifications that are immediately actionable for implementation teams. Focus on practical solutions with clear business value and technical feasibility."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_completion_tokens": 10000  # More tokens for comprehensive specifications
                    }
                }
                
                f.write(json.dumps(request) + '\n')
                
                if (i + 1) % 50 == 0:
                    print(f"  Processed {i + 1}/{len(nodes_with_context)} nodes...")
        
        print(f"✅ Batch file created: {batch_file_path}")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """Submit the batch to OpenAI."""
        print("\n🚀 Submitting use case specifications batch to OpenAI...")
        
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
                "type": "usecase_specs_generation"
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
        print("\n📥 Processing use case specifications results...")
        
        # Download the output file
        output_file = self.client.files.content(batch.output_file_id)
        output_path = self.output_dir / f'batch_output_specs_{self.model_key}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jsonl'
        
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
                node_id = int(custom_id.split('_')[2])
                request_id = result['response'].get('request_id')
                
                try:
                    if result['response']['status_code'] == 200:
                        content = result['response']['body']['choices'][0]['message']['content']
                        
                        # Get the node
                        node = ProcessNode.objects.get(id=node_id)
                        
                        # Delete existing usecase_spec document if exists
                        NodeDocument.objects.filter(
                            node=node,
                            document_type='usecase_spec'
                        ).delete()
                        
                        # Create new specification document
                        NodeDocument.objects.create(
                            node=node,
                            document_type='usecase_spec',
                            title=f"Use Case Specification - {node.name}",
                            content=content,
                            user=self.admin_user,
                            meta_json={
                                'generated_by': 'batch_api',
                                'model': self.openai_model,
                                'temperature': self.temperature,
                                'model_type': self.model_key,  # Store process model type (e.g., 'apqc_pcf')
                                'timestamp': datetime.now().isoformat(),
                                'batch_id': batch.id,
                                'request_id': request_id,  # OpenAI request ID for each individual request
                                'source': 'process_details_and_candidates'
                            }
                        )
                        
                        print(f"  ✅ Created spec for [{node.code}] {node.name}")
                        success_count += 1
                        
                    else:
                        print(f"  ❌ API Error for node {node_id}: {result['response']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to process node {node_id}: {str(e)}")
                    error_count += 1
                
                if (success_count + error_count) % 25 == 0:
                    print(f"  Progress: {success_count + error_count} processed ({success_count} success, {error_count} errors)")
        
        print(f"\n✅ Processing complete!")
        print(f"   Successfully created: {success_count} use case specifications")
        print(f"   Errors: {error_count}")
        
        return success_count, error_count
    
    def run(self, test_mode=False, test_count=3):
        """Run the batch use case specifications generation process."""
        print("="*70)
        print("BATCH USE CASE SPECIFICATIONS GENERATION")
        print("="*70)
        
        # Setup
        self.setup()
        
        # Get nodes with complete context
        nodes_with_context = self.get_nodes_with_full_context()
        
        if not nodes_with_context:
            print("\n❌ No nodes with complete context found!")
            print("   Ensure both process details and usecase candidates exist.")
            print("   Run batch_generate_process_details.py and batch_generate_usecase_candidates.py first.")
            return
        
        if test_mode:
            # In test mode, only process specified number of nodes
            nodes_with_context = nodes_with_context[:test_count]
            print(f"\n⚠️  TEST MODE: Only processing {len(nodes_with_context)} nodes")
            print("   Test nodes:")
            for node_data in nodes_with_context:
                node = node_data['node']
                candidate_count = len(node_data['usecase_candidates'])
                print(f"     [{node.code}] {node.name} ({candidate_count} candidates)")
        
        # Prepare batch file
        batch_file_path = self.prepare_batch_file(nodes_with_context)
        
        # Confirm before submitting
        estimated_cost = len(nodes_with_context) * 3500 / 1_000_000 * 10.0  # Higher token usage
        
        print(f"\n📊 Ready to submit use case specifications batch:")
        print(f"   Nodes: {len(nodes_with_context)}")
        print(f"   Estimated cost: ${estimated_cost:.2f}")
        print(f"   Processing time: ~24 hours")
        print(f"   Output: Comprehensive enterprise-grade specifications")
        
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
        
        print("\n✅ Use case specifications batch generation complete!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Batch generate use case specifications')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--count', type=int, default=3, help='Number of nodes to process in test mode')
    
    args = parser.parse_args()
    
    generator = UsecaseSpecsBatchGenerator(model_key='apqc_pcf')
    
    if args.test:
        generator.run(test_mode=True, test_count=args.count)
    else:
        generator.run(test_mode=False)