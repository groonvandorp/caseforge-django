#!/usr/bin/env python3
"""
Copy AI usecase candidates from Cross Industry to Life Science model using PCF ID-based matching.
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
from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeAttribute, NodeUsecaseCandidate, User

def get_pcf_id_matches():
    """Get identical nodes between CI and LS based on PCF ID + name + description."""
    print("🔍 Finding PCF ID-based matches...")
    
    # Get nodes from both models with PCF IDs
    ci_nodes = ProcessNode.objects.filter(
        model_version__model__model_key='apqc_pcf',
        model_version__is_current=True
    ).select_related('model_version')
    
    ls_nodes = ProcessNode.objects.filter(
        model_version__model__model_key='apqc_pcf_lifescience',
        model_version__is_current=True
    ).select_related('model_version')
    
    # Build CI nodes with PCF IDs
    ci_pcf_map = {}
    for node in ci_nodes:
        pcf_attr = NodeAttribute.objects.filter(node=node, key='pcf_id').first()
        if pcf_attr:
            key = (pcf_attr.value, node.name, node.description or '')
            ci_pcf_map[key] = node
    
    # Find matching LS nodes
    matches = []
    for node in ls_nodes:
        pcf_attr = NodeAttribute.objects.filter(node=node, key='pcf_id').first()
        if pcf_attr:
            key = (pcf_attr.value, node.name, node.description or '')
            if key in ci_pcf_map:
                matches.append({
                    'pcf_id': pcf_attr.value,
                    'ci_node': ci_pcf_map[key],
                    'ls_node': node,
                    'name': node.name
                })
    
    print(f"✅ Found {len(matches)} PCF ID-based matches")
    return matches

def get_copyable_usecase_candidates(matches):
    """Filter matches to find which ones can have usecase candidates copied."""
    print("💡 Analyzing AI usecase candidates copy opportunities...")
    
    copyable = []
    for match in matches:
        # Get CI node's usecase candidates
        ci_candidates = NodeUsecaseCandidate.objects.filter(node=match['ci_node'])
        
        if ci_candidates.exists():
            # Check if LS node already has usecase candidates
            ls_candidates = NodeUsecaseCandidate.objects.filter(node=match['ls_node'])
            
            if not ls_candidates.exists():
                copyable.append({
                    **match,
                    'ci_candidates': list(ci_candidates),
                    'candidate_count': ci_candidates.count()
                })
    
    print(f"✅ Found {len(copyable)} nodes with AI usecase candidates ready to copy")
    
    # Calculate total candidates
    total_candidates = sum(item['candidate_count'] for item in copyable)
    print(f"📊 Total AI usecase candidates to copy: {total_candidates}")
    
    return copyable

def copy_usecase_candidates(copyable_matches, dry_run=True):
    """Copy usecase candidates from CI to LS nodes."""
    if not copyable_matches:
        print("❌ No usecase candidates to copy")
        return 0
    
    total_candidates = sum(item['candidate_count'] for item in copyable_matches)
    
    print(f"📋 {'DRY RUN: Would copy' if dry_run else 'Copying'} {total_candidates} usecase candidates from {len(copyable_matches)} nodes...")
    
    if dry_run:
        print("\n📝 Sample operations that would be performed:")
        for i, match in enumerate(copyable_matches[:10]):
            print(f"   {i+1}. PCF {match['pcf_id']}: {match['name']}")
            print(f"      From CI node {match['ci_node'].code} -> LS node {match['ls_node'].code}")
            print(f"      Candidates: {match['candidate_count']}")
            
            # Show sample candidates
            sample_candidates = match['ci_candidates'][:2]
            for j, candidate in enumerate(sample_candidates):
                print(f"         - {candidate.title}")
        
        if len(copyable_matches) > 10:
            print(f"   ... and {len(copyable_matches) - 10} more nodes")
        
        print(f"\n✅ DRY RUN complete. {total_candidates} usecase candidates would be copied.")
        return total_candidates
    
    # Get user for ownership
    user = User.objects.filter(email='gruhno@gmail.com').first()
    if not user:
        print("❌ User gruhno@gmail.com not found!")
        return 0
    
    copied_nodes = 0
    copied_candidates = 0
    failed_nodes = 0
    
    with transaction.atomic():
        savepoint = transaction.savepoint()
        
        try:
            for i, match in enumerate(copyable_matches):
                try:
                    node_success = True
                    node_copied_count = 0
                    
                    # Copy all candidates for this node
                    for candidate in match['ci_candidates']:
                        try:
                            # Generate new unique UID for the copied candidate
                            import uuid
                            new_uid = f"ls_{str(uuid.uuid4())[:8]}_{candidate.candidate_uid}"
                            
                            new_candidate = NodeUsecaseCandidate.objects.create(
                                node=match['ls_node'],
                                user=user,
                                candidate_uid=new_uid,  # Use new unique UID
                                title=candidate.title,
                                description=candidate.description,
                                impact_assessment=candidate.impact_assessment,
                                complexity_score=candidate.complexity_score,
                                meta_json=candidate.meta_json
                            )
                            
                            copied_candidates += 1
                            node_copied_count += 1
                            
                        except Exception as e:
                            print(f"      ⚠️  Failed to copy candidate '{candidate.title}': {str(e)}")
                            node_success = False
                            continue
                    
                    if node_success:
                        copied_nodes += 1
                    else:
                        failed_nodes += 1
                    
                    if (i + 1) % 50 == 0:
                        print(f"   Processed {i + 1}/{len(copyable_matches)} nodes...")
                
                except Exception as e:
                    print(f"   ⚠️  Failed to process node PCF {match['pcf_id']}: {str(e)}")
                    failed_nodes += 1
                    continue
            
            print(f"\n✅ Successfully copied usecase candidates:")
            print(f"   Nodes processed: {copied_nodes}")
            print(f"   Total candidates copied: {copied_candidates}")
            if failed_nodes > 0:
                print(f"   ⚠️  Failed nodes: {failed_nodes}")
            
            return copied_candidates
            
        except Exception as e:
            transaction.savepoint_rollback(savepoint)
            print(f"❌ Transaction failed: {str(e)}")
            print("🔄 All changes rolled back - no data was modified")
            return 0

def verify_copy_results():
    """Verify the copy operation results."""
    print("\n🔍 Verifying copy results...")
    
    ci_count = NodeUsecaseCandidate.objects.filter(
        node__model_version__model__model_key='apqc_pcf'
    ).count()
    
    ls_count = NodeUsecaseCandidate.objects.filter(
        node__model_version__model__model_key='apqc_pcf_lifescience'
    ).count()
    
    print(f"   Cross Industry usecase candidates: {ci_count}")
    print(f"   Life Science usecase candidates: {ls_count}")
    
    return ci_count, ls_count

def main():
    """Main execution function."""
    print("🚀 PCF ID-BASED AI USECASE CANDIDATES COPY")
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
    
    # Find copyable usecase candidates
    copyable = get_copyable_usecase_candidates(matches)
    
    if not copyable:
        print("❌ No usecase candidates to copy!")
        return
    
    # Verify current state
    ci_before, ls_before = verify_copy_results()
    
    # Run dry run first
    print("\n" + "="*50)
    print("🧪 PHASE 1: DRY RUN")
    print("="*50)
    copy_usecase_candidates(copyable, dry_run=True)
    
    # Auto-proceed for automation
    print("\n" + "="*50)
    print("✅ AUTO-PROCEEDING WITH COPY")
    print("="*50)
    
    # Execute actual copy
    print("\n" + "="*50)
    print("🎯 PHASE 2: ACTUAL COPY")
    print("="*50)
    
    copied_count = copy_usecase_candidates(copyable, dry_run=False)
    
    # Verify results
    print("\n" + "="*50)
    print("🔍 PHASE 3: VERIFICATION")
    print("="*50)
    
    ci_after, ls_after = verify_copy_results()
    
    print(f"\n📊 COPY RESULTS:")
    print(f"   Cross Industry (before/after): {ci_before} / {ci_after}")
    print(f"   Life Science (before/after): {ls_before} / {ls_after}")
    print(f"   Successfully copied: {copied_count}")
    print(f"   Life Science increase: +{ls_after - ls_before}")
    
    if ci_before == ci_after:
        print("✅ Cross Industry data integrity verified")
    else:
        print("⚠️  Cross Industry count changed unexpectedly")
    
    if copied_count > 0:
        print("\n🎉 AI usecase candidates copy completed successfully!")
    else:
        print("\n❌ No usecase candidates were copied!")

if __name__ == "__main__":
    main()