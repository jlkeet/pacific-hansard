#!/usr/bin/env python3
"""
Generate embeddings for existing documents in Solr and update them with vectors.
"""

import sys
import json
import logging
from pathlib import Path
import pysolr
import numpy as np

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from rag.embedding_service import get_embedding_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def generate_and_update_embeddings():
    """Generate embeddings for all documents in Solr and update them."""
    
    # Initialize services
    logger.info("Initializing services...")
    embedding_service = get_embedding_service()
    solr = pysolr.Solr('http://localhost:8983/solr/hansard_core')
    
    try:
        # Get all documents from Solr
        logger.info("Fetching all documents from Solr...")
        results = solr.search('*:*', rows=1000, fl='id,content,title')
        total_docs = len(results)
        
        if total_docs == 0:
            logger.warning("No documents found in Solr!")
            return
        
        logger.info(f"Found {total_docs} documents to process")
        
        # Process documents in batches
        batch_size = 10
        updated_count = 0
        
        for i in range(0, total_docs, batch_size):
            batch = list(results)[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs-1)//batch_size + 1} ({len(batch)} docs)")
            
            # Prepare batch data
            batch_texts = []
            batch_docs = []
            
            for doc in batch:
                content = doc.get('content', [''])[0] if isinstance(doc.get('content'), list) else doc.get('content', '')
                title = doc.get('title', [''])[0] if isinstance(doc.get('title'), list) else doc.get('title', '')
                
                # Combine title and content for embedding
                combined_text = f"{title}. {content}".strip()
                
                batch_texts.append(combined_text)
                batch_docs.append(doc)
            
            try:
                # Generate embeddings for batch
                logger.info(f"Generating embeddings for batch of {len(batch_texts)} documents...")
                embeddings = embedding_service.encode_documents(batch_texts)
                
                # Update each document with its embedding
                solr_updates = []
                
                for j, (doc, embedding) in enumerate(zip(batch_docs, embeddings)):
                    doc_id = doc['id']
                    
                    # Convert numpy array to list for Solr
                    embedding_list = embedding.tolist()
                    
                    # Prepare update document
                    update_doc = {
                        'id': doc_id,
                        'content_vector': {'set': embedding_list}
                    }
                    
                    solr_updates.append(update_doc)
                
                # Batch update Solr
                if solr_updates:
                    logger.info(f"Updating {len(solr_updates)} documents in Solr...")
                    solr.add(solr_updates)
                    updated_count += len(solr_updates)
                    
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                continue
        
        # Commit all changes
        logger.info("Committing changes to Solr...")
        solr.commit()
        
        logger.info(f"[SUCCESS] Updated {updated_count}/{total_docs} documents with embeddings")
        
        # Verify updates
        verification_result = solr.search('content_vector:[* TO *]', rows=0)
        docs_with_vectors = verification_result.hits
        logger.info(f"[VERIFY] {docs_with_vectors} documents now have vector embeddings")
        
    except Exception as e:
        logger.error(f"Error in embedding generation process: {e}")
        raise

def main():
    """Main entry point."""
    print("Generating embeddings for existing documents...")
    generate_and_update_embeddings()
    print("Done!")

if __name__ == "__main__":
    main()