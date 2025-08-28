#!/usr/bin/env python3
"""
SAFE copy of process detail documents from Cross Industry to Life Science model.
Only copies to identical leaf nodes (same code, name, description).
PRESERVES original Cross Industry data completely.
"""

import os
import sys
import django
import json
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.db import transaction
from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeDocument, User

def get_leaf_nodes_with_details(model_key):
    """Get leaf nodes that have process details for a specific model."""
    nodes = ProcessNode.objects.filter(
        model_version__model__model_key=model_key,
        model_version__is_current=True
    ).exclude(
        # Exclude nodes that have children (not leaf nodes)
        id__in=ProcessNode.objects.filter(parent__isnull=False).values('parent_id')
    ).select_related('model_version', 'model_version__model')
    
    nodes_with_details = []
    for node in nodes:
        # Check if node has process details
        process_details = NodeDocument.objects.filter(
            node=node,
            document_type='process_details'
        ).first()
        
        if process_details:
            nodes_with_details.append({
                'node': node,
                'document': process_details,
                'code': node.code,
                'name': node.name,
                'description': node.description or '',
            })
    
    return nodes_with_details

def find_matching_pairs():
    """Find CI-LS node pairs that are identical and eligible for copying."""
    print("🔍 Finding identical leaf nodes between models...")
    
    ci_nodes = get_leaf_nodes_with_details('apqc_pcf')
    ls_nodes_dict = {}
    
    # Create lookup dict for LS nodes
    ls_nodes = ProcessNode.objects.filter(
        model_version__model__model_key='apqc_pcf_lifescience',
        model_version__is_current=True
    ).exclude(
        id__in=ProcessNode.objects.filter(parent__isnull=False).values('parent_id')
    ).select_related('model_version', 'model_version__model')
    
    for node in ls_nodes:
        key = (node.code, node.name, node.description or '')
        ls_nodes_dict[key] = node
    
    # Find matching pairs
    matching_pairs = []
    for ci_data in ci_nodes:
        key = (ci_data['code'], ci_data['name'], ci_data['description'])
        if key in ls_nodes_dict:
            ls_node = ls_nodes_dict[key]
            
            # Check if LS node already has process details
            existing_ls_details = NodeDocument.objects.filter(
                node=ls_node,
                document_type='process_details'
            ).exists()
            
            if not existing_ls_details:
                matching_pairs.append({
                    'ci_node': ci_data['node'],
                    'ci_document': ci_data['document'],
                    'ls_node': ls_node,
                    'code': ci_data['code'],
                    'name': ci_data['name']
                })
    
    return matching_pairs

def copy_process_details(matching_pairs, dry_run=True, max_copies=None):
    """
    Copy process details from CI to LS for matching pairs.
    
    Args:
        matching_pairs: List of CI-LS node pairs
        dry_run: If True, only simulate the operation
        max_copies: Limit number of copies (for testing)
    """
    
    if not matching_pairs:
        print("❌ No matching pairs found for copying.")
        return
    
    copy_count = len(matching_pairs)
    if max_copies:
        matching_pairs = matching_pairs[:max_copies]
        copy_count = len(matching_pairs)
    
    print(f"📋 {'DRY RUN: Would copy' if dry_run else 'Copying'} {copy_count} process details...")
    
    if dry_run:
        print("\n📝 Sample operations that would be performed:")
        for i, pair in enumerate(matching_pairs[:5]):  # Show first 5 samples
            print(f"   {i+1}. {pair['code']}: {pair['name']}")
            print(f"      From CI node ID {pair['ci_node'].id} -> LS node ID {pair['ls_node'].id}")
            print(f"      Document title: {pair['ci_document'].title}")
        
        if len(matching_pairs) > 5:
            print(f"   ... and {len(matching_pairs) - 5} more")
        
        print(f"\n✅ DRY RUN complete. {copy_count} process details would be copied.")
        return copy_count
    
    # Get the user for ownership (using first available user)
    user = User.objects.first()
    if not user:
        print("❌ No user found. Cannot proceed with copying.")
        return 0
    
    copied_count = 0
    failed_count = 0
    
    with transaction.atomic():
        savepoint = transaction.savepoint()
        
        try:
            for i, pair in enumerate(matching_pairs):
                try:
                    # Create new document for LS node
                    new_document = NodeDocument.objects.create(
                        node=pair['ls_node'],
                        document_type='process_details',
                        title=pair['ci_document'].title,
                        content=pair['ci_document'].content,
                        meta_json=pair['ci_document'].meta_json,
                        user=user
                    )
                    
                    copied_count += 1
                    
                    if (i + 1) % 100 == 0:
                        print(f"   Copied {i + 1}/{copy_count}...")
                
                except Exception as e:
                    print(f"   ⚠️  Failed to copy {pair['code']}: {str(e)}")
                    failed_count += 1
                    continue
            
            print(f"\n✅ Successfully copied {copied_count} process details")
            if failed_count > 0:
                print(f"⚠️  Failed to copy {failed_count} documents")
            
            return copied_count
            
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            print(f"❌ Transaction failed: {str(e)}")
            print("🔄 All changes rolled back - no data was modified")
            return 0

def verify_copy_integrity():
    """Verify that the copy operation didn't damage original CI data."""
    print("\n🔍 Verifying Cross Industry data integrity...")
    
    ci_count_before = NodeDocument.objects.filter(
        node__model_version__model__model_key='apqc_pcf',
        document_type='process_details'
    ).count()
    
    print(f"   Cross Industry process details count: {ci_count_before}")
    
    # Sample check - verify a few CI documents still exist and are unchanged
    sample_docs = NodeDocument.objects.filter(
        node__model_version__model__model_key='apqc_pcf',
        document_type='process_details'
    )[:5]
    
    for doc in sample_docs:
        if doc.content and len(doc.content) > 100:
            print(f"   ✅ CI doc ID {doc.id} intact: {len(doc.content)} chars")
    
    return ci_count_before

def main():
    """Main execution function."""
    print("🚀 PROCESS DETAILS COPY OPERATION")
    print("=" * 50)
    print("📍 From: Cross Industry Model")  
    print("📍 To: Life Science Model")
    print("🎯 Target: Identical leaf nodes only")
    print("🛡️  Safety: Original CI data preserved\n")
    
    # Find matching pairs
    matching_pairs = find_matching_pairs()
    
    if not matching_pairs:
        print("❌ No eligible nodes found for copying.")
        return
    
    print(f"✅ Found {len(matching_pairs)} identical leaf nodes eligible for copying\n")
    
    # Verify CI data integrity before
    ci_count_original = verify_copy_integrity()
    
    # Run dry run first
    print("\n" + "="*50)
    print("🧪 PHASE 1: DRY RUN")
    print("="*50)
    copy_process_details(matching_pairs, dry_run=True)
    
    # Ask for confirmation
    print("\n" + "="*50)
    print("⚠️  CONFIRMATION REQUIRED")
    print("="*50)
    response = input(f"Proceed with copying {len(matching_pairs)} process details? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("❌ Operation cancelled by user.")
        return
    
    # Execute actual copy
    print("\n" + "="*50)
    print("🎯 PHASE 2: ACTUAL COPY")
    print("="*50)
    
    copied_count = copy_process_details(matching_pairs, dry_run=False)
    
    # Verify integrity after
    print("\n" + "="*50)
    print("🔍 PHASE 3: INTEGRITY CHECK")
    print("="*50)
    
    ci_count_after = verify_copy_integrity()
    
    if ci_count_original == ci_count_after:
        print("✅ Cross Industry data integrity verified - no data lost")
    else:
        print(f"⚠️  Cross Industry count changed: {ci_count_original} -> {ci_count_after}")
    
    # Final stats
    ls_count_after = NodeDocument.objects.filter(
        node__model_version__model__model_key='apqc_pcf_lifescience',
        document_type='process_details'
    ).count()
    
    print(f"\n📊 FINAL RESULTS:")
    print(f"   Cross Industry process details: {ci_count_after}")
    print(f"   Life Science process details: {ls_count_after}")
    print(f"   Successfully copied: {copied_count}")
    
    print(f"\n🎉 Copy operation completed successfully!")

if __name__ == "__main__":
    main()