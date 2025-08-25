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

  async getChildren(nodeId: number): Promise<ProcessNode[]> {
    const response = await this.apiClient.get(`/nodes/${nodeId}/children/`);
    return response.data.results || response.data;
  }

  async getNodeByCode(code: string, modelKey: string): Promise<ProcessNode> {
    const response: AxiosResponse<ProcessNode> = await this.apiClient.get(`/nodes/by-code/${code}/`, {
      params: { model_key: modelKey }
    });
    return response.data;
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

  // Use Case Candidates
  async getUsecasesByNode(nodeId: number): Promise<NodeUsecaseCandidate[]> {
    const response = await this.apiClient.get('/usecases/by_node/', {
      params: { node_id: nodeId }
    });
    return response.data.results || response.data;
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
  
  // Expose axios instance for direct API calls
  get api() {
    return this.apiClient;
  }
}

export const apiService = new ApiService();