#!/usr/bin/env python
"""
Test script to generate embeddings for a small number of ProcessNodes.
Use this to verify the setup before running the full generation.
"""

import os
import sys
import django
import asyncio
import json
from datetime import datetime

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


async def test_embedding_generation(limit=5):
    """Test embedding generation with a small number of nodes."""
    
    logger.info(f"Testing embedding generation with {limit} nodes...")
    
    # Get API key
    api_key = AdminSettings.get_setting('openai_api_key') or os.getenv('OPENAI_API_KEY')
    if not api_key:
        logger.error("OpenAI API key not found!")
        return False
    
    logger.info("✓ OpenAI API key found")
    
    # Initialize client
    client = AsyncOpenAI(api_key=api_key)
    model = "text-embedding-3-small"
    
    # Get sample nodes
    sample_nodes = ProcessNode.objects.filter(embedding__isnull=True)[:limit]
    
    if not sample_nodes:
        logger.info("No nodes without embeddings found. Trying with any nodes...")
        sample_nodes = ProcessNode.objects.all()[:limit]
    
    logger.info(f"Selected {len(sample_nodes)} nodes for testing:")
    for node in sample_nodes:
        logger.info(f"  - {node.code}: {node.name}")
    
    # Generate embeddings
    success_count = 0
    for node in sample_nodes:
        try:
            # Prepare text
            text = f"{node.name}. {node.description or ''} Code: {node.code}"
            logger.info(f"\nProcessing: {node.code}")
            logger.info(f"Text (first 100 chars): {text[:100]}...")
            
            # Generate embedding
            response = await client.embeddings.create(
                model=model,
                input=text
            )
            
            embedding = response.data[0].embedding
            logger.info(f"✓ Generated embedding with {len(embedding)} dimensions")
            
            # Save to database
            NodeEmbedding.objects.update_or_create(
                node=node,
                defaults={
                    'embedding_vector': embedding,
                    'embedding_model': model
                }
            )
            logger.info(f"✓ Saved to database")
            success_count += 1
            
        except Exception as e:
            logger.error(f"✗ Failed for {node.code}: {e}")
    
    # Summary
    logger.info(f"\n=== Test Results ===")
    logger.info(f"Successfully processed: {success_count}/{len(sample_nodes)} nodes")
    
    # Verify in database
    total_embeddings = NodeEmbedding.objects.count()
    logger.info(f"Total embeddings in database: {total_embeddings}")
    
    # Check a sample embedding
    if success_count > 0:
        sample = NodeEmbedding.objects.first()
        logger.info(f"Sample embedding dimensions: {len(sample.embedding_vector)}")
        logger.info(f"Sample embedding model: {sample.embedding_model}")
        logger.info(f"First 5 values: {sample.embedding_vector[:5]}")
    
    return success_count > 0


async def main():
    """Run the test."""
    success = await test_embedding_generation(limit=5)
    if success:
        logger.info("\n✓ Test successful! You can now run generate_embeddings.py for all nodes.")
    else:
        logger.error("\n✗ Test failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())