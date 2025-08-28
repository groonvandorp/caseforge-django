#!/usr/bin/env python
"""
Generate embeddings for AI use case candidates via OpenAI's Batch API.

This creates searchable embeddings for all use case candidates, enabling:
- Search by use case title and description
- Search by impact assessment and complexity
- Search by technology requirements
- Search by implementation timeline
- Cross-referencing with process nodes
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

from django.db import connection
from core.models import (
    ProcessNode, ProcessModelVersion, NodeUsecaseCandidate,
    AdminSettings
)

class UsecaseEmbeddingGenerator:
    def __init__(self, model_key='apqc_pcf'):
        self.model_key = model_key
        self.client = None
        self.model_version = None
        self.embedding_model = "text-embedding-3-small"
        self.output_dir = Path('embeddings_batch_usecases')
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
        
    def get_usecase_candidates(self):
        """Get all AI-generated use case candidates."""
        usecases = NodeUsecaseCandidate.objects.filter(
            node__model_version=self.model_version,
            meta_json__generated_by='batch_api'  # Only AI-generated ones
        ).select_related('node', 'node__parent')
        
        print(f"✅ Found {usecases.count()} AI-generated use case candidates")
        
        return usecases
    
    def build_usecase_embedding_text(self, usecase):
        """Build comprehensive text for use case embedding."""
        node = usecase.node
        
        # Build hierarchical context
        hierarchy = []
        current = node
        while current:
            hierarchy.insert(0, f"[{current.code}] {current.name}")
            current = current.parent
        
        # Get metadata from meta_json
        meta = usecase.meta_json or {}
        
        # Build comprehensive text for embedding
        text_parts = [
            f"Use Case: {usecase.title}",
            f"Process: [{node.code}] {node.name}",
            f"Hierarchy: {' > '.join(hierarchy)}",
            f"Description: {usecase.description}",
        ]
        
        # Add impact assessment
        if usecase.impact_assessment:
            text_parts.append(f"Impact: {usecase.impact_assessment}")
        
        # Add complexity score
        if usecase.complexity_score:
            text_parts.append(f"Complexity: {usecase.complexity_score}")
        
        # Add metadata fields if available
        if meta.get('complexity_details'):
            text_parts.append(f"Complexity Details: {meta['complexity_details']}")
            
        if meta.get('technology_requirements'):
            text_parts.append(f"Technology: {meta['technology_requirements']}")
            
        if meta.get('success_metrics'):
            text_parts.append(f"Success Metrics: {meta['success_metrics']}")
            
        if meta.get('implementation_timeline'):
            text_parts.append(f"Timeline: {meta['implementation_timeline']}")
            
        if meta.get('category'):
            text_parts.append(f"Category: {meta['category']}")
            
        if meta.get('estimated_roi'):
            text_parts.append(f"ROI: {meta['estimated_roi']}")
            
        if meta.get('risk_level'):
            text_parts.append(f"Risk: {meta['risk_level']}")
        
        # Join all parts
        full_text = "\n\n".join(text_parts)
        
        # Ensure we don't exceed embedding model limits
        max_chars = 30000  # Conservative limit for text-embedding-3-small
        if len(full_text) > max_chars:
            # Prioritize title, description, and impact
            essential_parts = text_parts[:4]  # Title, Process, Hierarchy, Description
            if usecase.impact_assessment:
                essential_parts.append(f"Impact: {usecase.impact_assessment}")
            full_text = "\n\n".join(essential_parts)
            if len(full_text) > max_chars:
                full_text = full_text[:max_chars]
        
        return full_text
    
    def prepare_batch_file(self, usecases):
        """Prepare the JSONL batch file for OpenAI embeddings."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file_path = self.output_dir / f'batch_input_usecase_embeddings_{self.model_key}_{timestamp}.jsonl'
        
        with open(batch_file_path, 'w') as f:
            for i, usecase in enumerate(usecases):
                embedding_text = self.build_usecase_embedding_text(usecase)
                
                # Create the batch request object
                request = {
                    "custom_id": f"usecase_{usecase.id}_{usecase.candidate_uid}",
                    "method": "POST",
                    "url": "/v1/embeddings",
                    "body": {
                        "model": self.embedding_model,
                        "input": embedding_text
                    }
                }
                
                f.write(json.dumps(request) + '\n')
                
                if (i + 1) % 1000 == 0:
                    print(f"  Processed {i + 1}/{usecases.count()} use cases...")
        
        print(f"✅ Batch file created: {batch_file_path}")
        print(f"   Total requests: {usecases.count()}")
        return batch_file_path
    
    def submit_batch(self, batch_file_path):
        """Submit the batch to OpenAI."""
        print("\n🚀 Submitting use case embeddings batch to OpenAI...")
        
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
                "type": "usecase_embeddings"
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
        """Process the batch results and store embeddings."""
        print("\n📥 Processing use case embedding results...")
        
        # First, ensure the UsecaseEmbedding table exists
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usecase_embedding (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usecase_id INTEGER UNIQUE REFERENCES node_usecase_candidate(id),
                    embedding_vector TEXT,
                    embedding_model VARCHAR(100),
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_usecase_embedding_created 
                ON usecase_embedding(created_at)
            """)
        
        # Download the output file
        output_file = self.client.files.content(batch.output_file_id)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f'batch_output_usecase_embeddings_{self.model_key}_{timestamp}.jsonl'
        
        with open(output_path, 'wb') as f:
            f.write(output_file.read())
        
        print(f"✅ Results downloaded to: {output_path}")
        
        # Process each result
        success_count = 0
        error_count = 0
        created_count = 0
        updated_count = 0
        
        with open(output_path, 'r') as f:
            for line in f:
                result = json.loads(line)
                custom_id = result['custom_id']
                
                # Extract usecase ID from custom_id
                usecase_id = int(custom_id.split('_')[1])
                
                try:
                    if result['response']['status_code'] == 200:
                        embedding_vector = result['response']['body']['data'][0]['embedding']
                        
                        # Store embedding directly in database
                        with connection.cursor() as cursor:
                            cursor.execute("""
                                INSERT OR REPLACE INTO usecase_embedding 
                                (usecase_id, embedding_vector, embedding_model, created_at, updated_at)
                                VALUES (?, ?, ?, datetime('now'), datetime('now'))
                            """, [usecase_id, json.dumps(embedding_vector), self.embedding_model])
                            
                            if cursor.rowcount > 0:
                                created_count += 1
                        
                        success_count += 1
                    else:
                        print(f"  ❌ Error for usecase {usecase_id}: {result['response']}")
                        error_count += 1
                        
                except Exception as e:
                    print(f"  ❌ Failed to process usecase {usecase_id}: {str(e)}")
                    error_count += 1
                
                if (success_count + error_count) % 1000 == 0:
                    print(f"  Progress: {success_count + error_count} processed ({success_count} success, {error_count} errors)")
        
        print(f"\n✅ Processing complete!")
        print(f"   Embeddings created: {created_count}")
        print(f"   Total successful: {success_count}")
        print(f"   Errors: {error_count}")
        print(f"\n🎯 Use case candidates are now searchable with embeddings!")
        
        return success_count, error_count
    
    def run(self, test_mode=False, test_count=10):
        """Run the use case embedding generation process."""
        print("="*70)
        print("USE CASE EMBEDDINGS GENERATION")
        print("="*70)
        
        # Setup
        self.setup()
        
        # Get use case candidates
        usecases = self.get_usecase_candidates()
        
        if test_mode:
            usecases = usecases[:test_count]
            print(f"\n⚠️  TEST MODE: Only processing {usecases.count()} use cases")
        
        # Prepare batch file
        batch_file_path = self.prepare_batch_file(usecases)
        
        # Estimate cost
        # text-embedding-3-small: $0.02 per 1M tokens
        # Assume average 500 tokens per use case
        estimated_cost = usecases.count() * 500 / 1_000_000 * 0.02
        
        # Confirm before submitting
        print(f"\n📊 Ready to submit use case embeddings batch:")
        print(f"   Use cases: {usecases.count()}")
        print(f"   Estimated cost: ${estimated_cost:.2f}")
        print(f"   Processing time: ~30-60 minutes")
        
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
        
        print("\n✅ Use case embedding generation complete!")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate embeddings for use case candidates')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    parser.add_argument('--count', type=int, default=10, help='Number of use cases to process in test mode')
    
    args = parser.parse_args()
    
    generator = UsecaseEmbeddingGenerator(model_key='apqc_pcf')
    generator.run(test_mode=args.test, test_count=args.count)