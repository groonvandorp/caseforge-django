# CaseForge MCP Server

**Model Context Protocol server providing Claude Desktop integration with the CaseForge process framework and AI use case system.**

## 📋 Overview

The **Onwell MCP Server** enables direct integration between Claude Desktop and the CaseForge Django backend, allowing natural language queries to access process data, AI use cases, and technology recommendations through the Model Context Protocol.

### Key Capabilities
- **Process Discovery**: Search and explore APQC PCF hierarchies
- **AI Use Case Access**: Query generated use case candidates and specifications
- **Semantic Search**: Vector-based search across processes and documents
- **Technology Recommendations**: Build Advisor integration for implementation guidance
- **Portfolio Management**: Access to saved use case portfolios

## 🏗️ Architecture

### Integration Flow
```
Claude Desktop ←→ MCP Server ←→ Django REST API ←→ CaseForge Database
      ↓               ↓                ↓                    ↓
  Natural Lang.   MCP Protocol    HTTP/JSON           PostgreSQL/SQLite
```

### Authentication Flow
```
MCP Server → Django JWT Auth → API Access Token → Authenticated Requests
```

## 📁 Directory Structure

```
services/mcp/
├── 📄 README.md                     # MCP server documentation
├── 📄 package.json                  # Node.js dependencies
├── 📄 tsconfig.json                 # TypeScript configuration
├── 📄 mcp-config.json              # MCP server metadata
├── 📁 src/
│   └── index.ts                     # Main server implementation (TypeScript)
├── 📁 dist/
│   └── index.js                     # Compiled JavaScript
├── 📄 .env.example                  # Environment template
└── 📄 .env                         # Environment configuration
```

## 🚀 Quick Start

### 1. MCP Server Setup
```bash
# Navigate to MCP server directory
cd services/mcp/

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env with your Django backend settings

# Build TypeScript
npm run build
```

### 2. Django Backend Setup
```bash
# Ensure Django backend is running
cd ../../  # Back to Django project root
python manage.py runserver  # Should be running on port 8000
```

### 3. Claude Desktop Configuration
Add to Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "caseforge": {
      "command": "node",
      "args": [
        "/path/to/your/project/services/mcp/dist/index.js"
      ],
      "env": {
        "DJANGO_API_URL": "http://localhost:8000/api",
        "DJANGO_USERNAME": "gruhno",
        "DJANGO_PASSWORD": "wollw"
      }
    }
  }
}
```

### 4. Test Connection
```bash
# Start MCP server in development mode
cd services/mcp/
npm run dev

# Restart Claude Desktop
# Test with natural language queries in Claude Desktop
```

## 🔧 Available Tools

### Process Management Tools

#### `search_processes`
**Purpose**: Search for process nodes by name or code
**Usage**: "Search for processes related to customer research"
**Parameters**:
- `query` (string): Search term
- `model_key` (optional): Specific model to search

#### `get_process_details`
**Purpose**: Get detailed information about a specific process node
**Usage**: "Get details for process node 123"
**Parameters**:
- `node_id` (number): Process node ID

#### `list_models`
**Purpose**: List all available process models
**Usage**: "What process models are available?"
**Returns**: Cross Industry, Life Science, Retail models

#### `get_model_tree`
**Purpose**: Get hierarchical tree structure for a model
**Usage**: "Show me the tree structure for Life Science model"
**Parameters**:
- `model_key` (string): Model identifier

#### `get_node_children`
**Purpose**: Get child nodes for a specific process
**Usage**: "Show me the child processes of node 456"
**Parameters**:
- `node_id` (number): Parent node ID

### AI Use Case Tools

#### `list_use_cases`
**Purpose**: List AI use case candidates for a process
**Usage**: "Show me AI use cases for this process"
**Parameters**:
- `node_id` (number): Process node ID

#### `get_use_case_details`
**Purpose**: Get detailed information about a specific use case
**Usage**: "Tell me more about use case 789"
**Parameters**:
- `use_case_id` (number): Use case candidate ID

#### `get_build_advice`
**Purpose**: Get technology recommendations for implementing a use case
**Usage**: "What technology should I use for use case 789?"
**Parameters**:
- `use_case_id` (number): Use case candidate ID

### Search & Discovery Tools

#### `search_semantic`
**Purpose**: Perform semantic search across processes and use cases
**Usage**: "Search semantically for 'predictive analytics in supply chain'"
**Parameters**:
- `query` (string): Search query
- `limit` (optional): Number of results (default: 10)

#### `list_portfolios`
**Purpose**: List all portfolios and their items
**Usage**: "Show me all saved portfolios"
**Returns**: User portfolios with use case collections

## 🔐 Configuration

### Environment Variables
```bash
# Django Backend Configuration
DJANGO_API_URL=http://localhost:8000/api
DJANGO_USERNAME=gruhno
DJANGO_PASSWORD=wollw

# Optional: Override defaults
DJANGO_TIMEOUT=30000
```

### Authentication
- **Method**: JWT-based authentication
- **Credentials**: Django user account
- **Auto-renewal**: Token refreshed automatically
- **Security**: Credentials in environment variables only

## 💬 Usage Examples

### Natural Language Queries

#### Process Discovery
```
User: "Search for processes related to customer research"
→ search_processes tool called with query="customer research"

User: "Show me all child processes under 'Develop and manage products'"
→ search_processes + get_node_children tools used
```

#### AI Use Case Exploration
```
User: "What AI use cases are available for customer data analysis?"
→ search_processes + list_use_cases tools combined

User: "Tell me about use case 123 and what technologies I need"
→ get_use_case_details + get_build_advice tools used
```

#### Technology Recommendations
```
User: "I want to implement predictive analytics. What should I use?"
→ search_semantic + get_build_advice for relevant use cases

User: "Show me all portfolios with machine learning use cases"
→ list_portfolios + semantic filtering
```

### Advanced Queries
```
User: "Find all processes in the Life Science model that deal with data"
→ get_model_tree + search_processes with model filtering

User: "What's the most complex AI use case for supply chain optimization?"
→ search_semantic + list_use_cases with complexity sorting
```

## 🔍 Integration Points

### Django REST API Endpoints
```
GET /api/process-models/                 # List models
GET /api/nodes/{id}/                     # Get process node
GET /api/nodes/{id}/children/            # Get child nodes
GET /api/search/processes/               # Process search
GET /api/search/semantic/                # Semantic search
GET /api/nodes/{id}/usecase-candidates/  # Use cases for node
GET /api/usecase-candidates/{id}/        # Use case details
GET /api/build-advice/{id}/              # Technology recommendations
GET /api/portfolios/                     # User portfolios
```

### Data Models Accessed
```python
# Core process data
ProcessModel, ProcessModelVersion, ProcessNode

# AI-generated content
NodeDocument (process_details, waste_*, usecase_spec)
NodeUsecaseCandidate, PortfolioItem

# Search & embeddings
NodeEmbedding, NodeDocumentEmbedding

# Technology recommendations
Technology, TechnologyCapability, UseCaseTechnologyRecommendation
```

## 🚨 Troubleshooting

### Common Issues

1. **MCP Server Not Connecting**
   ```bash
   # Check Django backend is running
   curl http://localhost:8000/api/process-models/

   # Check MCP server build
   cd services/mcp/
   npm run build
   ```

2. **Authentication Failures**
   ```bash
   # Verify credentials in .env
   cat services/mcp/.env

   # Test Django authentication
   curl -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"username":"gruhno","password":"wollw"}'
   ```

3. **Claude Desktop Configuration Issues**
   ```bash
   # Check config file location
   # macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
   # Windows: %APPDATA%\Claude\claude_desktop_config.json

   # Verify path to MCP server
   ls -la /path/to/your/project/services/mcp/dist/index.js
   ```

4. **Tool Not Found Errors**
   ```bash
   # Rebuild TypeScript
   cd services/mcp/
   npm run build

   # Check tool definitions in source
   grep -n "name:" src/index.ts
   ```

### Debug Mode
```bash
# Run MCP server with debug output
cd services/mcp/
DEBUG=mcp:* npm run dev

# Check Django logs
cd ../../
python manage.py runserver --verbosity=2
```

### Performance Issues
```bash
# Check API response times
curl -w "@curl-format.txt" http://localhost:8000/api/nodes/123/

# Monitor database queries
# Add logging to Django settings.py for database queries
```

## 🔧 Development

### Adding New Tools
1. **Define tool in `getTools()` method**:
   ```typescript
   {
     name: 'my_new_tool',
     description: 'Description of what the tool does',
     inputSchema: {
       type: 'object',
       properties: {
         param1: { type: 'string', description: 'Parameter description' }
       },
       required: ['param1']
     }
   }
   ```

2. **Implement tool handler**:
   ```typescript
   case 'my_new_tool':
     return await this.handleMyNewTool(args.param1);
   ```

3. **Create handler method**:
   ```typescript
   private async handleMyNewTool(param1: string) {
     const response = await this.api.get(`/my-endpoint/${param1}`);
     return { content: [{ type: 'text', text: response.data }] };
   }
   ```

### Testing Tools
```bash
# Test individual API endpoints
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/nodes/123/

# Test MCP server responses
cd services/mcp/
npm run dev
# Use MCP inspector or Claude Desktop for testing
```

### Code Structure
```typescript
class OnwellMCPServer {
  server: Server;           // MCP SDK server instance
  api: AxiosInstance;       // Django API client
  authToken: string;        // JWT authentication token

  setupHandlers()           // Initialize MCP handlers
  authenticate()            // Handle Django authentication
  getTools()               // Define available tools
  handleToolCall()         // Route tool calls to handlers
}
```

## 📈 Performance Optimization

### Caching Strategy
```typescript
// Cache frequently accessed data
private cache = new Map<string, any>();

private async getCachedData(key: string, fetcher: () => Promise<any>) {
  if (this.cache.has(key)) {
    return this.cache.get(key);
  }
  const data = await fetcher();
  this.cache.set(key, data);
  return data;
}
```

### Request Optimization
```typescript
// Batch API calls when possible
const [nodes, useCases] = await Promise.all([
  this.api.get(`/nodes/${nodeId}/`),
  this.api.get(`/nodes/${nodeId}/usecase-candidates/`)
]);
```

## 🔗 Related Documentation

- [CaseForge Development Guide](../../DEVELOPMENT_GUIDE.md)
- [Django REST API Documentation](../api/README.md)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/introduction)
- [Claude Desktop Configuration Guide](https://docs.anthropic.com/claude/docs/claude-desktop)

## 🆘 Support

### For MCP Server Issues:
1. Check Django backend connectivity
2. Verify authentication credentials
3. Review Claude Desktop configuration
4. Check MCP server logs and build status

### For Tool Development:
1. Review TypeScript compilation errors
2. Test API endpoints independently
3. Validate tool input/output schemas
4. Use MCP inspector for debugging

---

**🎯 The MCP server bridges natural language interaction with CaseForge's comprehensive process intelligence, enabling seamless AI-powered business process analysis through Claude Desktop.**