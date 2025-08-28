#!/usr/bin/env python3
"""
Copy process details from Cross Industry to Retail model using PCF ID-based matching.
Uses the CORRECT matching criteria: PCF ID + name + description.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.db import transaction
from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeAttribute, NodeDocument, User

def get_pcf_id_matches():
    """Get identical nodes between CI and Retail based on PCF ID + name + description."""
    print("🔍 Finding PCF ID-based matches between CI and Retail...")
    
    # Get nodes from both models with PCF IDs
    ci_nodes = ProcessNode.objects.filter(
        model_version__model__model_key='apqc_pcf',
        model_version__is_current=True
    ).select_related('model_version')
    
    retail_nodes = ProcessNode.objects.filter(
        model_version__model__model_key='apqc_pcf_retail',
        model_version__is_current=True
    ).select_related('model_version')
    
    # Build CI nodes with PCF IDs
    ci_pcf_map = {}
    for node in ci_nodes:
        pcf_attr = NodeAttribute.objects.filter(node=node, key='pcf_id').first()
        if pcf_attr:
            key = (pcf_attr.value, node.name, node.description or '')
            ci_pcf_map[key] = node
    
    # Find matching Retail nodes
    matches = []
    for node in retail_nodes:
        pcf_attr = NodeAttribute.objects.filter(node=node, key='pcf_id').first()
        if pcf_attr:
            key = (pcf_attr.value, node.name, node.description or '')
            if key in ci_pcf_map:
                matches.append({
                    'pcf_id': pcf_attr.value,
                    'ci_node': ci_pcf_map[key],
                    'retail_node': node,
                    'name': node.name
                })
    
    print(f"✅ Found {len(matches)} PCF ID-based matches")
    return matches

def get_copyable_process_details(matches):
    """Filter matches to find which ones can have process details copied."""
    print("📄 Analyzing process details copy opportunities...")
    
    copyable = []
    for match in matches:
        # Check if CI node has process details
        ci_details = NodeDocument.objects.filter(
            node=match['ci_node'],
            document_type='process_details'
        ).first()
        
        if ci_details:
            # Check if Retail node already has process details
            retail_details = NodeDocument.objects.filter(
                node=match['retail_node'],
                document_type='process_details'
            ).exists()
            
            if not retail_details:
                copyable.append({
                    **match,
                    'ci_document': ci_details
                })
    
    print(f"✅ Found {len(copyable)} process details ready to copy")
    return copyable

def copy_process_details(copyable_matches, dry_run=True):
    """Copy process details from CI to Retail nodes."""
    if not copyable_matches:
        print("❌ No process details to copy")
        return 0
    
    print(f"📋 {'DRY RUN: Would copy' if dry_run else 'Copying'} {len(copyable_matches)} process details...")
    
    if dry_run:
        print("\n📝 Sample operations that would be performed:")
        for i, match in enumerate(copyable_matches[:10]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']}")
            print(f"      From CI node {match['ci_node'].code} -> Retail node {match['retail_node'].code}")
            print(f"      Document: '{match['ci_document'].title}'")
        
        if len(copyable_matches) > 10:
            print(f"   ... and {len(copyable_matches) - 10} more")
        
        print(f"\n✅ DRY RUN complete. {len(copyable_matches)} process details would be copied.")
        return len(copyable_matches)
    
    # Get user for ownership
    user = User.objects.filter(email='gruhno@gmail.com').first()
    if not user:
        print("❌ User gruhno@gmail.com not found!")
        return 0
    
    copied_count = 0
    failed_count = 0
    
    with transaction.atomic():
        savepoint = transaction.savepoint()
        
        try:
            for i, match in enumerate(copyable_matches):
                try:
                    # Create new process details document for Retail node
                    new_document = NodeDocument.objects.create(
                        node=match['retail_node'],
                        document_type='process_details',
                        title=match['ci_document'].title,
                        content=match['ci_document'].content,
                        meta_json=match['ci_document'].meta_json,
                        user=user
                    )
                    
                    copied_count += 1
                    
                    if (i + 1) % 100 == 0:
                        print(f"   Copied {i + 1}/{len(copyable_matches)}...")
                
                except Exception as e:
                    print(f"   ⚠️  Failed to copy PCF {match['pcf_id']}: {str(e)}")
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

def verify_copy_results():
    """Verify the copy operation results."""
    print("\n🔍 Verifying copy results...")
    
    ci_count = NodeDocument.objects.filter(
        node__model_version__model__model_key='apqc_pcf',
        document_type='process_details'
    ).count()
    
    retail_count = NodeDocument.objects.filter(
        node__model_version__model__model_key='apqc_pcf_retail',
        document_type='process_details'
    ).count()
    
    print(f"   Cross Industry process details: {ci_count}")
    print(f"   Retail process details: {retail_count}")
    
    return ci_count, retail_count

def main():
    """Main execution function."""
    print("🚀 PCF ID-BASED PROCESS DETAILS COPY: CI → RETAIL")
    print("=" * 60)
    print("✅ Using CORRECT matching criteria:")
    print("   - Same PCF ID (5-digit number)")
    print("   - Same name")
    print("   - Same description")
    print("❌ NOT using hierarchical codes")
    
    # Find PCF ID matches
    matches = get_pcf_id_matches()
    
    if not matches:
        print("❌ No PCF ID matches found!")
        return
    
    # Find copyable process details
    copyable = get_copyable_process_details(matches)
    
    if not copyable:
        print("❌ No process details to copy!")
        return
    
    # Verify current state
    ci_before, retail_before = verify_copy_results()
    
    # Run dry run first
    print("\n" + "="*50)
    print("🧪 PHASE 1: DRY RUN")
    print("="*50)
    copy_process_details(copyable, dry_run=True)
    
    # Auto-proceed for automation
    print("\n" + "="*50)
    print("✅ AUTO-PROCEEDING WITH COPY")
    print("="*50)
    
    # Execute actual copy
    print("\n" + "="*50)
    print("🎯 PHASE 2: ACTUAL COPY")
    print("="*50)
    
    copied_count = copy_process_details(copyable, dry_run=False)
    
    # Verify results
    print("\n" + "="*50)
    print("🔍 PHASE 3: VERIFICATION")
    print("="*50)
    
    ci_after, retail_after = verify_copy_results()
    
    print(f"\n📊 COPY RESULTS:")
    print(f"   Cross Industry (before/after): {ci_before} / {ci_after}")
    print(f"   Retail (before/after): {retail_before} / {retail_after}")
    print(f"   Successfully copied: {copied_count}")
    print(f"   Retail increase: +{retail_after - retail_before}")
    
    if ci_before == ci_after:
        print("✅ Cross Industry data integrity verified")
    else:
        print("⚠️  Cross Industry count changed unexpectedly")
    
    if copied_count > 0:
        print("\n🎉 Process details copy completed successfully!")
    else:
        print("\n❌ No process details were copied!")

if __name__ == "__main__":
    main()