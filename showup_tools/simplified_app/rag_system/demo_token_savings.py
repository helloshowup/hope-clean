#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Demonstration of token savings with the RAG system.

This script shows how much the RAG system reduces token usage
without making actual API calls to Claude.
"""

import os
import asyncio
import hashlib
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import our RAG components (with relative imports for standalone script)
from showup_tools.simplified_app.rag_system.token_counter import count_tokens
from showup_tools.simplified_app.rag_system.textbook_vector_db import vector_db


async def analyze_token_savings(handbook_path, query):
    """Analyze token savings without making API calls
    
    Args:
        handbook_path: Path to the handbook file
        query: Query to find relevant content
        
    Returns:
        Dictionary with token stats
    """
    if not os.path.exists(handbook_path):
        logger.error(f"Handbook not found: {handbook_path}")
        return None
    
    # Read the full handbook content
    with open(handbook_path, 'r', encoding='utf-8') as f:
        handbook_content = f.read()
    
    # Count tokens in the full handbook
    full_token_count = count_tokens(handbook_content)
    logger.info(f"Full handbook: {len(handbook_content):,} chars, {full_token_count:,} tokens")
    
    # Create a textbook ID based on the path
    textbook_id = hashlib.md5(handbook_path.encode()).hexdigest()
    
    # Index the textbook (will use cached index if unchanged)
    await vector_db.index_textbook_async(handbook_content, textbook_id)
    
    # Get relevant chunks
    results = await vector_db.query_textbook_async(textbook_id, query, top_k=3)
    
    # Extract the content from results
    relevant_chunks = [r['content'] for r in results]
    relevant_content = "\n\n".join(relevant_chunks)
    
    # Count tokens in retrieved content
    retrieved_token_count = count_tokens(relevant_content)
    logger.info(f"Retrieved chunks: {len(relevant_content):,} chars, {retrieved_token_count:,} tokens")
    
    # Calculate token reduction
    token_reduction = full_token_count - retrieved_token_count
    reduction_percent = (token_reduction / full_token_count) * 100
    
    # Create a sample prompt
    prompt = f"""Based on the provided handbook, explain the academic integrity policy. 
    
    {relevant_content}
    """
    
    # Count tokens in full prompt
    prompt_token_count = count_tokens(prompt)
    
    # Prepare statistics
    stats = {
        "full_handbook_chars": len(handbook_content),
        "full_handbook_tokens": full_token_count,
        "retrieved_chunks_chars": len(relevant_content),
        "retrieved_chunks_tokens": retrieved_token_count,
        "token_reduction": token_reduction,
        "reduction_percent": reduction_percent,
        "chunks_retrieved": len(relevant_chunks),
        "final_prompt_tokens": prompt_token_count
    }
    
    return stats


async def demo_specific_queries(handbook_path):
    """Demonstrate token savings for specific handbook queries
    
    Args:
        handbook_path: Path to the handbook file
    """
    print("\n===== DEMONSTRATING TOKEN SAVINGS WITH RAG =====\n")
    
    # Test different queries
    queries = [
        "What is the academic integrity policy?",
        "Explain the grading system and GPA calculation",
        "What are the graduation requirements?",
        "How does the school handle accommodations for students with disabilities?"
    ]
    
    for query in queries:
        print(f"\nQUERY: {query}")
        print("-" * 50)
        
        # Get stats
        stats = await analyze_token_savings(handbook_path, query)
        
        if stats:
            # Print the results
            print(f"FULL HANDBOOK:   {stats['full_handbook_tokens']:,} tokens")
            print(f"RETRIEVED CHUNKS: {stats['retrieved_chunks_tokens']:,} tokens")
            print(f"TOKEN REDUCTION: {stats['token_reduction']:,} tokens ({stats['reduction_percent']:.1f}%)")
            print(f"FINAL PROMPT:    {stats['final_prompt_tokens']:,} tokens")
            
            # Print sample chunks
            print("\nSAMPLE OF RETRIEVED CONTENT:")
            with open(handbook_path, 'r', encoding='utf-8') as f:
                handbook_content = f.read()
            
            textbook_id = hashlib.md5(handbook_path.encode()).hexdigest()
            results = await vector_db.query_textbook_async(textbook_id, query, top_k=1)
            if results:
                print("\n" + results[0]["content"][:200] + "...")
    
    print("\n===== DEMONSTRATION COMPLETE =====\n")


async def main():
    """Main demo function"""
    handbook_path = "C:\\Users\\User\\Desktop\\ShowupSquaredV4 (2)\\ShowupSquaredV4\\ShowupSquaredV4\\showup-tools\\simplified_app\\EHS Student Catalog_Handbook from Canva.md"
    
    if not os.path.exists(handbook_path):
        logger.error(f"Handbook not found: {handbook_path}")
        return
    
    await demo_specific_queries(handbook_path)


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())
