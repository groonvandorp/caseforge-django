"""
Semantic search service for finding similar ProcessNodes using embeddings.
"""

import logging
import numpy as np
from typing import List, Dict, Tuple
from django.db.models import Q
from core.models import ProcessNode, NodeEmbedding
from .services import OpenAIService

logger = logging.getLogger(__name__)


class SemanticSearchService:
    """Service for semantic search using embeddings."""
    
    def __init__(self):
        self.openai_service = None
        
    def _get_openai_service(self):
        """Lazy initialization of OpenAI service."""
        if self.openai_service is None:
            try:
                self.openai_service = OpenAIService()
            except Exception as e:
                logger.warning(f"OpenAI service not available: {e}")
                self.openai_service = None
        return self.openai_service
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
    
    async def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query."""
        try:
            from .services import OpenAIService
            openai_service = OpenAIService()
            
            # Use the async method directly
            embeddings = await openai_service._async_generate_embeddings([query])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise ValueError(f"Failed to generate embedding: {e}")
    
    def generate_query_embedding_sync(self, query: str) -> List[float]:
        """Generate embedding for search query synchronously."""
        try:
            import asyncio
            from asgiref.sync import sync_to_async
            from .services import OpenAIService
            
            openai_service = OpenAIService()
            
            # Run async method in sync context
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            embeddings = loop.run_until_complete(openai_service._async_generate_embeddings([query]))
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise ValueError(f"Failed to generate embedding: {e}")
    
    def search_nodes(
        self,
        query_embedding: List[float],
        model_version_id: int = None,
        level_filter: List[int] = None,
        limit: int = 20,
        min_similarity: float = 0.1
    ) -> List[Dict]:
        """
        Search for similar nodes using cosine similarity.
        
        Args:
            query_embedding: The query vector
            model_version_id: Filter by model version
            level_filter: Filter by process levels (e.g., [1, 2])
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of search results with similarity scores
        """
        logger.info(f"Searching nodes with similarity threshold: {min_similarity}, limit: {limit}")
        
        # Build query for nodes with embeddings
        nodes_query = ProcessNode.objects.select_related(
            'parent', 'model_version__model'
        ).prefetch_related('embedding')
        
        # Apply filters
        if model_version_id:
            nodes_query = nodes_query.filter(model_version_id=model_version_id)
        
        if level_filter:
            nodes_query = nodes_query.filter(level__in=level_filter)
        
        # Only nodes with embeddings
        nodes_query = nodes_query.filter(embedding__isnull=False)
        
        results = []
        processed_count = 0
        
        for node in nodes_query:
            try:
                # Get the node's embedding
                node_embedding = node.embedding.embedding_vector
                
                # Calculate similarity
                similarity = self.cosine_similarity(query_embedding, node_embedding)
                
                if similarity >= min_similarity:
                    results.append({
                        'node_id': node.id,
                        'code': node.code,
                        'name': node.name,
                        'description': node.description,
                        'level': node.level,
                        'similarity_score': round(similarity, 4),
                        'model_key': node.model_version.model.model_key,
                        'parent_code': node.parent.code if node.parent else None,
                        'parent_name': node.parent.name if node.parent else None,
                    })
                
                processed_count += 1
                
                # Log progress for large searches
                if processed_count % 1000 == 0:
                    logger.info(f"Processed {processed_count} nodes, found {len(results)} matches")
                
            except Exception as e:
                logger.error(f"Error processing node {node.id}: {e}")
                continue
        
        # Sort by similarity score (highest first) and limit results
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        final_results = results[:limit]
        
        logger.info(f"Search complete: processed {processed_count} nodes, "
                   f"found {len(results)} matches, returning top {len(final_results)}")
        
        return final_results
    
    def text_search_fallback(
        self,
        query: str,
        model_version_id: int = None,
        level_filter: List[int] = None,
        limit: int = 20
    ) -> List[Dict]:
        """
        Fallback text-based search when embeddings are not available.
        
        Args:
            query: Search query text
            model_version_id: Filter by model version
            level_filter: Filter by process levels
            limit: Maximum number of results
            
        Returns:
            List of search results
        """
        logger.info(f"Performing text-based fallback search for: '{query}'")
        
        # Build query for text search
        nodes_query = ProcessNode.objects.select_related(
            'parent', 'model_version__model'
        )
        
        # Apply filters
        if model_version_id:
            nodes_query = nodes_query.filter(model_version_id=model_version_id)
        
        if level_filter:
            nodes_query = nodes_query.filter(level__in=level_filter)
        
        # Text search across name and description
        search_query = Q(name__icontains=query)
        if query:  # Also search in description
            search_query |= Q(description__icontains=query)
        
        nodes = nodes_query.filter(search_query)[:limit]
        
        results = []
        for node in nodes:
            results.append({
                'node_id': node.id,
                'code': node.code,
                'name': node.name,
                'description': node.description,
                'level': node.level,
                'similarity_score': None,  # No similarity score for text search
                'model_key': node.model_version.model.model_key,
                'parent_code': node.parent.code if node.parent else None,
                'parent_name': node.parent.name if node.parent else None,
                'search_type': 'text'
            })
        
        logger.info(f"Text search complete: found {len(results)} matches")
        return results


# Global service instance
search_service = SemanticSearchService()