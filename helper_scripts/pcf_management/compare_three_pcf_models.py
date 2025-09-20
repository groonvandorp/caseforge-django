#!/usr/bin/env python3
"""
Comprehensive comparison of all three APQC PCF models:
- Cross Industry V.7.4
- Life Science 7.2.2  
- Retail V.7.2.1
"""

import sqlite3
import csv
from collections import defaultdict

def get_db_connection():
    """Get database connection."""
    return sqlite3.connect('db.sqlite3')

def get_model_nodes(conn, model_key):
    """Get all nodes for a specific model."""
    cursor = conn.execute("""
        SELECT pn.code, pn.name, pn.description, pn.level, pn.display_order
        FROM process_node pn
        JOIN process_model_version pmv ON pn.model_version_id = pmv.id
        JOIN process_model pm ON pmv.model_id = pm.id
        WHERE pm.model_key = ? AND pmv.is_current = 1
        ORDER BY pn.code
    """, (model_key,))
    
    return {row[0]: {
        'name': row[1],
        'description': row[2] or '',
        'level': row[3],
        'display_order': row[4] or 0
    } for row in cursor.fetchall()}

def analyze_three_way_comparison():
    """Perform comprehensive three-way comparison."""
    
    conn = get_db_connection()
    
    print("🔍 Loading APQC PCF Models...")
    models = {
        'cross_industry': get_model_nodes(conn, 'apqc_pcf'),
        'life_science': get_model_nodes(conn, 'apqc_pcf_lifescience'), 
        'retail': get_model_nodes(conn, 'apqc_pcf_retail')
    }
    
    print(f"   Cross Industry: {len(models['cross_industry'])} nodes")
    print(f"   Life Science: {len(models['life_science'])} nodes")
    print(f"   Retail: {len(models['retail'])} nodes")
    
    # Get all unique codes across all models
    all_codes = set()
    for model_nodes in models.values():
        all_codes.update(model_nodes.keys())
    
    print(f"   Total unique codes: {len(all_codes)}")
    
    # Categorize codes
    categories = {
        'all_three': [],      # Present in all three models
        'ci_ls_only': [],     # Cross Industry + Life Science only
        'ci_retail_only': [], # Cross Industry + Retail only  
        'ls_retail_only': [], # Life Science + Retail only
        'ci_only': [],        # Cross Industry only
        'ls_only': [],        # Life Science only
        'retail_only': []     # Retail only
    }
    
    identical_names = {
        'all_three': 0,
        'ci_ls_only': 0, 
        'ci_retail_only': 0,
        'ls_retail_only': 0
    }
    
    print("\n📊 Analyzing node distribution...")
    
    for code in sorted(all_codes):
        in_ci = code in models['cross_industry']
        in_ls = code in models['life_science']
        in_retail = code in models['retail']
        
        if in_ci and in_ls and in_retail:
            categories['all_three'].append(code)
            # Check if names are identical
            ci_name = models['cross_industry'][code]['name']
            ls_name = models['life_science'][code]['name']  
            retail_name = models['retail'][code]['name']
            if ci_name == ls_name == retail_name:
                identical_names['all_three'] += 1
                
        elif in_ci and in_ls and not in_retail:
            categories['ci_ls_only'].append(code)
            ci_name = models['cross_industry'][code]['name']
            ls_name = models['life_science'][code]['name']
            if ci_name == ls_name:
                identical_names['ci_ls_only'] += 1
                
        elif in_ci and not in_ls and in_retail:
            categories['ci_retail_only'].append(code)  
            ci_name = models['cross_industry'][code]['name']
            retail_name = models['retail'][code]['name']
            if ci_name == retail_name:
                identical_names['ci_retail_only'] += 1
                
        elif not in_ci and in_ls and in_retail:
            categories['ls_retail_only'].append(code)
            ls_name = models['life_science'][code]['name']
            retail_name = models['retail'][code]['name'] 
            if ls_name == retail_name:
                identical_names['ls_retail_only'] += 1
                
        elif in_ci and not in_ls and not in_retail:
            categories['ci_only'].append(code)
        elif not in_ci and in_ls and not in_retail:
            categories['ls_only'].append(code)
        elif not in_ci and not in_ls and in_retail:
            categories['retail_only'].append(code)
    
    # Print summary statistics
    print("\n📈 DISTRIBUTION SUMMARY:")
    print("=" * 50)
    print(f"Present in all three models:     {len(categories['all_three']):4d} ({identical_names['all_three']} identical names)")
    print(f"Cross Industry + Life Science:   {len(categories['ci_ls_only']):4d} ({identical_names['ci_ls_only']} identical names)")
    print(f"Cross Industry + Retail:         {len(categories['ci_retail_only']):4d} ({identical_names['ci_retail_only']} identical names)")
    print(f"Life Science + Retail only:      {len(categories['ls_retail_only']):4d} ({identical_names['ls_retail_only']} identical names)")
    print(f"Cross Industry only:             {len(categories['ci_only']):4d}")
    print(f"Life Science only:               {len(categories['ls_only']):4d}")
    print(f"Retail only:                     {len(categories['retail_only']):4d}")
    
    # Core universal processes
    universal_percentage = (len(categories['all_three']) / len(all_codes)) * 100
    print(f"\n🎯 UNIVERSAL PROCESSES: {universal_percentage:.1f}% of all processes exist in all three models")
    
    # Level analysis for universal processes
    print(f"\n📊 LEVEL ANALYSIS (Universal Processes):")
    level_counts = defaultdict(int)
    for code in categories['all_three']:
        level = models['cross_industry'][code]['level'] 
        level_counts[level] += 1
    
    for level in sorted(level_counts.keys()):
        print(f"   Level {level}: {level_counts[level]:3d} processes")
    
    # Industry-specific analysis
    print(f"\n🏭 INDUSTRY-SPECIFIC PROCESSES:")
    ls_specific_total = len(categories['ls_only'])
    retail_specific_total = len(categories['retail_only']) 
    ci_specific_total = len(categories['ci_only'])
    
    print(f"   Life Science unique:   {ls_specific_total:3d} processes")
    print(f"   Retail unique:         {retail_specific_total:3d} processes") 
    print(f"   Cross Industry unique: {ci_specific_total:3d} processes")
    
    # Sample examples
    print(f"\n📝 SAMPLE UNIVERSAL PROCESSES (Level 1-2):")
    for code in sorted(categories['all_three']):
        if models['cross_industry'][code]['level'] <= 2:
            ci_name = models['cross_industry'][code]['name']
            ls_name = models['life_science'][code]['name'] 
            retail_name = models['retail'][code]['name']
            match_indicator = "✓" if ci_name == ls_name == retail_name else "≈"
            print(f"   {code} {match_indicator} {ci_name}")
            if ci_name != ls_name or ci_name != retail_name:
                if ci_name != ls_name:
                    print(f"      LS: {ls_name}")
                if ci_name != retail_name:
                    print(f"      RT: {retail_name}")
    
    print(f"\n📝 SAMPLE LIFE SCIENCE SPECIFIC PROCESSES:")
    ls_sample = sorted(categories['ls_only'])[:10]
    for code in ls_sample:
        name = models['life_science'][code]['name']
        level = models['life_science'][code]['level']
        print(f"   {code} (L{level}): {name}")
    
    print(f"\n📝 SAMPLE RETAIL SPECIFIC PROCESSES:")
    retail_sample = sorted(categories['retail_only'])[:10] 
    for code in retail_sample:
        name = models['retail'][code]['name']
        level = models['retail'][code]['level']
        print(f"   {code} (L{level}): {name}")
    
    conn.close()
    
    # Export detailed comparison to CSV
    export_detailed_comparison(models, categories)
    
    return categories, identical_names

def export_detailed_comparison(models, categories):
    """Export detailed comparison to CSV file."""
    
    print(f"\n💾 Exporting detailed comparison to 'pcf_three_model_comparison.csv'...")
    
    with open('pcf_three_model_comparison.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['code', 'presence', 'cross_industry_name', 'life_science_name', 'retail_name', 
                     'level', 'name_match', 'category']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        all_codes = set()
        for model_nodes in models.values():
            all_codes.update(model_nodes.keys())
        
        for code in sorted(all_codes):
            in_ci = code in models['cross_industry']
            in_ls = code in models['life_science'] 
            in_retail = code in models['retail']
            
            # Determine presence pattern
            presence = ""
            if in_ci: presence += "CI "
            if in_ls: presence += "LS "
            if in_retail: presence += "RT"
            presence = presence.strip()
            
            # Get names
            ci_name = models['cross_industry'].get(code, {}).get('name', '')
            ls_name = models['life_science'].get(code, {}).get('name', '')
            retail_name = models['retail'].get(code, {}).get('name', '')
            
            # Determine level (use first available)
            level = 0
            for model in models.values():
                if code in model:
                    level = model[code]['level']
                    break
            
            # Check name matching
            name_match = ""
            if in_ci and in_ls and in_retail:
                name_match = "ALL_IDENTICAL" if ci_name == ls_name == retail_name else "DIFFERENT"
            elif in_ci and in_ls:
                name_match = "CI_LS_MATCH" if ci_name == ls_name else "DIFFERENT"  
            elif in_ci and in_retail:
                name_match = "CI_RT_MATCH" if ci_name == retail_name else "DIFFERENT"
            elif in_ls and in_retail:
                name_match = "LS_RT_MATCH" if ls_name == retail_name else "DIFFERENT"
            
            # Determine category
            category = ""
            if code in categories['all_three']:
                category = "UNIVERSAL"
            elif code in categories['ci_ls_only']:
                category = "CI_LS_ONLY" 
            elif code in categories['ci_retail_only']:
                category = "CI_RETAIL_ONLY"
            elif code in categories['ls_retail_only']:
                category = "LS_RETAIL_ONLY"
            elif code in categories['ci_only']:
                category = "CI_SPECIFIC"
            elif code in categories['ls_only']:
                category = "LS_SPECIFIC"  
            elif code in categories['retail_only']:
                category = "RETAIL_SPECIFIC"
            
            writer.writerow({
                'code': code,
                'presence': presence,
                'cross_industry_name': ci_name,
                'life_science_name': ls_name, 
                'retail_name': retail_name,
                'level': level,
                'name_match': name_match,
                'category': category
            })

if __name__ == "__main__":
    print("🔍 COMPREHENSIVE APQC PCF THREE-MODEL COMPARISON")
    print("=" * 60)
    
    categories, identical_names = analyze_three_way_comparison()
    
    print(f"\n✅ Analysis complete! Check 'pcf_three_model_comparison.csv' for detailed results.")