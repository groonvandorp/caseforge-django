#!/usr/bin/env python
"""
Generate rich embeddings using process details documents via OpenAI's Batch API.

This enhanced version creates embeddings that include:
1. Basic node information (name, description, hierarchy)
2. Full process details documentation (6000+ tokens of rich content)
3. Use case candidate titles for additional context

This provides much better semantic search quality compared to basic embeddings.
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

from core.models import (
    ProcessNode, ProcessModelVersion, NodeDocument, 
    NodeEmbedding, AdminSettings, NodeUsecaseCandidate
)

class EnhancedEmbeddingGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.model_version = None
        self.embedding_model = "text-embedding-3-small"  # Consistent with existing embeddings
        self.output_dir = Path('embeddings_batch_enhanced')
        self.output_dir.mkdir(exist_ok=True)
        
    def setup(self):
        """Setup OpenAI client and get model version."""
        # Get OpenAI API key from admin settings
        api_key = AdminSettings.get_setting('openai_api_key')
        if not api_key:
            raise ValueError("OpenAI API key not found in admin settings")
        
        self.client = OpenAI(api_key=api_key)
        
        # Get model version
        self.model_version = ProcessModelVersion.objects.filter(
            model__model_key=self.model_key,
            is_current=True
        ).first()
        
        if not self.model_version:
            raise ValueError(f"Model {self.model_key} not found")
        
        print(f"✅ Setup complete")
        print(f"   Process Model: {self.model_version.model.name}")
        print(f"   Embedding Model: {self.embedding_model}")
        
    def get_nodes_with_details(self):
        """Get all nodes, prioritizing those with process details."""
        all_nodes = ProcessNode.objects.filter(model_version=self.model_version)
        
        nodes_data = []
        nodes_with_details = 0
        nodes_with_usecases = 0
        
        for node in all_nodes:
            # Get process details document
            process_details = NodeDocument.objects.filter(
                node=node,
                document_type='process_details'
            ).first()
            
            # Get use case candidates for additional context
            use_cases = NodeUsecaseCandidate.objects.filter(
                node=node,
                meta_json__generated_by='batch_api'
            ).values_list('title', flat=True)[:5]  # Top 5 use case titles
            
            if process_details:
                nodes_with_details += 1
            if use_cases:
                nodes_with_usecases += 1
                
            nodes_data.append({
                'node': node,
                'process_details': process_details,
                'use_cases': list(use_cases)
            })
        
        print(f"✅ Found {len(nodes_data)} total nodes")
        print(f"   Nodes with process details: {nodes_with_details}")
        print(f"   Nodes with use cases: {nodes_with_usecases}")
        
        return nodes_data
    
    def build_embedding_text(self, node_data):
        """Build comprehensive text for embedding from all available data."""
        node = node_data['node']
        process_details = node_data['process_details']
        use_cases = node_data['use_cases']
        
        # Build hierarchical context
        hierarchy = []
        current = node
        while current:
            hierarchy.insert(0, f"[{current.code}] {current.name}")
            current = current.parent
        
        # Start with basic information
        text_parts = [
            f"Process Node: [{node.code}] {node.name}",
            f"Level: {node.level}",
            f"Hierarchy: {' > '.join(hierarchy)}",
        ]
        
        # Add description if available
        if node.description:
            text_parts.append(f"Description: {node.description}")
        
        # Add rich process details if available (MOST IMPORTANT)
        if process_details:
            # Truncate to reasonable length for embeddings (8000 tokens ~ 32000 chars)
            content = process_details.content[:32000]
            text_parts.append(f"Process Details:\n{content}")
        
        # Add use case titles for additional context
        if use_cases:
            text_parts.append(f"Related Use Cases: {'; '.join(use_cases)}")
        
        # Join all parts
        full_text = "\n\n".join(text_parts)
        
        # Ensure we don't exceed embedding model limits (8191 tokens)
        # Rough estimate: 1 token = 4 chars
        max_chars = 30000  # Conservative limit
        if len(full_text) > max_chars:
            # Prioritize process details over other content
            if process_details:
                # Keep hierarchy and truncated process details
                truncated_details = process_details.content[:max_chars - 1000]
                full_text = "\n\n".join([
                    text_parts[0],  # Node name
                    text_parts[1],  # Level
                    text_parts[2],  # Hierarchy
                    f"Process Details:\n{truncated_details}"
                ])
            else:
                full_text = full_text[:max_chars]
        
        return full_text
    
    def prepare_batch_file(self, nodes_data):
        """Prepare the JSONL batch file for OpenAI embeddings."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file_path = self.output_dir / f'batch_input_embeddings_{self.model_key}_{timestamp}.jsonl'
        
        with open(batch_file_path, 'w') as f:
            for i, node_data in enumerate(nodes_data):
                node = node_data['node']
                embedding_text = self.build_embedding_text(node_data)
                
                # Create the batch request object
                request = {
                    "custom_id": f"node_{node.id}_{node.code}",
                    "method": "POST",
                    "url": "/v1/embeddings",
                    "body": {
                        "model": self.embedding_model,
                        "input": embedding_text
                    }
                }
                
                f.write(json.dumps(request) + '\n')
                
                if (i + 1) % 500 == 0:
                    print(f"  Processed {i + 1}/{len(nodes_data)} nodes...")
        
        print(f"✅ Batch file created: {batch_file_path}")
        print(f"   Total requests: {len(nodes_data)}")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """Submit the batch to OpenAI."""
        print("\n🚀 Submitting embeddings batch to OpenAI...")
        
        with open(batch_file_path, 'rb') as f:
            batch_file = self.client.files.create(
                file=f,
                purpose="batch"
            )
        
        batch = self.client.batches.create(
            input_file_id=batch_file.id,
            endpoint="/v1/embeddings",
            completion_window="24h",
            metadata={
                "model_key": self.model_key,
                "type": "enhanced_embeddings_with_details"
            }
        )
        
        print(f"✅ Batch submitted")
        print(f"   Batch ID: {batch.id}")
        print(f"   Status: {batch.status}")
        
        # Save batch ID for monitoring
        batch_id_file = self.output_dir / 'current_batch_id.txt'
        with open(batch_id_file, 'w') as f:
            f.write(batch.id)
        print(f"   Batch ID saved to: {batch_id_file}")
        
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
                if batch.errors:
                    print(f"   Errors: {batch.errors}")
                return None
            
            time.sleep(check_interval)
    
    def process_results(self, batch):
        """Process the batch results and store embeddings in database."""
        print("\n📥 Processing embedding results...")
        
        # Download the output file
        output_file = self.client.files.content(batch.output_file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f'batch_output_embeddings_{self.model_key}_{timestamp}.jsonl'
        
        with open(output_path, 'wb') as f:
            f.write(output_file.read())
        
        print(f"✅ Results downloaded to: {output_path}")
        
        # Process each result
        success_count = 0
        error_count = 0
        updated_count = 0
        created_count = 0
        
        with open(output_path, 'r') as f:
            for line in f:
                result = json.loads(line)
                custom_id = result['custom_id']
                
                # Extract node ID from custom_id
                node_id = int(custom_id.split('_')[1])
                
                try:
                    if result['response']['status_code'] == 200:
                        embedding_vector = result['response']['body']['data'][0]['embedding']
                        
                        # Get the node
                        node = ProcessNode.objects.get(id=node_id)
                        
                        # Update or create embedding
                        embedding, created = NodeEmbedding.objects.update_or_create(
                            node=node,
                            defaults={
                                'embedding_vector': embedding_vector,
                                'embedding_model': self.embedding_model,
                            }
                        )
                        
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                        
                        success_count += 1
                    else:
                        print(f"  ❌ Error for node {node_id}: {result['response']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to process node {node_id}: {str(e)}")
                    error_count += 1
                
                if (success_count + error_count) % 500 == 0:
                    print(f"  Progress: {success_count + error_count} processed ({success_count} success, {error_count} errors)")
        
        print(f"\n✅ Processing complete!")
        print(f"   Created: {created_count} new embeddings")
        print(f"   Updated: {updated_count} existing embeddings")
        print(f"   Errors: {error_count}")
        print(f"\n🎯 Embeddings now include rich process details for superior search quality!")
        
        return success_count, error_count
    
    def run(self, test_mode=False, test_count=10):
        """Run the enhanced embedding generation process."""
        print("="*70)
        print("ENHANCED EMBEDDINGS GENERATION WITH PROCESS DETAILS")
        print("="*70)
        
        # Setup
        self.setup()
        
        # Get nodes with their details
        nodes_data = self.get_nodes_with_details()
        
        if test_mode:
            # In test mode, only process specified number of nodes with details
            test_nodes = [n for n in nodes_data if n['process_details']][:test_count]
            if not test_nodes:
                test_nodes = nodes_data[:test_count]
            nodes_data = test_nodes
            print(f"\n⚠️  TEST MODE: Only processing {len(nodes_data)} nodes")
        
        # Prepare batch file
        batch_file_path = self.prepare_batch_file(nodes_data)
        
        # Estimate cost (embeddings are much cheaper than text generation)
        # text-embedding-3-small: $0.02 per 1M tokens
        # Assume average 2000 tokens per embedding
        estimated_cost = len(nodes_data) * 2000 / 1_000_000 * 0.02
        
        # Confirm before submitting
        print(f"\n📊 Ready to submit embeddings batch:")
        print(f"   Nodes: {len(nodes_data)}")
        print(f"   Estimated cost: ${estimated_cost:.2f}")
        print(f"   Processing time: ~1-2 hours")
        print(f"   Quality improvement: Embeddings will include full process documentation")
        
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
        
        # Poll for completion
        completed_batch = self.poll_batch_status(batch.id)
        
        if completed_batch:
            # Process results
            self.process_results(completed_batch)
        
        print("\n✅ Enhanced embedding generation complete!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate enhanced embeddings with process details')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--count', type=int, default=10, help='Number of nodes to process in test mode')
    
    args = parser.parse_args()
    
    generator = EnhancedEmbeddingGenerator(model_key='apqc_pcf')
    generator.run(test_mode=args.test, test_count=args.count)