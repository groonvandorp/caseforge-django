#!/usr/bin/env python3
"""
Check if PCF IDs exist in the Life Science Excel file
"""

import pandas as pd
import sys

def check_excel_for_pcf_ids():
    """Check the Life Science Excel file for PCF ID columns."""
    
    excel_file = "../model_information/apqc_lifescience/K07122_Life_Sciences_v722_vsLife_Sciences_v721_2025.xlsx"
    
    print("🔍 Analyzing Life Science Excel file for PCF IDs...")
    print(f"File: {excel_file}")
    
    try:
        # Get all sheet names
        excel_file_obj = pd.ExcelFile(excel_file)
        sheet_names = excel_file_obj.sheet_names
        
        print(f"\n📋 Found {len(sheet_names)} sheets:")
        for i, sheet in enumerate(sheet_names):
            print(f"   {i+1}. {sheet}")
        
        # Check each sheet for columns
        for sheet_name in sheet_names:
            print(f"\n📊 Analyzing sheet: '{sheet_name}'")
            
            try:
                # Read first few rows to see structure
                df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=0)  # Just get headers
                columns = list(df.columns)
                
                print(f"   Columns ({len(columns)}):")
                for col in columns:
                    print(f"      - {col}")
                
                # Check for PCF ID related columns
                pcf_columns = [col for col in columns if 'pcf' in str(col).lower() or 'id' in str(col).lower()]
                if pcf_columns:
                    print(f"   🎯 Potential PCF ID columns: {pcf_columns}")
                    
                    # Read some sample data
                    sample_df = pd.read_excel(excel_file, sheet_name=sheet_name, nrows=10)
                    for pcf_col in pcf_columns:
                        sample_values = sample_df[pcf_col].dropna().head(5).tolist()
                        print(f"      {pcf_col} sample values: {sample_values}")
                        
            except Exception as e:
                print(f"   ⚠️ Error reading sheet {sheet_name}: {e}")
        
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")

if __name__ == "__main__":
    check_excel_for_pcf_ids()