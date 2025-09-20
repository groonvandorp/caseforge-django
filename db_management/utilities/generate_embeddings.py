#!/usr/bin/env python
"""
Standalone script to generate embeddings for all ProcessNodes.
This runs outside the main application for one-time bulk embedding generation.
"""

import os
import sys
import django
import asyncio
import json
from datetime import datetime
from typing import List, Dict
import time

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'caseforge.settings')
django.setup()

from django.db import transaction
from core.models import ProcessNode, NodeEmbedding, AdminSettings
from openai import AsyncOpenAI
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    def __init__(self):
        # Get OpenAI API key from AdminSettings or environment
        api_key = AdminSettings.get_setting('openai_api_key') or os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set it in AdminSettings or OPENAI_API_KEY environment variable.")
        
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = "text-embedding-3-small"
        self.batch_size = 100  # Process in batches to avoid rate limits
        self.delay_between_batches = 1  # Seconds between batches
        
        logger.info(f"Initialized with model: {self.model}")
        logger.info(f"Batch size: {self.batch_size}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts."""
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings batch: {e}")
            raise
    
    def prepare_node_text(self, node: ProcessNode) -> str:
        """Prepare text representation of a node for embedding."""
        # Combine node name and description for richer context
        text_parts = [node.name]
        
        if node.description:
            text_parts.append(node.description)
        
        # Add code for additional context
        text_parts.append(f"Code: {node.code}")
        
        # Add parent context if available
        if node.parent:
            text_parts.append(f"Parent: {node.parent.name}")
        
        return ". ".join(text_parts)
    
    async def process_all_nodes(self):
        """Process all nodes and generate embeddings."""
        # Get all nodes that don't have embeddings yet
        nodes_without_embeddings = ProcessNode.objects.filter(
            embedding__isnull=True
        ).select_related('parent')
        
        total_nodes = nodes_without_embeddings.count()
        
        if total_nodes == 0:
            logger.info("All nodes already have embeddings!")
            return
        
        logger.info(f"Found {total_nodes} nodes without embeddings")
        
        # Process in batches
        processed = 0
        failed = 0
        
        for i in range(0, total_nodes, self.batch_size):
            batch_nodes = list(nodes_without_embeddings[i:i + self.batch_size])
            batch_texts = [self.prepare_node_text(node) for node in batch_nodes]
            
            logger.info(f"Processing batch {i // self.batch_size + 1} ({i + 1}-{min(i + self.batch_size, total_nodes)} of {total_nodes})")
            
            try:
                # Generate embeddings for the batch
                embeddings = await self.generate_embeddings_batch(batch_texts)
                
                # Save embeddings to database
                with transaction.atomic():
                    for node, embedding in zip(batch_nodes, embeddings):
                        NodeEmbedding.objects.update_or_create(
                            node=node,
                            defaults={
                                'embedding_vector': embedding,
                                'embedding_model': self.model
                            }
                        )
                
                processed += len(batch_nodes)
                logger.info(f"Successfully processed {len(batch_nodes)} nodes in this batch")
                
            except Exception as e:
                failed += len(batch_nodes)
                logger.error(f"Failed to process batch: {e}")
                # Continue with next batch instead of stopping
                
            # Rate limiting delay between batches
            if i + self.batch_size < total_nodes:
                await asyncio.sleep(self.delay_between_batches)
        
        logger.info(f"Embedding generation complete!")
        logger.info(f"Successfully processed: {processed} nodes")
        logger.info(f"Failed: {failed} nodes")
        
        # Verify embeddings
        total_embeddings = NodeEmbedding.objects.count()
        logger.info(f"Total embeddings in database: {total_embeddings}")
    
    async def verify_embeddings(self):
        """Verify that embeddings were created correctly."""
        # Check total count
        total_nodes = ProcessNode.objects.count()
        total_embeddings = NodeEmbedding.objects.count()
        
        logger.info(f"\n=== Verification Results ===")
        logger.info(f"Total ProcessNodes: {total_nodes}")
        logger.info(f"Total Embeddings: {total_embeddings}")
        logger.info(f"Coverage: {(total_embeddings/total_nodes)*100:.2f}%")
        
        # Check embedding dimensions
        sample_embedding = NodeEmbedding.objects.first()
        if sample_embedding:
            embedding_dim = len(sample_embedding.embedding_vector)
            logger.info(f"Embedding dimensions: {embedding_dim}")
            logger.info(f"Embedding model: {sample_embedding.embedding_model}")
        
        # Find nodes without embeddings
        nodes_without_embeddings = ProcessNode.objects.filter(embedding__isnull=True).count()
        if nodes_without_embeddings > 0:
            logger.warning(f"Nodes still without embeddings: {nodes_without_embeddings}")
            sample_missing = ProcessNode.objects.filter(embedding__isnull=True)[:5]
            for node in sample_missing:
                logger.warning(f"  - {node.code}: {node.name}")


async def main():
    """Main function to run the embedding generation."""
    logger.info("Starting embedding generation process...")
    start_time = time.time()
    
    try:
        generator = EmbeddingGenerator()
        
        # Generate embeddings
        await generator.process_all_nodes()
        
        # Verify results
        await generator.verify_embeddings()
        
        elapsed_time = time.time() - start_time
        logger.info(f"\nTotal time: {elapsed_time:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())