import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { 
  User, ProcessModel, ProcessModelVersion, ProcessNode, NodeDocument,
  NodeUsecaseCandidate, Portfolio, LoginCredentials, SignupData, AuthResponse
} from '../types';

class ApiService {
  private apiClient: AxiosInstance;

  constructor() {
    this.apiClient = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add auth token to requests
    this.apiClient.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle auth errors
    this.apiClient.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response: AxiosResponse<AuthResponse> = await this.apiClient.post('/auth/token/', credentials);
    return response.data;
  }

  async signup(data: SignupData): Promise<{ message: string }> {
    const response = await this.apiClient.post('/auth/signup/', data);
    return response.data;
  }

  async getCurrentUser(): Promise<User> {
    const response: AxiosResponse<User> = await this.apiClient.get('/auth/me/');
    return response.data;
  }

  // Process Models
  async getModels(): Promise<ProcessModel[]> {
    console.log('API: Fetching models...');
    const response = await this.apiClient.get('/models/');
    console.log('API: Raw response:', response.data);
    const models = response.data.results || response.data;
    console.log('API: Parsed models:', models);
    return models;
  }

  async getVersions(modelKey?: string): Promise<ProcessModelVersion[]> {
    const params = modelKey ? { model_key: modelKey } : {};
    const response = await this.apiClient.get('/versions/', { params });
    return response.data.results || response.data;
  }

  // Process Navigation
  async getRoots(modelKey: string): Promise<ProcessNode[]> {
    const response = await this.apiClient.get('/nodes/roots/', {
      params: { model_key: modelKey }
    });
    return response.data.results || response.data;
  }

  async getNode(nodeId: number): Promise<ProcessNode> {
    const response: AxiosResponse<ProcessNode> = await this.apiClient.get(`/nodes/${nodeId}/`);
    return response.data;
  }

  async getChildren(nodeId: number): Promise<ProcessNode[]> {
    const response = await this.apiClient.get(`/nodes/${nodeId}/children/`);
    return response.data.results || response.data;
  }

  async getNodeByCode(code: string, modelKey: string): Promise<ProcessNode> {
    try {
      const response: AxiosResponse<ProcessNode> = await this.apiClient.get(`/nodes/by-code/${code}/`, {
        params: { model_key: modelKey }
      });
      return response.data;
    } catch (error) {
      console.log(`Direct lookup failed for code ${code}, trying alternative search...`);
      // Fallback: search through the tree structure
      return await this.findNodeByCodeInTree(code, modelKey);
    }
  }

  private async findNodeByCodeInTree(code: string, modelKey: string): Promise<ProcessNode> {
    // Start with root nodes and search recursively
    const roots = await this.getRoots(modelKey);
    
    const searchInNodes = async (nodes: ProcessNode[]): Promise<ProcessNode | null> => {
      for (const node of nodes) {
        if (node.code === code) {
          return node;
        }
        
        // Search in children if not a leaf node
        if (!node.is_leaf && node.children_count > 0) {
          try {
            const children = await this.getChildren(node.id);
            const found = await searchInNodes(children);
            if (found) return found;
          } catch (childError) {
            console.error(`Failed to load children for node ${node.id}:`, childError);
          }
        }
      }
      return null;
    };

    const foundNode = await searchInNodes(roots);
    if (!foundNode) {
      throw new Error(`Node with code ${code} not found in tree`);
    }
    
    return foundNode;
  }

  // Documents
  async getDocumentsByNode(nodeId: number, documentType?: string): Promise<NodeDocument[]> {
    const params: any = { node_id: nodeId };
    if (documentType) params.document_type = documentType;
    
    const response = await this.apiClient.get('/documents/by_node/', { params });
    return response.data.results || response.data;
  }

  async saveDocument(document: Partial<NodeDocument>): Promise<NodeDocument> {
    const response: AxiosResponse<NodeDocument> = await this.apiClient.post('/documents/', document);
    return response.data;
  }

  async deleteProcessDetails(nodeId: number): Promise<{ message: string; node_id: number; node_code: string; node_name: string }> {
    const response = await this.apiClient.delete(`/nodes/${nodeId}/delete_details/`);
    return response.data;
  }

  async generateUsecaseCandidates(nodeId: number, includeBranch = true, crossCategory = true): Promise<{
    message: string;
    task_id: string;
    node_id: number;
    node_code: string;
    node_name: string;
    status: string;
  }> {
    const response = await this.apiClient.post(`/nodes/${nodeId}/generate_usecases/`, {
      include_branch: includeBranch,
      cross_category: crossCategory
    });
    return response.data;
  }

  async getTaskStatus(taskId: string): Promise<{
    task_id: string;
    status: string;
    ready: boolean;
    success?: boolean;
    result?: any;
    error?: string;
    info?: {
      current: number;
      total: number;
      status: string;
    };
  }> {
    const response = await this.apiClient.get(`/nodes/task-status/${taskId}/`);
    return response.data;
  }

  // Use Case Candidates
  async getUsecasesByNode(nodeId: number): Promise<NodeUsecaseCandidate[]> {
    const response = await this.apiClient.get('/usecases/by_node/', {
      params: { node_id: nodeId }
    });
    return response.data.results || response.data;
  }

  async getUsecaseCounts(nodeIds: number[]): Promise<Record<number, number>> {
    const counts: Record<number, number> = {};
    
    if (nodeIds.length === 0) {
      return counts;
    }

    console.log(`Getting usecase counts for ${nodeIds.length} nodes...`);
    
    // Batch requests in smaller chunks to avoid overwhelming the server
    const BATCH_SIZE = 5; // Process 5 nodes at a time
    const batches: number[][] = [];
    
    for (let i = 0; i < nodeIds.length; i += BATCH_SIZE) {
      batches.push(nodeIds.slice(i, i + BATCH_SIZE));
    }

    // Process batches sequentially to avoid rate limiting
    for (const batch of batches) {
      const batchPromises = batch.map(async (nodeId) => {
        try {
          const usecases = await this.getUsecasesByNode(nodeId);
          return { nodeId, count: usecases.length };
        } catch (error: any) {
          // Log but don't fail the entire operation
          console.warn(`Failed to get usecase count for node ${nodeId}:`, error.response?.status || error.message);
          return { nodeId, count: 0 };
        }
      });

      try {
        const batchResults = await Promise.all(batchPromises);
        batchResults.forEach(({ nodeId, count }) => {
          counts[nodeId] = count;
        });
        
        // Small delay between batches to be nice to the server
        if (batches.indexOf(batch) < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 100));
        }
      } catch (error) {
        console.error('Batch failed:', error);
        // Continue with next batch even if this one fails
      }
    }

    console.log(`Successfully loaded usecase counts for ${Object.keys(counts).length} nodes:`, counts);
    return counts;
  }

  async saveUsecase(usecase: Partial<NodeUsecaseCandidate>): Promise<NodeUsecaseCandidate> {
    const response: AxiosResponse<NodeUsecaseCandidate> = await this.apiClient.post('/usecases/', usecase);
    return response.data;
  }

  // Bookmarks
  async toggleBookmark(nodeId: number): Promise<{ bookmarked: boolean }> {
    const response = await this.apiClient.post('/bookmarks/toggle/', { node_id: nodeId });
    return response.data;
  }

  async getBookmarkCounts(modelKey: string): Promise<Record<string, number>> {
    const response = await this.apiClient.get('/bookmarks/counts/', {
      params: { model_key: modelKey }
    });
    return response.data;
  }

  async getBookmarks(modelKey?: string): Promise<{ 
    id: number; 
    node: number; 
    node_code: string; 
    node_name: string; 
    created_at: string;
  }[]> {
    const response = await this.apiClient.get('/bookmarks/');
    return response.data.results || response.data;
  }

  // Portfolios
  async getPortfolios(): Promise<Portfolio[]> {
    const response = await this.apiClient.get('/portfolios/');
    return response.data.results || response.data;
  }

  async createPortfolio(name: string, description?: string): Promise<Portfolio> {
    const response: AxiosResponse<Portfolio> = await this.apiClient.post('/portfolios/', { name, description });
    return response.data;
  }

  // Dashboard
  async getDashboardSpecs(modelKey: string): Promise<NodeDocument[]> {
    const response = await this.apiClient.get('/dashboard/specs/', {
      params: { model_key: modelKey }
    });
    return response.data.results || response.data;
  }

  async getDashboardStats(modelKey: string): Promise<{
    totalUsecaseCandidates: number;
    totalUsecaseSpecs: number;
    totalDetailedProcesses: number;
  }> {
    try {
      console.log(`Getting dashboard stats for model: ${modelKey}`);

      // Use direct API approach since node-based counting has issues
      console.log('Using direct document API calls for reliable counts...');
      
      const [directSpecs, directProcessDetails, usecasesResponse] = await Promise.all([
        this.apiClient.get('/documents/', { params: { model_key: modelKey, document_type: 'usecase_spec' } }),
        this.apiClient.get('/documents/', { params: { model_key: modelKey, document_type: 'process_details' } }),
        this.apiClient.get('/usecases/') // Get all usecases to filter by model metadata
      ]);
      
      const totalUsecaseSpecs = directSpecs.data.count || (Array.isArray(directSpecs.data.results) ? directSpecs.data.results.length : directSpecs.data.length);
      const totalDetailedProcesses = directProcessDetails.data.count || (Array.isArray(directProcessDetails.data.results) ? directProcessDetails.data.results.length : directProcessDetails.data.length);
      
      // Filter usecases by model metadata
      const allUsecases = usecasesResponse.data.results || usecasesResponse.data;
      let totalUsecaseCandidates = 0;
      
      if (Array.isArray(allUsecases)) {
        console.log(`Filtering ${allUsecases.length} usecases by model metadata for ${modelKey}`);
        console.log('Sample usecase structure:', allUsecases[0]);
        
        const filteredUsecases = allUsecases.filter(usecase => {
          // Try both meta_json.metadata.model_key and direct metadata.model_key
          const modelKeyFromMeta = usecase.meta_json?.metadata?.model_key;
          const modelKeyFromMetadata = usecase.metadata?.model_key;
          
          return modelKeyFromMeta === modelKey || modelKeyFromMetadata === modelKey;
        });
        
        totalUsecaseCandidates = filteredUsecases.length;
        console.log(`Model filtering result: ${totalUsecaseCandidates} usecases for model ${modelKey}`);
        
        if (filteredUsecases.length > 0) {
          console.log('Sample filtered usecase:', filteredUsecases[0]);
        }
      } else {
        console.warn('Usecases response is not an array:', allUsecases);
        totalUsecaseCandidates = usecasesResponse.data.count || 0;
      }

      console.log(`Direct API results for model ${modelKey}:`, {
        totalUsecaseCandidates,
        totalUsecaseSpecs,
        totalDetailedProcesses
      });
      
      console.log('Raw API responses breakdown:');
      console.log('- Specs response:', {
        count: directSpecs.data.count,
        resultsLength: directSpecs.data.results?.length,
        fullResponse: directSpecs.data
      });
      console.log('- Process details response:', {
        count: directProcessDetails.data.count,
        resultsLength: directProcessDetails.data.results?.length,
        fullResponse: directProcessDetails.data
      });
      console.log('- Usecases response:', {
        count: usecasesResponse.data.count,
        resultsLength: usecasesResponse.data.results?.length,
        fullResponse: usecasesResponse.data
      });


      return {
        totalUsecaseCandidates,
        totalUsecaseSpecs,
        totalDetailedProcesses
      };
    } catch (error) {
      console.error('Failed to load dashboard stats:', error);
      return {
        totalUsecaseCandidates: 0,
        totalUsecaseSpecs: 0,
        totalDetailedProcesses: 0
      };
    }
  }
  
  // Expose axios instance for direct API calls
  get api() {
    return this.apiClient;
  }
}

export const apiService = new ApiService();