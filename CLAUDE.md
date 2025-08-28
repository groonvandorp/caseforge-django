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