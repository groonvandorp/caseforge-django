#!/usr/bin/env python3
"""
Import script for APQC PCF Life Science 7.2.2 model from multi-tab Excel file.
This script imports process nodes from an Excel file where each root node (1-13) 
is in a separate tab.
"""

import os
import sys
import django
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from core.models import ProcessModel, ProcessModelVersion, ProcessNode, User, NodeAttribute

class LifeScienceModelImporter:
    """Import APQC PCF Life Science 7.2.2 model from multi-tab Excel file."""
    
    def __init__(self, excel_file_path):
        self.excel_file_path = Path(excel_file_path)
        self.model_key = "apqc_pcf_lifescience"
        self.model_name = "APQC PCF - Life Science 7.2.2"
        self.version_label = "v7.2.2"
        
        # Expected columns in Excel sheets (adjust based on actual structure)
        self.expected_columns = ['Level', 'Code', 'Name', 'Description']
        
    def validate_excel_file(self):
        """Validate that the Excel file exists and has the expected structure."""
        if not self.excel_file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.excel_file_path}")
        
        # Check that we can read the Excel file
        try:
            excel_file = pd.ExcelFile(self.excel_file_path)
            sheet_names = excel_file.sheet_names
            print(f"Found {len(sheet_names)} sheets in Excel file:")
            for sheet in sheet_names:
                print(f"  - {sheet}")
            
            # Validate that we have numbered sheets (1.0, 2.0, etc.) 
            numbered_sheets = []
            for sheet in sheet_names:
                # Check for patterns like "1.0", "2.0", etc.
                if '.' in sheet:
                    try:
                        main_num = sheet.split('.')[0]
                        if main_num.isdigit() and sheet.endswith('.0'):
                            numbered_sheets.append(sheet)
                    except:
                        continue
            
            if len(numbered_sheets) == 0:
                print("Warning: No numbered root sheets (X.0) found. Available sheets:")
                for sheet in sheet_names:
                    print(f"  - {sheet}")
                return sheet_names
            
            # Sort by the main number (1.0 -> 1, 2.0 -> 2, etc.)
            numbered_sheets.sort(key=lambda x: int(x.split('.')[0]))
            print(f"Found {len(numbered_sheets)} root node sheets: {numbered_sheets}")
            return numbered_sheets
            
        except Exception as e:
            raise Exception(f"Error reading Excel file: {e}")
    
    def analyze_sheet_structure(self, sheet_names):
        """Analyze the structure of the Excel sheets to understand the data format."""
        sample_sheets = sheet_names[:3]  # Analyze first 3 sheets
        
        print("\nAnalyzing sheet structure...")
        for sheet_name in sample_sheets:
            print(f"\n--- Sheet: {sheet_name} ---")
            try:
                # Try different header row positions
                for header_row in [0, 1, 2]:
                    try:
                        df = pd.read_excel(self.excel_file_path, sheet_name=sheet_name, header=header_row, nrows=5)
                        print(f"Header row {header_row} - Columns: {list(df.columns)}")
                        print(f"Sample data:\n{df.head(2)}")
                        break
                    except Exception as e:
                        continue
            except Exception as e:
                print(f"Error reading sheet {sheet_name}: {e}")
        
        # Ask user to confirm the structure
        print("\nPlease review the sheet structure above.")
        print("The importer expects columns like: Level, Code, Name, Description")
        
        header_row = input("Which header row should be used? (default: 0): ").strip()
        if not header_row:
            header_row = 0
        else:
            header_row = int(header_row)
        
        return header_row
    
    def read_sheet_data(self, sheet_name, header_row=0):
        """Read and process data from a single Excel sheet."""
        print(f"Reading sheet: {sheet_name}")
        
        try:
            df = pd.read_excel(self.excel_file_path, sheet_name=sheet_name, header=header_row)
            
            # Clean up column names
            df.columns = df.columns.str.strip()
            
            print(f"Sheet {sheet_name} - Columns: {list(df.columns)}")
            print(f"Sheet {sheet_name} - Rows: {len(df)}")
            
            # Filter out empty rows
            df = df.dropna(how='all')
            
            # Map APQC column names to our expected names
            column_mapping = {
                'Hierarchy ID': 'Code',
                'Element Description': 'Description',
                'PCF ID': 'PCF_ID'
            }
            
            # Rename columns using the mapping
            df = df.rename(columns=column_mapping)
            
            # Basic validation - check for required columns after mapping
            required_cols = ['Code', 'Name']  # Minimum required columns
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                print(f"Warning: Missing required columns in sheet {sheet_name}: {missing_cols}")
                print(f"Available columns: {list(df.columns)}")
                return None
            
            print(f"Sheet {sheet_name} - Mapped columns: {list(df.columns)}")
            return df
            
        except Exception as e:
            print(f"Error reading sheet {sheet_name}: {e}")
            return None
    
    def create_model_and_version(self):
        """Create the ProcessModel and ProcessModelVersion."""
        try:
            # Get or create the gruhno user
            user = User.objects.get(email='gruhno@gmail.com')
            print(f"Using user: {user.username}")
        except User.DoesNotExist:
            print("Error: gruhno@gmail.com user not found")
            return None, None
        
        # Create or get ProcessModel
        model, created = ProcessModel.objects.get_or_create(
            model_key=self.model_key,
            defaults={
                'name': self.model_name,
                'description': 'APQC Process Classification Framework for Life Science Industry version 7.2.2',
            }
        )
        
        if created:
            print(f"Created new ProcessModel: {self.model_key}")
        else:
            print(f"Using existing ProcessModel: {self.model_key}")
        
        # Create or get ProcessModelVersion
        version, created = ProcessModelVersion.objects.get_or_create(
            model=model,
            version_label=self.version_label,
            defaults={
                'external_reference': str(self.excel_file_path),
                'notes': f'APQC Life Science 7.2.2 model imported from Excel file on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'effective_date': datetime.now().date(),
                'is_current': True
            }
        )
        
        if created:
            print(f"Created new ProcessModelVersion: {self.version_label}")
        else:
            print(f"Using existing ProcessModelVersion: {self.version_label}")
        
        return model, version
    
    def parse_process_level(self, code):
        """Determine the process level from the code (e.g., '1.2.3' -> level 3)."""
        if pd.isna(code) or not isinstance(code, str):
            return 0
        return len(str(code).split('.'))
    
    def build_materialized_path(self, code):
        """Build materialized path from process code."""
        if pd.isna(code) or not isinstance(code, str):
            return ""
        parts = str(code).split('.')
        paths = []
        for i in range(len(parts)):
            paths.append('.'.join(parts[:i+1]))
        return '/'.join(paths) + '/'
    
    def import_sheet_nodes(self, sheet_data, sheet_name, model_version):
        """Import process nodes from a single sheet."""
        if sheet_data is None or sheet_data.empty:
            print(f"No data to import from sheet {sheet_name}")
            return 0, 0
        
        imported_count = 0
        skipped_count = 0
        node_map = {}  # code -> ProcessNode
        
        # Sort by level and code to ensure parents are created before children
        sheet_data['Level'] = sheet_data.get('Code', '').apply(self.parse_process_level)
        sheet_data = sheet_data.sort_values(['Level', 'Code']).reset_index(drop=True)
        
        print(f"Processing {len(sheet_data)} rows from sheet {sheet_name}")
        
        for idx, row in sheet_data.iterrows():
            code = str(row.get('Code', '')).strip()
            name = str(row.get('Name', '')).strip()
            description = str(row.get('Description', '')).strip()
            pcf_id = str(row.get('PCF_ID', '')).strip() if pd.notna(row.get('PCF_ID', '')) else None
            
            # Skip empty rows
            if not code or code == 'nan' or not name or name == 'nan':
                skipped_count += 1
                continue
            
            # Determine parent
            parent_node = None
            code_parts = code.split('.')
            if len(code_parts) > 1:
                parent_code = '.'.join(code_parts[:-1])
                parent_node = node_map.get(parent_code)
                if not parent_node:
                    # Try to find parent in database
                    parent_node = ProcessNode.objects.filter(
                        model_version=model_version,
                        code=parent_code
                    ).first()
            
            # Check if node already exists
            existing_node = ProcessNode.objects.filter(
                model_version=model_version,
                code=code
            ).first()
            
            if existing_node:
                print(f"Node {code} already exists, updating...")
                existing_node.name = name or existing_node.name
                existing_node.description = description or existing_node.description
                existing_node.save()
                
                # Update PCF ID attribute if provided
                if pcf_id and pcf_id != 'nan':
                    NodeAttribute.objects.update_or_create(
                        node=existing_node,
                        key='pcf_id',
                        defaults={'value': pcf_id, 'data_type': 'text'}
                    )
                
                node_map[code] = existing_node
                continue
            
            # Create new node
            try:
                level = self.parse_process_level(code)
                materialized_path = self.build_materialized_path(code)
                
                node = ProcessNode.objects.create(
                    model_version=model_version,
                    parent=parent_node,
                    code=code,
                    name=name,
                    description=description,
                    level=level,
                    display_order=idx + 1,
                    materialized_path=materialized_path
                )
                
                # Store PCF ID as node attribute if provided
                if pcf_id and pcf_id != 'nan':
                    NodeAttribute.objects.create(
                        node=node,
                        key='pcf_id',
                        value=pcf_id,
                        data_type='text'
                    )
                    print(f"  Created: {code} - {name} (Level {level}) [PCF ID: {pcf_id}]")
                else:
                    print(f"  Created: {code} - {name} (Level {level})")
                
                node_map[code] = node
                imported_count += 1
                
            except Exception as e:
                print(f"Error creating node {code}: {e}")
                skipped_count += 1
        
        return imported_count, skipped_count
    
    def import_model(self, interactive=True):
        """Main method to import the life science model."""
        print(f"Starting import of APQC Life Science 7.2.2 model from: {self.excel_file_path}")
        
        # Validate Excel file
        sheet_names = self.validate_excel_file()
        
        if interactive:
            # Analyze structure
            header_row = self.analyze_sheet_structure(sheet_names)
        else:
            header_row = 0
        
        # Create model and version
        model, version = self.create_model_and_version()
        if not model or not version:
            print("Failed to create model and version")
            return False
        
        # Process each sheet
        total_imported = 0
        total_skipped = 0
        
        # If sheets are numbered (1.0-13.0), sort them numerically
        if all('.' in sheet and sheet.split('.')[0].isdigit() for sheet in sheet_names if sheet.endswith('.0')):
            # Sort by the main number (1.0 -> 1, 2.0 -> 2, etc.)
            sheet_names = sorted([s for s in sheet_names if s.endswith('.0')], 
                               key=lambda x: int(x.split('.')[0]))
            print(f"Processing root node sheets in order: {sheet_names}")
        
        for sheet_name in sheet_names:
            print(f"\n=== Processing Sheet: {sheet_name} ===")
            
            # Read sheet data
            sheet_data = self.read_sheet_data(sheet_name, header_row)
            
            # Import nodes from this sheet
            imported, skipped = self.import_sheet_nodes(sheet_data, sheet_name, version)
            
            total_imported += imported
            total_skipped += skipped
            
            print(f"Sheet {sheet_name}: {imported} imported, {skipped} skipped")
        
        print(f"\n=== Import Summary ===")
        print(f"Model: {self.model_name}")
        print(f"Version: {self.version_label}")
        print(f"Total nodes imported: {total_imported}")
        print(f"Total nodes skipped: {total_skipped}")
        print(f"Import completed successfully!")
        
        return True

def main():
    """Main function to run the importer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import APQC PCF Life Science 7.2.2 model from Excel')
    parser.add_argument('excel_file', help='Path to the life science model Excel file')
    parser.add_argument('--non-interactive', action='store_true', help='Run without user interaction')
    
    args = parser.parse_args()
    
    try:
        importer = LifeScienceModelImporter(args.excel_file)
        success = importer.import_model(interactive=not args.non_interactive)
        
        if success:
            print("\n✅ Import completed successfully!")
            return 0
        else:
            print("\n❌ Import failed!")
            return 1
            
    except Exception as e:
        print(f"Error during import: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())