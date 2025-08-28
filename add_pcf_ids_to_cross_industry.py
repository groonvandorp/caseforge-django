#!/usr/bin/env python3
"""
Add PCF IDs to existing Cross Industry model nodes by reading from the Excel file.
This updates the existing nodes without re-importing the entire model.
"""

import os
import sys
import django
import pandas as pd

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.db import transaction
from core.models import ProcessModel, ProcessModelVersion, ProcessNode, NodeAttribute

class CrossIndustryPCFUpdater:
    """Add PCF IDs to existing Cross Industry nodes."""
    
    def __init__(self):
        self.excel_file = '/Users/oliver/Library/Mobile Documents/com~apple~CloudDocs/Projekte/2025 Onwell/development/backend/model_information/K014749_APQC Process Classification Framework (PCF) - Cross-Industry - Excel Version 7.4.xlsx'
        self.model_key = 'apqc_pcf'
    
    def read_excel_pcf_data(self):
        """Read PCF ID data from all sheets in the Excel file."""
        print("📖 Reading PCF ID data from Cross Industry Excel file...")
        
        # Get sheet names (1.0 through 13.0)
        excel_file_obj = pd.ExcelFile(self.excel_file)
        sheet_names = [s for s in excel_file_obj.sheet_names if s.endswith('.0') and s.split('.')[0].isdigit()]
        sheet_names.sort(key=lambda x: int(x.split('.')[0]))
        
        print(f"   Processing {len(sheet_names)} sheets: {sheet_names}")
        
        pcf_data = {}  # code -> {pcf_id, name, description}
        
        for sheet_name in sheet_names:
            print(f"   Reading sheet: {sheet_name}")
            
            try:
                df = pd.read_excel(self.excel_file, sheet_name=sheet_name)
                
                # Clean column names
                df.columns = df.columns.str.strip()
                
                # Map columns (same as Life Science)
                column_mapping = {
                    'Hierarchy ID': 'Code',
                    'Element Description': 'Description',
                    'PCF ID': 'PCF_ID'
                }
                df = df.rename(columns=column_mapping)
                
                # Process each row
                for _, row in df.iterrows():
                    code = str(row.get('Code', '')).strip()
                    name = str(row.get('Name', '')).strip()
                    description = str(row.get('Description', '')).strip()
                    pcf_id = str(row.get('PCF_ID', '')).strip() if pd.notna(row.get('PCF_ID', '')) else None
                    
                    if code and code != 'nan' and name and name != 'nan' and pcf_id and pcf_id != 'nan':
                        pcf_data[code] = {
                            'pcf_id': pcf_id,
                            'name': name,
                            'description': description
                        }
                
            except Exception as e:
                print(f"   Error reading sheet {sheet_name}: {e}")
                continue
        
        print(f"✅ Read {len(pcf_data)} PCF ID entries from Excel")
        return pcf_data
    
    def update_cross_industry_nodes(self, pcf_data):
        """Update existing Cross Industry nodes with PCF IDs."""
        print("\n🔄 Updating Cross Industry nodes with PCF IDs...")
        
        # Get Cross Industry model
        ci_model = ProcessModel.objects.filter(model_key=self.model_key).first()
        if not ci_model:
            print("❌ Cross Industry model not found!")
            return False
        
        ci_version = ci_model.versions.filter(is_current=True).first()
        if not ci_version:
            print("❌ No current Cross Industry version found!")
            return False
        
        print(f"   Model: {ci_model.name}")
        print(f"   Version: {ci_version.version_label}")
        
        # Get all nodes
        nodes = ci_version.nodes.all()
        print(f"   Total nodes: {nodes.count()}")
        
        updated_count = 0
        not_found_count = 0
        already_exists_count = 0
        
        with transaction.atomic():
            for node in nodes:
                # Check if PCF ID already exists for this node
                existing_attr = NodeAttribute.objects.filter(
                    node=node,
                    key='pcf_id'
                ).first()
                
                if existing_attr:
                    already_exists_count += 1
                    continue
                
                # Look up PCF data by code
                if node.code in pcf_data:
                    pcf_info = pcf_data[node.code]
                    
                    # Verify name matches (sanity check)
                    if node.name == pcf_info['name']:
                        # Create PCF ID attribute
                        NodeAttribute.objects.create(
                            node=node,
                            key='pcf_id',
                            value=pcf_info['pcf_id'],
                            data_type='text'
                        )
                        updated_count += 1
                        
                        if updated_count % 100 == 0:
                            print(f"   Updated {updated_count} nodes...")
                    else:
                        print(f"   ⚠️  Name mismatch for {node.code}: DB='{node.name}' vs Excel='{pcf_info['name']}'")
                        not_found_count += 1
                else:
                    not_found_count += 1
        
        print(f"\n📊 Update Results:")
        print(f"   ✅ Updated with PCF IDs: {updated_count}")
        print(f"   ⚠️  Not found in Excel: {not_found_count}")
        print(f"   ℹ️  Already had PCF IDs: {already_exists_count}")
        
        return updated_count > 0
    
    def verify_update(self):
        """Verify that PCF IDs were added correctly."""
        print("\n🔍 Verifying PCF ID updates...")
        
        ci_model = ProcessModel.objects.filter(model_key=self.model_key).first()
        ci_version = ci_model.versions.filter(is_current=True).first()
        
        total_nodes = ci_version.nodes.count()
        pcf_attrs = NodeAttribute.objects.filter(
            node__model_version=ci_version,
            key='pcf_id'
        ).count()
        
        print(f"   Total nodes: {total_nodes}")
        print(f"   Nodes with PCF IDs: {pcf_attrs}")
        print(f"   Coverage: {(pcf_attrs/total_nodes*100):.1f}%")
        
        # Show sample PCF IDs
        sample_attrs = NodeAttribute.objects.filter(
            node__model_version=ci_version,
            key='pcf_id'
        ).select_related('node').order_by('node__level', 'node__code')[:5]
        
        print(f"\n📋 Sample PCF IDs:")
        for attr in sample_attrs:
            print(f"   {attr.node.code}: {attr.node.name} [PCF: {attr.value}]")

def main():
    """Main execution function."""
    print("🚀 ADDING PCF IDS TO CROSS INDUSTRY MODEL")
    print("=" * 60)
    
    updater = CrossIndustryPCFUpdater()
    
    # Read PCF data from Excel
    pcf_data = updater.read_excel_pcf_data()
    
    if not pcf_data:
        print("❌ No PCF data found in Excel file!")
        return
    
    # Update nodes with PCF IDs
    success = updater.update_cross_industry_nodes(pcf_data)
    
    if success:
        updater.verify_update()
        print("\n🎉 PCF ID update completed successfully!")
    else:
        print("\n❌ PCF ID update failed!")

if __name__ == "__main__":
    main()