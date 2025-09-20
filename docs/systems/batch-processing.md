# CaseForge Batch Processing Systems

This document provides comprehensive documentation for all batch processing systems in the CaseForge application.

## 📋 Overview

CaseForge uses OpenAI's Batch API for cost-effective mass generation of AI content across process models. The system is organized into specialized batch processing modules for different content types.

## 🏗️ Architecture

### Batch Processing Flow
```
1. Data Preparation → 2. JSONL Generation → 3. Batch Submission → 4. Monitoring → 5. Result Processing
```

### Core Components
- **Batch Generators**: Create and submit batch jobs
- **Monitors**: Track batch progress and completion
- **Test Scripts**: Validate functionality with limited datasets
- **Result Processors**: Parse and store batch results

## 📁 Organized Structure

### `batch_waste_by_type/` ⭐ **Current System**
**Purpose**: Generate individual waste type analysis using TIMWOOD+ framework

**Scripts**:
- `batch_generate_waste_by_type.py` - Main batch generator (12 waste types per process)
- `monitor_waste_by_type.py` - Monitor batch progress
- `test_waste_by_type.py` - Test with 2 processes × 3 waste types

**Features**:
- 12 separate API calls per process (Transportation, Inventory, Motion, Waiting, Overprocessing, Overproduction, Defects, Skills, Digital, Knowledge, Compliance, Communication)
- 3000 tokens per waste type analysis
- Separate NodeDocument storage per waste type
- Better filtering and search capabilities

**Usage**:
```bash
cd batch_waste_by_type/
python test_waste_by_type.py                    # Test with limited data
python batch_generate_waste_by_type.py         # Full generation
python monitor_waste_by_type.py                # Monitor progress
```

### `batch_waste_embeddings/`
**Purpose**: Generate embeddings for waste documents to enable semantic search

**Scripts**:
- `batch_generate_waste_embeddings.py` - Generate embeddings for all waste_* documents
- `monitor_waste_embeddings.py` - Monitor embedding generation
- `test_waste_embeddings.py` - Test embedding system setup

**Features**:
- Uses `text-embedding-3-small` model
- Processes all 12 waste document types
- Stores embeddings in NodeDocumentEmbedding model
- Enables semantic search across waste analyses

**Usage**:
```bash
cd batch_waste_embeddings/
python test_waste_embeddings.py                 # Test system setup
python batch_generate_waste_embeddings.py      # Generate embeddings
python monitor_waste_embeddings.py             # Monitor progress
```

### `batch_process_waste/` (Legacy)
**Purpose**: Original combined waste analysis approach

**Scripts**:
- `batch_generate_process_waste.py` - Combined waste analysis (superseded)
- `monitor_process_waste.py` - Monitor combined generation
- `test_waste_analysis.py` - Test combined approach

**Status**: Legacy system, superseded by `batch_waste_by_type/`

### `batch_process_details/`
**Purpose**: Generate detailed process descriptions

**Scripts**:
- `batch_generate_process_details.py` - Generate process detail documents

**Features**:
- Creates comprehensive process descriptions
- Foundation for other batch processes
- Prerequisite for waste analysis generation

### `batch_usecase_candidates/`
**Purpose**: Generate AI use case recommendations

**Scripts**:
- `batch_generate_usecase_candidates.py` - Generate AI use case candidates
- `batch_generate_usecase_specs.py` - Generate detailed use case specifications
- `monitor_usecase_batch.py` - Monitor use case generation

**Features**:
- AI-driven use case identification
- Complexity and impact scoring
- Detailed implementation specifications

### `batch_embeddings/`
**Purpose**: General embedding generation

**Scripts**:
- `batch_generate_embeddings.py` - General node embeddings
- `batch_generate_usecase_embeddings.py` - Use case embeddings
- `monitor_embeddings_batch.py` - Monitor embedding generation
- `test_embeddings.py` - Test embedding systems

**Features**:
- Node-level embeddings for semantic search
- Use case embeddings for recommendations
- Multiple embedding model support

### `batch_processing/`
**Purpose**: General batch utilities

**Scripts**:
- `monitor_batch.py` - General batch monitoring utilities

## 🔧 Configuration

### Environment Variables
```bash
# Required in AdminSettings or environment
OPENAI_API_KEY=sk-...                  # OpenAI API access
```

### Batch Settings
- **Model**: `gpt-5` (configurable per generator)
- **Temperature**: 1.0 (creative generation)
- **Token Limits**: 3000-8000 depending on content type
- **Completion Window**: 24 hours
- **Cost Optimization**: 50% cheaper than real-time API

## 📊 Monitoring & Management

### Real-time Monitoring
```bash
# Monitor specific batch
python monitor_waste_by_type.py

# General batch monitoring
python batch_processing/monitor_batch.py
```

### Batch Status Tracking
- **Submitted**: Batch created and submitted to OpenAI
- **Validating**: OpenAI validating input format
- **In Progress**: Processing requests
- **Finalizing**: Completing and preparing results
- **Completed**: Ready for result processing
- **Failed/Expired**: Error states requiring intervention

### Progress Indicators
- Total requests vs completed
- Success/failure rates
- Estimated completion time
- Token usage tracking

## 🎯 Workflow Examples

### Complete Waste Analysis Workflow
```bash
# 1. Ensure process details exist
cd batch_process_details/
python batch_generate_process_details.py

# 2. Generate waste analysis by type
cd ../batch_waste_by_type/
python test_waste_by_type.py           # Test first
python batch_generate_waste_by_type.py # Full generation

# 3. Monitor progress
python monitor_waste_by_type.py

# 4. Generate embeddings for search
cd ../batch_waste_embeddings/
python batch_generate_waste_embeddings.py

# 5. Monitor embedding generation
python monitor_waste_embeddings.py
```

### Use Case Generation Workflow
```bash
# 1. Generate use case candidates
cd batch_usecase_candidates/
python batch_generate_usecase_candidates.py

# 2. Generate detailed specifications
python batch_generate_usecase_specs.py

# 3. Generate use case embeddings
cd ../batch_embeddings/
python batch_generate_usecase_embeddings.py
```

## 🔍 Data Models Integration

### Waste Analysis Storage
```python
# Individual waste documents
NodeDocument.objects.filter(document_type='waste_transportation')
NodeDocument.objects.filter(document_type='waste_inventory')
# ... (12 waste types total)

# Waste document embeddings
NodeDocumentEmbedding.objects.filter(document__document_type__startswith='waste_')
```

### Process Details Storage
```python
# Process descriptions
NodeDocument.objects.filter(document_type='process_details')

# Node embeddings
NodeEmbedding.objects.all()
```

### Use Case Storage
```python
# AI use case candidates
NodeUsecaseCandidate.objects.all()

# Use case specifications
NodeDocument.objects.filter(document_type='usecase_spec')
```

## 🚨 Troubleshooting

### Common Issues

1. **Batch Fails - Invalid API Key**
   ```bash
   # Check AdminSettings
   python manage.py shell -c "from core.models import AdminSettings; print(AdminSettings.get_setting('openai_api_key')[:10])"
   ```

2. **No Process Details Found**
   ```bash
   # Generate process details first
   cd batch_process_details/
   python batch_generate_process_details.py
   ```

3. **Batch Stuck in Validating**
   - Check JSONL format in batch input files
   - Verify token limits not exceeded
   - Check OpenAI API status

4. **Results Processing Fails**
   - Check database connectivity
   - Verify disk space for batch output files
   - Review batch result format

### Debug Tools
```bash
# Check batch input files
ls -la batch_waste_by_type/batch_waste_by_type/
cat batch_waste_by_type/batch_waste_by_type/input_*.jsonl | head -5

# Check database state
python manage.py shell -c "from core.models import NodeDocument; print(f'Waste docs: {NodeDocument.objects.filter(document_type__startswith=\"waste_\").count()}')"

# Monitor OpenAI usage
# Use OpenAI dashboard for quota and billing monitoring
```

## 📈 Performance & Scaling

### Batch Size Optimization
- **Small batches**: 50-100 requests (testing)
- **Medium batches**: 500-1000 requests (typical)
- **Large batches**: 2000+ requests (full model processing)

### Cost Management
- Batch API: ~50% cost savings vs real-time
- Embedding generation: Optimized for bulk processing
- Token limit optimization per content type

### Processing Time
- **Validation**: 5-10 minutes
- **Processing**: 2-24 hours (depends on queue)
- **Result Processing**: 5-30 minutes (depends on batch size)

## 🔗 Integration Points

### Database Integration
- All results stored in appropriate Django models
- Automatic relationship mapping (nodes, documents, embeddings)
- Transaction safety for batch result processing

### Search Integration
- Embeddings enable semantic search
- Document type filtering for targeted search
- Cross-model process matching via PCF IDs

### API Integration
- Results accessible via Django REST API
- Real-time search and filtering
- Batch status monitoring endpoints

## 📚 Related Documentation

- [Database Backup Systems](./database-backup.md)
- [Deployment Guide](../deployment/README.md)
- [API Documentation](../api/README.md)
- [OpenAI Batch API Documentation](https://platform.openai.com/docs/guides/batch)

---

## 🆘 Support

For batch processing issues:
1. Check script logs and error output
2. Verify OpenAI API key and quota
3. Review troubleshooting section above
4. Contact development team with batch ID and error details