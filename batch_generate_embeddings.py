#!/usr/bin/env python
"""
Generate embeddings using OpenAI's Batch API (50% cheaper than real-time API).
This script:
1. Exports ProcessNodes data to JSONL format
2. Creates a batch job with OpenAI
3. Monitors the batch job
4. Imports the embeddings back to the database
"""

import os
import json
import time
import sqlite3
from datetime import datetime
from pathlib import Path
from openai import OpenAI
import argparse

# Configuration
MODEL = "text-embedding-3-small"
DB_PATH = "db.sqlite3"
OUTPUT_DIR = Path("embeddings_batch")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_pcf_mapping():
    """Load PCF-ID mapping from the Excel source file."""
    excel_file = "/Users/oliver/Library/Mobile Documents/com~apple~CloudDocs/Projekte/2025 Onwell/development/backend/model_information/K014749_APQC Process Classification Framework (PCF) - Cross-Industry - Excel Version 7.4.xlsx"
    
    try:
        import pandas as pd
        print(f"Loading PCF-ID mapping from Excel file...")
        
        # Read the Combined sheet with proper headers
        df = pd.read_excel(excel_file, sheet_name='Combined', header=0)
        df.columns = ['PCF_ID', 'Hierarchy_ID', 'Name', 'Difference_Index', 'Change_Details', 'Metrics_Available', 'Element_Description']
        
        # Create mapping dictionary: code -> PCF_ID
        pcf_mapping = {}
        for _, row in df.iterrows():
            pcf_mapping[row['Hierarchy_ID']] = row['PCF_ID']
        
        print(f"Loaded {len(pcf_mapping)} PCF-ID mappings")
        return pcf_mapping
        
    except ImportError:
        print("Warning: pandas not available, PCF-IDs will be set to None")
        return {}
    except Exception as e:
        print(f"Warning: Could not load PCF mapping: {e}")
        return {}


def extract_nodes_from_db():
    """Extract ProcessNodes from Django SQLite database with PCF-ID mapping."""
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Query to get all process nodes with model information
    query = """
    SELECT 
        pn.id,
        pn.code,
        pn.name,
        pn.description,
        pn.level,
        parent.name as parent_name,
        pm.model_key as model_type
    FROM process_node pn
    LEFT JOIN process_node parent ON pn.parent_id = parent.id
    JOIN process_model_version pmv ON pn.model_version_id = pmv.id
    JOIN process_model pm ON pmv.model_id = pm.id
    ORDER BY pn.id
    """
    
    cursor.execute(query)
    nodes = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(nodes)} nodes")
    
    # Load PCF-ID mapping
    pcf_mapping = load_pcf_mapping()
    
    # Enhance nodes with PCF-ID
    enhanced_nodes = []
    for node in nodes:
        node_id, code, name, description, level, parent_name, model_type = node
        pcf_id = pcf_mapping.get(code, None)
        enhanced_nodes.append((node_id, code, name, description, level, parent_name, model_type, pcf_id))
    
    return enhanced_nodes


def prepare_batch_input(nodes, output_file="batch_input_v2.jsonl"):
    """
    Prepare JSONL file for OpenAI Batch API with complete PCF data.
    Each line is a request to generate embeddings with all required fields.
    """
    output_path = OUTPUT_DIR / output_file
    
    missing_pcf_count = 0
    with open(output_path, 'w') as f:
        for node in nodes:
            node_id, code, name, description, level, parent_name, model_type, pcf_id = node
            
            # Count missing PCF IDs
            if pcf_id is None:
                missing_pcf_count += 1
            
            # Prepare comprehensive text for embedding including all required fields
            text_parts = []
            
            # Process name
            text_parts.append(f"Process: {name}")
            
            # PCF-ID (5-digit unique identifier)
            if pcf_id:
                text_parts.append(f"PCF-ID: {pcf_id}")
            
            # Node number (hierarchy ID)
            text_parts.append(f"Node: {code}")
            
            # Level
            text_parts.append(f"Level: {level}")
            
            # Model type
            text_parts.append(f"Model: {model_type}")
            
            # Parent context
            if parent_name:
                text_parts.append(f"Parent: {parent_name}")
            
            # Full description (most important for semantic search)
            if description and description.strip():
                text_parts.append(f"Description: {description.strip()}")
            
            # Join all parts with separators
            text = ". ".join(text_parts)
            
            # Create batch request format
            request = {
                "custom_id": f"node-{node_id}",
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": MODEL,
                    "input": text
                }
            }
            
            f.write(json.dumps(request) + '\n')
    
    print(f"Created enhanced batch input file: {output_path}")
    print(f"Total requests: {len(nodes)}")
    if missing_pcf_count > 0:
        print(f"Warning: {missing_pcf_count} nodes missing PCF-ID")
    return output_path


def upload_batch_file(client, file_path):
    """Upload the batch file to OpenAI."""
    print(f"Uploading file: {file_path}")
    
    with open(file_path, 'rb') as f:
        batch_file = client.files.create(
            file=f,
            purpose="batch"
        )
    
    print(f"File uploaded successfully. File ID: {batch_file.id}")
    return batch_file.id


def create_batch_job(client, file_id):
    """Create a batch processing job."""
    print(f"Creating batch job with file: {file_id}")
    
    batch = client.batches.create(
        input_file_id=file_id,
        endpoint="/v1/embeddings",
        completion_window="24h"
    )
    
    print(f"Batch job created. Batch ID: {batch.id}")
    print(f"Status: {batch.status}")
    return batch.id


def monitor_batch_job(client, batch_id):
    """Monitor the batch job until completion."""
    print(f"\nMonitoring batch job: {batch_id}")
    print("This may take several minutes to hours depending on the queue...")
    
    while True:
        batch = client.batches.retrieve(batch_id)
        
        print(f"\r[{datetime.now().strftime('%H:%M:%S')}] Status: {batch.status} | "
              f"Completed: {batch.request_counts.completed}/{batch.request_counts.total} | "
              f"Failed: {batch.request_counts.failed}", end='', flush=True)
        
        if batch.status == "completed":
            print("\n✓ Batch processing completed!")
            return batch.output_file_id
        elif batch.status == "failed":
            print(f"\n✗ Batch processing failed!")
            if batch.errors:
                print(f"Errors: {batch.errors}")
            return None
        elif batch.status == "cancelled":
            print("\n✗ Batch was cancelled")
            return None
        
        time.sleep(30)  # Check every 30 seconds


def download_results(client, output_file_id):
    """Download the results from OpenAI."""
    if not output_file_id:
        print("No output file to download")
        return None
    
    print(f"Downloading results file: {output_file_id}")
    
    content = client.files.content(output_file_id)
    output_path = OUTPUT_DIR / f"batch_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
    
    with open(output_path, 'wb') as f:
        f.write(content.content)
    
    print(f"Results saved to: {output_path}")
    return output_path


def parse_results(results_file):
    """Parse the results file and extract embeddings."""
    print(f"Parsing results from: {results_file}")
    
    embeddings = {}
    errors = []
    
    with open(results_file, 'r') as f:
        for line in f:
            result = json.loads(line)
            custom_id = result['custom_id']
            
            # Check if response was successful
            if 'response' in result and result['response'].get('status_code') == 200:
                try:
                    node_id = int(custom_id.replace('node-', ''))
                    embedding = result['response']['body']['data'][0]['embedding']
                    embeddings[node_id] = embedding
                except (KeyError, ValueError, IndexError) as e:
                    errors.append((custom_id, f"Parse error: {str(e)}"))
            elif result.get('error'):
                # Only count as error if error field is not None/empty
                errors.append((custom_id, result['error']))
            else:
                # Handle unexpected response format
                status = result.get('response', {}).get('status_code', 'Unknown')
                if status != 200:
                    errors.append((custom_id, f"Status code: {status}"))
    
    print(f"Successfully parsed {len(embeddings)} embeddings")
    if errors:
        print(f"Errors found: {len(errors)}")
        for custom_id, error in errors[:5]:  # Show first 5 errors
            print(f"  - {custom_id}: {error}")
    
    return embeddings


def save_embeddings_to_db(embeddings, clear_existing=False):
    """Save embeddings back to the Django database."""
    print(f"Saving {len(embeddings)} embeddings to database...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if node_embedding table exists and has data
    cursor.execute("SELECT COUNT(*) FROM node_embedding")
    existing_count = cursor.fetchone()[0]
    print(f"Existing embeddings in database: {existing_count}")
    
    # Clear existing embeddings if requested (for regeneration)
    if clear_existing and existing_count > 0:
        print("Clearing existing embeddings...")
        cursor.execute("DELETE FROM node_embedding")
        print(f"✓ Cleared {existing_count} existing embeddings")
    
    # Insert or update embeddings
    success_count = 0
    for node_id, embedding in embeddings.items():
        try:
            # Check if embedding already exists (if not cleared)
            if not clear_existing:
                cursor.execute("SELECT id FROM node_embedding WHERE node_id = ?", (node_id,))
                existing = cursor.fetchone()
            else:
                existing = None
            
            embedding_json = json.dumps(embedding)
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE node_embedding 
                    SET embedding_vector = ?, embedding_model = ?, created_at = ?
                    WHERE node_id = ?
                """, (embedding_json, MODEL, datetime.now().isoformat(), node_id))
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO node_embedding (node_id, embedding_vector, embedding_model, created_at)
                    VALUES (?, ?, ?, ?)
                """, (node_id, embedding_json, MODEL, datetime.now().isoformat()))
            
            success_count += 1
            
            if success_count % 100 == 0:
                conn.commit()
                print(f"  Saved {success_count}/{len(embeddings)} embeddings...")
                
        except Exception as e:
            print(f"Error saving embedding for node {node_id}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Successfully saved {success_count} embeddings to database")


def estimate_cost(num_nodes):
    """Estimate the cost for batch embedding generation."""
    # Rough estimate: ~500 tokens per node on average
    estimated_tokens = num_nodes * 500
    
    # Batch API pricing for text-embedding-3-small (50% discount)
    # Normal price: $0.020 per 1M tokens
    # Batch price: $0.010 per 1M tokens
    batch_cost = (estimated_tokens / 1_000_000) * 0.010
    normal_cost = (estimated_tokens / 1_000_000) * 0.020
    
    print(f"\n💰 Cost Estimate:")
    print(f"  Estimated tokens: {estimated_tokens:,}")
    print(f"  Batch API cost: ${batch_cost:.4f}")
    print(f"  Normal API cost: ${normal_cost:.4f}")
    print(f"  Savings: ${normal_cost - batch_cost:.4f} (50% discount)")
    
    return batch_cost


def main():
    parser = argparse.ArgumentParser(description='Generate embeddings using OpenAI Batch API')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    parser.add_argument('--estimate-only', action='store_true', help='Only show cost estimate')
    parser.add_argument('--monitor', help='Monitor existing batch job by ID')
    parser.add_argument('--parse', help='Parse existing results file')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key and not args.estimate_only:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY or use --api-key")
        return 1
    
    # Extract nodes
    print("=" * 60)
    print("OPENAI BATCH EMBEDDING GENERATION")
    print("=" * 60)
    
    nodes = extract_nodes_from_db()
    
    # Show cost estimate
    estimate_cost(len(nodes))
    
    if args.estimate_only:
        return 0
    
    client = OpenAI(api_key=api_key)
    
    # If monitoring existing job
    if args.monitor:
        output_file_id = monitor_batch_job(client, args.monitor)
        if output_file_id:
            results_file = download_results(client, output_file_id)
            embeddings = parse_results(results_file)
            save_embeddings_to_db(embeddings)
        return 0
    
    # If parsing existing results
    if args.parse:
        embeddings = parse_results(args.parse)
        save_embeddings_to_db(embeddings, clear_existing=True)  # Clear old embeddings when regenerating
        return 0
    
    # Full pipeline
    print("\n📝 Step 1: Prepare batch input")
    batch_input_file = prepare_batch_input(nodes)
    
    print("\n📤 Step 2: Upload to OpenAI")
    file_id = upload_batch_file(client, batch_input_file)
    
    print("\n🚀 Step 3: Create batch job")
    batch_id = create_batch_job(client, file_id)
    
    print("\n⏳ Step 4: Monitor batch job")
    print(f"Batch ID: {batch_id}")
    print("You can stop this script and resume monitoring later with:")
    print(f"  python batch_generate_embeddings.py --monitor {batch_id}")
    
    output_file_id = monitor_batch_job(client, batch_id)
    
    if output_file_id:
        print("\n📥 Step 5: Download results")
        results_file = download_results(client, output_file_id)
        
        print("\n🔍 Step 6: Parse results")
        embeddings = parse_results(results_file)
        
        print("\n💾 Step 7: Save to database")
        save_embeddings_to_db(embeddings, clear_existing=True)  # Clear old embeddings when regenerating
        
        print("\n✅ Batch embedding generation complete!")
    else:
        print("\n❌ Batch processing failed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())