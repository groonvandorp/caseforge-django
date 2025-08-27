#!/usr/bin/env python
"""
Retry batch generation of use case candidates for failed nodes.
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
django.setup()

from batch_generate_usecase_candidates import UsecaseCandidatesBatchGenerator

def main():
    # Read failed node IDs
    failed_ids_file = Path('batch_usecase_candidates/failed_node_ids.txt')
    
    if not failed_ids_file.exists():
        print("❌ Failed node IDs file not found. Run identify_failed_nodes.py first.")
        return
    
    with open(failed_ids_file, 'r') as f:
        failed_node_ids = [int(line.strip()) for line in f if line.strip()]
    
    print(f"🔄 Retrying {len(failed_node_ids)} failed nodes")
    
    # Create generator instance
    generator = UsecaseCandidatesBatchGenerator(model_key='apqc_pcf')
    generator.setup()
    
    # Get failed nodes with their process details
    from core.models import ProcessNode, NodeDocument
    
    failed_nodes_with_details = []
    failed_nodes_without_details = []
    
    failed_nodes = ProcessNode.objects.filter(
        id__in=failed_node_ids,
        model_version=generator.model_version
    ).order_by('id')
    
    for node in failed_nodes:
        # Check if node has process details
        process_details = NodeDocument.objects.filter(
            node=node,
            document_type='process_details'
        ).first()
        
        if process_details:
            failed_nodes_with_details.append((node, process_details))
        else:
            failed_nodes_without_details.append(node)
    
    print(f"✅ Found {len(failed_nodes_with_details)} failed nodes with process details to retry")
    if failed_nodes_without_details:
        print(f"⚠️  {len(failed_nodes_without_details)} failed nodes without process details (will be skipped)")
    
    print("   First 5 nodes with details:")
    for node, _ in failed_nodes_with_details[:5]:
        print(f"     [{node.code}] {node.name}")
    
    if not failed_nodes_with_details:
        print("❌ No failed nodes have process details to retry!")
        return
    
    # Prepare batch file
    batch_file_path = generator.prepare_batch_file(failed_nodes_with_details)
    
    # Confirm before submitting
    print(f"\n📊 Ready to submit retry batch:")
    print(f"   Failed nodes with details: {len(failed_nodes_with_details)}")
    print(f"   Estimated cost: ${len(failed_nodes_with_details) * 1500 / 1_000_000 * 3.125:.2f}")
    print(f"   Processing time: ~24 hours")
    
    response = input("\nProceed with retry batch submission? (y/n): ")
    if response.lower() != 'y':
        print("❌ Retry batch submission cancelled")
        return
    
    # Submit batch
    batch = generator.submit_batch(batch_file_path)
    
    if not batch:
        print("❌ Failed to submit retry batch")
        return
    
    # Update batch ID file  
    batch_id_file = generator.output_dir / 'current_batch_id.txt'
    with open(batch_id_file, 'w') as f:
        f.write(batch.id)
    print(f"💾 Retry batch ID saved to: {batch_id_file}")
    
    # Poll for completion
    completed_batch = generator.poll_batch_status(batch.id)
    
    if completed_batch:
        # Process results
        generator.process_results(completed_batch)
    
    print("\n✅ Retry batch generation complete!")

if __name__ == '__main__':
    main()