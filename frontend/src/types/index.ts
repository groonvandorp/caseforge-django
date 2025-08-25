// API Types
export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
}

export interface ProcessModel {
  id: number;
  model_key: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface ProcessModelVersion {
  id: number;
  model: number;
  model_name: string;
  version_label: string;
  external_reference?: string;
  notes?: string;
  effective_date?: string;
  is_current: boolean;
  created_at: string;
}

export interface ProcessNode {
  id: number;
  model_version: number;
  parent?: number;
  code: string;
  name: string;
  description?: string;
  level: number;
  display_order?: number;
  materialized_path?: string;
  is_leaf: boolean;
  children_count: number;
  children?: ProcessNode[];
}

export interface NodeDocument {
  id: number;
  node: number;
  node_code: string;
  node_name: string;
  document_type: 'process_details' | 'usecase_spec' | 'research_summary';
  title?: string;
  content: string;
  meta_json?: any;
  created_at: string;
  updated_at: string;
}

export interface NodeUsecaseCandidate {
  id: number;
  node: number;
  node_code: string;
  node_name: string;
  candidate_uid: string;
  title: string;
  description: string;
  impact_assessment?: string;
  complexity_score?: number;
  meta_json?: any;
  created_at: string;
}

export interface Portfolio {
  id: number;
  name: string;
  description?: string;
  items_count: number;
  created_at: string;
}

// Auth Types
export interface LoginCredentials {
  email?: string;
  username?: string;
  password: string;
}

export interface SignupData {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// UI Types
export interface TreeViewNode {
  id: string;
  label: string;
  children?: TreeViewNode[];
  isLeaf?: boolean;
  nodeData?: ProcessNode;
}