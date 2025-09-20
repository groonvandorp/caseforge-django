# Helper Scripts

This folder contains temporary and helper scripts used for various development and maintenance tasks. Scripts are organized by category for better management.

## 📁 Folder Structure

### 🔢 PCF Management (`pcf_management/`)
Scripts for managing PCF IDs and cross-model comparisons:
- `add_pcf_ids_to_cross_industry.py` - Add PCF IDs to Cross Industry model
- `add_pcf_ids_to_retail.py` - Add PCF IDs to Retail model
- `check_pcf_ids_in_excel.py` - Verify PCF IDs in Excel files
- `compare_models_by_pcf_id.py` - Compare models using PCF ID matching
- `compare_three_pcf_models.py` - Three-way model comparison
- `find_ci_retail_matches.py` - Find matches between Cross Industry and Retail
- `find_pcf_id_matches.py` - General PCF ID matching utility

### 📊 Data Migration (`data_migration/`)
Scripts for copying data between process models:
- `copy_process_details_ci_to_ls.py` - Copy process details Cross Industry → Life Science
- `copy_process_details_ci_to_retail.py` - Copy process details Cross Industry → Retail
- `copy_process_details_pcf_based.py` - PCF-based process details copying
- `copy_usecase_candidates_ci_to_retail.py` - Copy use cases Cross Industry → Retail
- `copy_usecase_candidates_pcf_based.py` - PCF-based use case copying
- `migrate_documents.py` - Document migration utility
- `migrate_nodes.py` - Node migration utility
- `migrate_usecases.py` - Use case migration utility

### 🔍 Model Analysis (`model_analysis/`)
Scripts for analyzing and debugging process models:
- `check_leaf_nodes.py` - Analyze leaf node structure
- `check_leaf_nodes_debug.py` - Debug leaf node issues
- `identify_failed_nodes.py` - Find problematic nodes
- `fix_lifescience_hierarchy.py` - Fix Life Science model hierarchy

### 🧪 Testing Utilities (`testing_utilities/`)
Scripts for testing and system state capture:
- `test_embeddings.py` - Test embedding generation
- `capture_software_state.py` - Capture current system state

### 📥 Legacy Imports (`legacy_imports/`)
Scripts from earlier import and population processes:
- `import_lifescience_model.py` - Original Life Science model import
- `clear_lifescience_model.py` - Clear Life Science model data
- `generate_embeddings.py` - Legacy embedding generation
- `populate_usecase_metadata.py` - Legacy metadata population
- `retry_failed_usecase_nodes.py` - Retry failed use case generation

## 🚀 Usage Notes

### Running Scripts
Most scripts require Django setup and should be run from the project root:
```bash
cd /path/to/caseforge
python helper_scripts/category/script_name.py
```

### Import Path Fixes
When moving scripts to subdirectories, some may need Django path adjustments:
```python
import os
import sys
sys.path.append('..')  # Add parent directory to path
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "caseforge.settings")
```

### Categories
- **PCF Management**: Working with Process Classification Framework IDs
- **Data Migration**: Moving data between different process models
- **Model Analysis**: Debugging and analyzing process model structures
- **Testing Utilities**: Testing components and capturing system state
- **Legacy Imports**: Historical scripts from initial data population

## ⚠️ Important Notes

- These scripts are **temporary utilities** and may not be maintained long-term
- Always backup data before running migration scripts
- Test scripts in development environment first
- Some scripts may require specific database states or data to function properly
- Check script documentation and code before running

## 🔄 Maintenance

As new helper scripts are created:
1. Place them in the appropriate category folder
2. Update this README with script descriptions
3. Ensure proper Django setup if database access is needed
4. Add any special requirements or usage notes