#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios, { AxiosInstance } from 'axios';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

interface AuthResponse {
  access: string;
  refresh: string;
}

class OnwellMCPServer {
  private server: Server;
  private api: AxiosInstance;
  private authToken: string | null = null;

  constructor() {
    this.server = new Server(
      {
        name: 'onwell-caseforge',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    // Initialize API client
    this.api = axios.create({
      baseURL: process.env.DJANGO_API_URL || 'http://localhost:8000/api',
      timeout: parseInt(process.env.DJANGO_TIMEOUT || '30000'),
    });

    this.setupHandlers();
    this.authenticate();
  }

  private async authenticate(): Promise<void> {
    try {
      const response = await this.api.post<AuthResponse>('/auth/token/', {
        username: process.env.DJANGO_USERNAME || 'gruhno',
        password: process.env.DJANGO_PASSWORD || 'wollw',
      });

      this.authToken = response.data.access;

      // Set auth header for future requests
      this.api.defaults.headers.common['Authorization'] = `Bearer ${this.authToken}`;

      console.error('✅ Authenticated with Django backend');
    } catch (error) {
      console.error('❌ Authentication failed:', error);
      throw error;
    }
  }

  private setupHandlers(): void {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: 'search_processes',
            description: 'Search for process nodes by name or code',
            inputSchema: {
              type: 'object',
              properties: {
                query: {
                  type: 'string',
                  description: 'Search term for process name or code',
                },
                model_key: {
                  type: 'string',
                  description: 'Optional model key to search within (cross_industry, life_science, retail)',
                },
              },
              required: ['query'],
            },
          },
          {
            name: 'get_process_details',
            description: 'Get detailed information about a specific process node',
            inputSchema: {
              type: 'object',
              properties: {
                node_id: {
                  type: 'number',
                  description: 'Process node ID',
                },
              },
              required: ['node_id'],
            },
          },
          {
            name: 'list_models',
            description: 'List all available process models',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
          {
            name: 'get_model_tree',
            description: 'Get hierarchical tree structure for a model',
            inputSchema: {
              type: 'object',
              properties: {
                model_key: {
                  type: 'string',
                  description: 'Model identifier (cross_industry, life_science, retail)',
                },
              },
              required: ['model_key'],
            },
          },
          {
            name: 'get_node_children',
            description: 'Get child nodes for a specific process',
            inputSchema: {
              type: 'object',
              properties: {
                node_id: {
                  type: 'number',
                  description: 'Parent node ID',
                },
              },
              required: ['node_id'],
            },
          },
          {
            name: 'list_use_cases',
            description: 'List AI use case candidates for a process',
            inputSchema: {
              type: 'object',
              properties: {
                node_id: {
                  type: 'number',
                  description: 'Process node ID',
                },
              },
              required: ['node_id'],
            },
          },
          {
            name: 'get_use_case_details',
            description: 'Get detailed information about a specific use case',
            inputSchema: {
              type: 'object',
              properties: {
                use_case_id: {
                  type: 'number',
                  description: 'Use case candidate ID',
                },
              },
              required: ['use_case_id'],
            },
          },
          {
            name: 'get_build_advice',
            description: 'Get technology recommendations for implementing a use case',
            inputSchema: {
              type: 'object',
              properties: {
                use_case_id: {
                  type: 'number',
                  description: 'Use case candidate ID',
                },
              },
              required: ['use_case_id'],
            },
          },
          {
            name: 'list_portfolios',
            description: 'List all portfolios and their items',
            inputSchema: {
              type: 'object',
              properties: {},
            },
          },
        ],
      };
    });

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'search_processes':
            return await this.handleSearchProcesses(args?.query as string, args?.model_key as string);

          case 'get_process_details':
            return await this.handleGetProcessDetails(args?.node_id as number);

          case 'list_models':
            return await this.handleListModels();

          case 'get_model_tree':
            return await this.handleGetModelTree(args?.model_key as string);

          case 'get_node_children':
            return await this.handleGetNodeChildren(args?.node_id as number);

          case 'list_use_cases':
            return await this.handleListUseCases(args?.node_id as number);

          case 'get_use_case_details':
            return await this.handleGetUseCaseDetails(args?.use_case_id as number);

          case 'get_build_advice':
            return await this.handleGetBuildAdvice(args?.use_case_id as number);

          case 'list_portfolios':
            return await this.handleListPortfolios();

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error executing ${name}: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
        };
      }
    });
  }

  private async handleSearchProcesses(query: string, modelKey?: string) {
    const params: any = { search: query };
    if (modelKey) params.model_key = modelKey;

    const response = await this.api.get('/nodes/', { params });
    const nodes = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `Found ${nodes.length} processes:\n\n${nodes.map((node: any) =>
            `**${node.code}** - ${node.name}\n*Level ${node.level}* | Model: ${node.model_version?.model_name || 'Unknown'}`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  private async handleGetProcessDetails(nodeId: number) {
    const [nodeResponse, documentsResponse] = await Promise.all([
      this.api.get(`/nodes/${nodeId}/`),
      this.api.get(`/documents/by_node/`, { params: { node_id: nodeId } })
    ]);

    const node = nodeResponse.data;
    const documents = documentsResponse.data.results || documentsResponse.data;

    let details = `# ${node.name}\n\n`;
    details += `**Code:** ${node.code}\n`;
    details += `**Level:** ${node.level}\n`;
    details += `**Model:** ${node.model_version?.model_name || 'Unknown'}\n\n`;

    if (node.description) {
      details += `**Description:**\n${node.description}\n\n`;
    }

    if (documents.length > 0) {
      details += `**Available Documents:**\n`;
      documents.forEach((doc: any) => {
        details += `- ${doc.document_type}: ${doc.title || 'Untitled'}\n`;
      });
    }

    return {
      content: [{ type: 'text', text: details }],
    };
  }

  private async handleListModels() {
    const response = await this.api.get('/models/');
    const models = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `Available Process Models:\n\n${models.map((model: any) =>
            `**${model.name}** (${model.key})\n${model.description || 'No description'}`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  private async handleGetModelTree(modelKey: string) {
    const response = await this.api.get('/nodes/roots/', {
      params: { model_key: modelKey }
    });
    const roots = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `Root processes for ${modelKey}:\n\n${roots.map((node: any) =>
            `**${node.code}** - ${node.name}\n*${node.children_count || 0} children*`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  private async handleGetNodeChildren(nodeId: number) {
    const response = await this.api.get(`/nodes/${nodeId}/children/`);
    const children = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `Child processes:\n\n${children.map((node: any) =>
            `**${node.code}** - ${node.name}\n*Level ${node.level}*`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  private async handleListUseCases(nodeId: number) {
    const response = await this.api.get('/usecases/by_node/', {
      params: { node_id: nodeId }
    });
    const useCases = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `AI Use Cases:\n\n${useCases.map((useCase: any) =>
            `**${useCase.candidate_uid}** - ${useCase.title}\n*${useCase.ai_category}* | Complexity: ${useCase.complexity_score}/10`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  private async handleGetUseCaseDetails(useCaseId: number) {
    const response = await this.api.get(`/usecases/${useCaseId}/`);
    const useCase = response.data;

    let details = `# ${useCase.title}\n\n`;
    details += `**Category:** ${useCase.ai_category}\n`;
    details += `**Complexity:** ${useCase.complexity_score}/10\n`;
    details += `**Impact:** ${useCase.business_impact}/10\n\n`;

    if (useCase.description) {
      details += `**Description:**\n${useCase.description}\n\n`;
    }

    if (useCase.implementation_approach) {
      details += `**Implementation Approach:**\n${useCase.implementation_approach}\n\n`;
    }

    return {
      content: [{ type: 'text', text: details }],
    };
  }

  private async handleGetBuildAdvice(useCaseId: number) {
    const response = await this.api.get(`/build-advice/${useCaseId}/`);
    const advice = response.data;

    return {
      content: [
        {
          type: 'text',
          text: `Technology Recommendations:\n\n${JSON.stringify(advice, null, 2)}`,
        },
      ],
    };
  }

  private async handleListPortfolios() {
    const response = await this.api.get('/portfolios/');
    const portfolios = response.data.results || response.data;

    return {
      content: [
        {
          type: 'text',
          text: `User Portfolios:\n\n${portfolios.map((portfolio: any) =>
            `**${portfolio.name}**\n${portfolio.description || 'No description'}\n*${portfolio.items?.length || 0} items*`
          ).join('\n\n')}`,
        },
      ],
    };
  }

  async run(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('🚀 Onwell MCP Server running on stdio');
  }
}

const server = new OnwellMCPServer();
server.run().catch(console.error);