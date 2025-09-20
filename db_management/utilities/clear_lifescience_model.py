#!/usr/bin/env python3
"""
Safely clear the APQC Life Science model data to prepare for re-import with PCF IDs.
This script deletes ONLY the Life Science model data, preserving other models.
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.db import transaction
from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeDocument, NodeAttribute

def clear_lifescience_model():
    """Safely clear the Life Science model data."""
    
    print("🚨 CLEARING LIFE SCIENCE MODEL DATA")
    print("=" * 50)
    print("⚠️  This will DELETE all Life Science model data!")
    print("✅ Other models (Cross Industry, Retail) will be preserved")
    
    # Find the Life Science model
    ls_model = ProcessModel.objects.filter(model_key='apqc_pcf_lifescience').first()
    if not ls_model:
        print("❌ Life Science model not found!")
        return False
    
    ls_version = ls_model.versions.filter(is_current=True).first()
    if not ls_version:
        print("❌ No current Life Science version found!")
        return False
    
    # Count what will be deleted
    node_count = ls_version.nodes.count()
    docs_count = NodeDocument.objects.filter(node__model_version=ls_version).count()
    attrs_count = NodeAttribute.objects.filter(node__model_version=ls_version).count()
    
    print(f"📊 Data to be deleted:")
    print(f"   Model: {ls_model.name}")
    print(f"   Version: {ls_version.version_label}")
    print(f"   Nodes: {node_count}")
    print(f"   Documents: {docs_count}")
    print(f"   Attributes: {attrs_count}")
    
    print("\n🔥 Proceeding with deletion (--force mode)...")
    
    # Delete with transaction safety
    with transaction.atomic():
        print("\n🗑️  Deleting Life Science model data...")
        
        # Delete documents first (to avoid FK constraint issues)
        deleted_docs = NodeDocument.objects.filter(node__model_version=ls_version).count()
        NodeDocument.objects.filter(node__model_version=ls_version).delete()
        print(f"   ✅ Deleted {deleted_docs} documents")
        
        # Delete node attributes
        deleted_attrs = NodeAttribute.objects.filter(node__model_version=ls_version).count()
        NodeAttribute.objects.filter(node__model_version=ls_version).delete()
        print(f"   ✅ Deleted {deleted_attrs} attributes")
        
        # Delete nodes
        deleted_nodes = ls_version.nodes.count()
        ls_version.nodes.all().delete()
        print(f"   ✅ Deleted {deleted_nodes} nodes")
        
        # Delete version
        version_label = ls_version.version_label
        ls_version.delete()
        print(f"   ✅ Deleted version {version_label}")
        
        # Delete model
        model_name = ls_model.name
        ls_model.delete()
        print(f"   ✅ Deleted model {model_name}")
    
    print("\n🎉 Life Science model data cleared successfully!")
    print("🔄 Ready for re-import with PCF IDs")
    
    return True

if __name__ == "__main__":
    clear_lifescience_model()