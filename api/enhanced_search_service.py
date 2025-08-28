"""
Enhanced search service with scope filtering for processes, use cases, or both.
Supports both semantic (embedding-based) and text search.
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional, Literal
from django.db import connection
from django.db.models import Q
from openai import OpenAI

from core.models import (
    ProcessNode, NodeUsecaseCandidate, NodeEmbedding,
    ProcessModelVersion, AdminSettings
)

SearchScope = Literal["processes", "usecases", "all"]

class EnhancedSearchService:
    """Enhanced search service with scope filtering."""
    
    def __init__(self):
        self.client = None
        self.embedding_model = "text-embedding-3-small"
        self._setup_openai()
    
    def _setup_openai(self):
        """Initialize OpenAI client."""
        api_key = AdminSettings.get_setting('openai_api_key')
        if api_key:
            self.client = OpenAI(api_key=api_key)
    
    def search(
        self,
        query: str,
        model_version_id: int,
        scope: SearchScope = "all",
        search_type: str = "hybrid",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Perform search with scope filtering.
        
        Args:
            query: Search query string
            model_version_id: Process model version to search within
            scope: Search scope - "processes", "usecases", or "all"
            search_type: Type of search - "semantic", "text", or "hybrid"
            limit: Maximum number of results
            
        Returns:
            Dictionary with search results organized by type
        """
        results = {
            "query": query,
            "scope": scope,
            "search_type": search_type,
            "processes": [],
            "usecases": [],
            "total_count": 0
        }
        
        # Perform search based on type
        if search_type == "semantic" and self.client:
            semantic_results = self._semantic_search(query, model_version_id, scope, limit)
            results.update(semantic_results)
        elif search_type == "text":
            text_results = self._text_search(query, model_version_id, scope, limit)
            results.update(text_results)
        else:  # hybrid
            # Combine semantic and text search
            if self.client:
                semantic_results = self._semantic_search(query, model_version_id, scope, limit)
                text_results = self._text_search(query, model_version_id, scope, limit)
                results = self._merge_results(semantic_results, text_results)
                results["scope"] = scope
                results["search_type"] = search_type
            else:
                # Fallback to text search if OpenAI not available
                text_results = self._text_search(query, model_version_id, scope, limit)
                results.update(text_results)
        
        results["total_count"] = len(results["processes"]) + len(results["usecases"])
        return results
    
    def _semantic_search(
        self,
        query: str,
        model_version_id: int,
        scope: SearchScope,
        limit: int
    ) -> Dict[str, Any]:
        """Perform semantic search using embeddings."""
        # Generate query embedding
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=query
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            return {"processes": [], "usecases": []}
        
        results = {"processes": [], "usecases": []}
        
        # Search processes if scope includes them
        if scope in ["processes", "all"]:
            process_results = self._search_process_embeddings(
                query_embedding, model_version_id, limit
            )
            results["processes"] = process_results
        
        # Search use cases if scope includes them
        if scope in ["usecases", "all"]:
            usecase_results = self._search_usecase_embeddings(
                query_embedding, model_version_id, limit
            )
            results["usecases"] = usecase_results
        
        return results
    
    def _search_process_embeddings(
        self,
        query_embedding: List[float],
        model_version_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search process node embeddings."""
        # Get all node embeddings for this model version
        embeddings = NodeEmbedding.objects.filter(
            node__model_version_id=model_version_id
        ).select_related('node')
        
        # Calculate similarities
        similarities = []
        for embedding in embeddings:
            similarity = self._cosine_similarity(
                query_embedding,
                embedding.embedding_vector
            )
            similarities.append((embedding.node, similarity))
        
        # Sort by similarity and take top results
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_results = similarities[:limit]
        
        # Format results
        results = []
        for node, similarity in top_results:
            if similarity > 0.7:  # Threshold for relevance
                results.append({
                    "id": node.id,
                    "code": node.code,
                    "name": node.name,
                    "description": node.description,
                    "level": node.level,
                    "similarity": round(similarity, 3),
                    "type": "process",
                    "parent_name": node.parent.name if node.parent else None,
                    "is_leaf": node.is_leaf
                })
        
        return results
    
    def _search_usecase_embeddings(
        self,
        query_embedding: List[float],
        model_version_id: int,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Search use case embeddings."""
        try:
            # Check if usecase_embedding table exists
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='usecase_embedding'")
                table_exists = cursor.fetchone()[0] > 0
                
                if not table_exists:
                    print("usecase_embedding table doesn't exist yet - embeddings not ready")
                    return []
                
                # Query use case embeddings directly from database
                cursor.execute("""
                    SELECT 
                        uc.id,
                        uc.candidate_uid,
                        uc.title,
                        uc.description,
                        uc.impact_assessment,
                        uc.complexity_score,
                        uc.meta_json,
                        ue.embedding_vector,
                        pn.code as node_code,
                        pn.name as node_name,
                        pn.id as node_id
                    FROM node_usecase_candidate uc
                    JOIN usecase_embedding ue ON uc.id = ue.usecase_id
                    JOIN process_node pn ON uc.node_id = pn.id
                    WHERE pn.model_version_id = ?
                    AND uc.meta_json LIKE '%"generated_by":"batch_api"%'
                """, [model_version_id])
                
                rows = cursor.fetchall()
            
            # Calculate similarities
            similarities = []
            for row in rows:
                embedding_vector = json.loads(row[7])  # embedding_vector
                similarity = self._cosine_similarity(query_embedding, embedding_vector)
                
                if similarity > 0.7:  # Threshold for relevance
                    meta_json = json.loads(row[6]) if row[6] else {}
                    similarities.append({
                        "id": row[0],
                        "candidate_uid": row[1],
                        "title": row[2],
                        "description": row[3][:200] + "..." if len(row[3]) > 200 else row[3],
                        "impact_assessment": row[4][:200] + "..." if row[4] and len(row[4]) > 200 else row[4],
                        "complexity_score": row[5],
                        "category": meta_json.get('category', 'unknown'),
                        "estimated_roi": meta_json.get('estimated_roi', 'unknown'),
                        "risk_level": meta_json.get('risk_level', 'unknown'),
                        "node_code": row[8],
                        "node_name": row[9],
                        "node_id": row[10],
                        "similarity": round(similarity, 3),
                        "type": "usecase"
                    })
            
            # Sort by similarity and return top results
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities[:limit]
            
        except Exception as e:
            print(f"Error in usecase embeddings search: {str(e)}")
            return []
    
    def _text_search(
        self,
        query: str,
        model_version_id: int,
        scope: SearchScope,
        limit: int
    ) -> Dict[str, Any]:
        """Perform text-based search."""
        results = {"processes": [], "usecases": []}
        
        # Search processes if scope includes them
        if scope in ["processes", "all"]:
            process_queryset = ProcessNode.objects.filter(
                model_version_id=model_version_id
            ).filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(code__icontains=query)
            )[:limit]
            
            results["processes"] = [
                {
                    "id": node.id,
                    "code": node.code,
                    "name": node.name,
                    "description": node.description,
                    "level": node.level,
                    "type": "process",
                    "parent_name": node.parent.name if node.parent else None,
                    "is_leaf": node.is_leaf,
                    "similarity": 0.8  # Fixed score for text matches
                }
                for node in process_queryset
            ]
        
        # Search use cases if scope includes them
        if scope in ["usecases", "all"]:
            usecase_queryset = NodeUsecaseCandidate.objects.filter(
                node__model_version_id=model_version_id,
                meta_json__generated_by='batch_api'
            ).filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(impact_assessment__icontains=query)
            ).select_related('node')[:limit]
            
            results["usecases"] = [
                {
                    "id": uc.id,
                    "candidate_uid": uc.candidate_uid,
                    "title": uc.title,
                    "description": uc.description[:200] + "..." if len(uc.description) > 200 else uc.description,
                    "impact_assessment": uc.impact_assessment[:200] + "..." if uc.impact_assessment and len(uc.impact_assessment) > 200 else uc.impact_assessment,
                    "complexity_score": uc.complexity_score,
                    "category": uc.meta_json.get('category', 'unknown') if uc.meta_json else 'unknown',
                    "estimated_roi": uc.meta_json.get('estimated_roi', 'unknown') if uc.meta_json else 'unknown',
                    "risk_level": uc.meta_json.get('risk_level', 'unknown') if uc.meta_json else 'unknown',
                    "node_code": uc.node.code,
                    "node_name": uc.node.name,
                    "node_id": uc.node.id,
                    "type": "usecase",
                    "similarity": 0.8  # Fixed score for text matches
                }
                for uc in usecase_queryset
            ]
        
        return results
    
    def _merge_results(
        self,
        semantic_results: Dict[str, Any],
        text_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge semantic and text search results, removing duplicates."""
        merged = {
            "query": semantic_results.get("query", ""),
            "processes": [],
            "usecases": []
        }
        
        # Merge processes (semantic results first, higher weight)
        process_ids = set()
        for process in semantic_results.get("processes", []):
            process_ids.add(process["id"])
            merged["processes"].append(process)
        
        for process in text_results.get("processes", []):
            if process["id"] not in process_ids:
                process["similarity"] *= 0.9  # Slightly lower weight for text-only matches
                merged["processes"].append(process)
        
        # Merge use cases
        usecase_ids = set()
        for usecase in semantic_results.get("usecases", []):
            usecase_ids.add(usecase["id"])
            merged["usecases"].append(usecase)
        
        for usecase in text_results.get("usecases", []):
            if usecase["id"] not in usecase_ids:
                usecase["similarity"] *= 0.9  # Slightly lower weight for text-only matches
                merged["usecases"].append(usecase)
        
        # Sort by similarity
        merged["processes"].sort(key=lambda x: x.get("similarity", 0), reverse=True)
        merged["usecases"].sort(key=lambda x: x.get("similarity", 0), reverse=True)
        
        return merged
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float]
    ) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)