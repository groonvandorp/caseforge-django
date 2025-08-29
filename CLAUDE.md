# CaseForge Build Advisor Implementation Notes

## Build Advisor Implementation Status (2025-08-28)

### ✅ PHASE 2 COMPLETE: Build Advisor API & Basic UI
**Status**: Fully operational Build Advisor with API and initial React component integration

#### Backend Implementation Complete
- **API Layer**: 8 new serializers, 5 ViewSets, 2 function-based views in `/api/serializers.py` and `/api/views.py`
- **URL Routing**: All Build Advisor endpoints registered in `/api/urls.py`
- **Django Admin**: Complete admin interface for technology inventory management in `/core/admin.py`
- **Technology Matching**: Keyword-based algorithm in `get_build_advice()` function

#### Frontend Implementation Complete  
- **BuildAdvisorPanel Component**: Rich UI component in `/frontend/src/components/BuildAdvisor/BuildAdvisorPanel.tsx`
- **Composer Integration**: Build Advisor panel integrated into each use case card in Composer view
- **Material-UI Components**: Comprehensive design with accordions, chips, progress indicators

#### Current Data State
- **Technologies**: 7 (GPT-4 Turbo, Azure services, Apache Airflow, Databricks, Pinecone)
- **Vendors**: 16 (Microsoft, OpenAI, Apache, Google, etc.)
- **Categories**: 9 (AI/ML Platforms, NLP & Language, Process Automation, etc.)
- **Capabilities**: 20 (Text Extraction, Machine Learning, Anomaly Detection, etc.)
- **Use Case → Technology Recommendations**: 4 (minimal dataset)

### 🚧 NEXT PHASE: Full Build Advisor Workspace

#### User's Vision for Enhanced UX
**New Approach**: Dedicated full-page Build Advisor instead of embedded panel
- **Left Side**: Complete use case information (description, impact, complexity, metadata)
- **Right Side**: Technology selection workspace with category-based clicking
- **Navigation**: "Build Solution" button on use case cards in Composer → `/build-advisor/:usecaseId`
- **Solution Building**: Accumulate selected technologies into coherent solution stack
- **Persistence**: Save technology stack with reference to AI use case

#### Implementation Requirements
1. Create full-page Build Advisor view component
2. Add navigation from Composer use case cards  
3. Implement category-based technology selection interface
4. Add solution stack persistence and management
5. Populate more technology data and recommendations

### Technical Architecture

#### API Endpoints
- `GET /api/build-advice/{use_case_id}/` - Get recommendations for use case
- `GET /api/technology-landscape/` - Get all technologies with filtering
- `GET /api/technology-categories/` - Get technology categories
- `GET /api/vendors/` - Get vendor information
- `GET /api/technologies/` - Get technologies with search/filter
- `GET /api/capabilities/` - Get technology capabilities

#### Key Models
- **Technology**: Core technology entities (tools, services, platforms)
- **TechnologyCategory**: Hierarchical categorization system
- **Vendor**: Technology providers with partnership status
- **TechnologyCapability**: What technologies can do
- **UseCaseTechnologyRecommendation**: AI-generated recommendations with scoring
- **ImplementationPattern**: Reusable solution architectures
- **OrganizationTechnologyInventory**: Track existing technology assets

### Authentication & User Management

#### Current User Setup
- **User**: gruhno (gruhno@gmail.com) with password 'wollw'
- **Model Access**: Full access to all 5 process models
- **Server Status**: Django (port 8000) and React (port 3000) running
- **Login**: Working authentication with JWT tokens

### Data Population Strategy
- **populate_initial_technologies.py**: Script exists but only partially executed
- **Technology Matching Algorithm**: Capability-keyword based matching implemented
- **Auto-Population Sources**: GitHub API, Cloud Provider APIs, Package registries documented

---

# APQC PCF Model Management Notes

## Critical Issues to Remember

### Root Node Formatting Problem
- **Issue**: The 1.0, 2.0, 3.0, etc. formatted root nodes are problematic and consistently cause issues
- **Context**: These appear in Excel sheet names and as root node codes in the APQC Life Science model
- **Impact**: Creates parsing and hierarchy problems in the import process
- **Date Noted**: 2025-08-28
- **Status**: Known issue to address in future imports

## Project History

### PCF ID Implementation and Cross-Model Data Copy (2025-08-28)
**MAJOR SUCCESS**: Implemented correct PCF ID-based matching and data copying

#### PCF ID Implementation
- Modified import script to capture PCF IDs from Excel files
- PCF IDs are 5-digit numbers (e.g., 10002, 17040, 19945) 
- Stored as NodeAttribute with key='pcf_id'
- **Cross Industry**: Added PCF IDs to 1,921 existing nodes (100% coverage)
- **Life Science**: Re-imported 1,950 nodes with PCF IDs (100% coverage)

#### Correct Matching Implementation
- **User Correction**: "first rule is: they must have the same PCF-ID the five digit number, and same name, and same description, the numbering 1.1.1.1.... is not important"
- Found **1,735 identical nodes** between Cross Industry and Life Science using PCF ID + name + description
- 89% match rate (1,735 out of 1,921 CI nodes)

#### Data Copy Results
**Cross Industry → Life Science:**
- **Process Details**: Copied 1,410 process details (100% success rate)
- **AI Usecase Candidates**: Copied 13,111 usecase candidates (100% success rate)

**Cross Industry → Retail:**
- **Process Details**: Copied 1,059 process details (100% success rate)
- **AI Usecase Candidates**: Copied 9,848 usecase candidates (100% success rate)

**Final State:**
- **Cross Industry**: 1,552 process details, 14,437 AI candidates (completely preserved)
- **Life Science**: 1,410 process details, 13,111 AI candidates (from 0)
- **Retail**: 1,060 process details, 9,848 AI candidates (from 1/0)
- **User Ownership**: All copied content assigned to gruhno@gmail.com for visibility

### Level 5 Node Display Fix
- Fixed ProcessNodeTreeSerializer depth limit from >=4 to >=6
- Allows level 5 nodes to display in UI

### Process Details Copy Operations
- Successfully copied 1,178 process details from Cross Industry to Life Science
- Fixed user ownership issues (admin → gruhno@gmail.com)
- **Important**: Original copy was based on wrong criteria (hierarchical codes)
- **Correction**: Must use PCF ID + name + description matching

## Database Schema Notes

### Key Models
- ProcessNode: Core node structure with hierarchical codes
- NodeAttribute: Flexible key-value storage for PCF IDs
- NodeDocument: Process details and AI-generated content
- User ownership critical for content visibility

### PCF ID Storage
- Stored in NodeAttribute table with key='pcf_id'
- Value contains 5-digit PCF identifier
- Enables proper cross-model process matching