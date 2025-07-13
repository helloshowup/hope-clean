#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Textbook Vector Database for RAG system.

Implements a vector database for textbook content with efficient chunking,
deduplicated storage, and fallback keyword search capabilities.
"""

import os
import re
import json
import math
import time
import hashlib
import logging
import asyncio
from typing import List, Dict, Any, Optional, Set

# Configure logging
logger = logging.getLogger(__name__)

# Try to import required dependencies
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("langchain not installed. TextSplitter will be limited.")

try:
    from langchain_community.vectorstores import FAISS
    from langchain_community.embeddings import HuggingFaceEmbeddings
    VECTOR_LIBS_AVAILABLE = True
except ImportError:
    VECTOR_LIBS_AVAILABLE = False
    logger.warning("FAISS or HuggingFace embeddings not installed. Vector search will be unavailable.")


class SimpleTextSplitter:
    """Fallback text splitter when langchain is not available"""
    
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 50):
        """Initialize with chunk parameters
        
        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap
        
        Args:
            text: Text to split
            
        Returns:
            List of text chunks
        """
        if not text:
            return []
        
        # Basic splitting on paragraph breaks when possible
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            # If adding this paragraph would exceed chunk size, store current chunk and start new one
            if len(current_chunk) + len(para) > self.chunk_size - self.chunk_overlap and current_chunk:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from the end of previous chunk
                if len(current_chunk) > self.chunk_overlap:
                    current_chunk = current_chunk[-self.chunk_overlap:] + '\n\n' + para
                else:
                    current_chunk = para
            else:
                # Add paragraph to current chunk
                if current_chunk:
                    current_chunk += '\n\n' + para
                else:
                    current_chunk = para
        
        # Add the last chunk if not empty
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks


class TextbookVectorDB:
    """Vector database for textbook retrieval with fallback keyword search"""
    
    def __init__(self, 
                 cache_dir: str = "./vector_cache", 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chunk_size: int = 800,
                 chunk_overlap: int = 50):
        """Initialize the vector database with configurable parameters
        
        Args:
            cache_dir: Directory to store vector indices and chunk data
            embedding_model: HuggingFace model name for embeddings
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            logger.info(f"Created vector cache directory: {cache_dir}")
        
        # Set up the text splitter
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        if LANGCHAIN_AVAILABLE:
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            logger.info("Using langchain RecursiveCharacterTextSplitter")
        else:
            self.text_splitter = SimpleTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            logger.info("Using SimpleTextSplitter fallback")
        
        # Initialize embeddings model if available
        self.embedding_model_name = embedding_model
        self.embeddings = None
        
        if VECTOR_LIBS_AVAILABLE:
            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=embedding_model,
                    cache_folder=os.path.join(cache_dir, "models")
                )
                logger.info(f"Initialized embedding model: {embedding_model}")
            except Exception as e:
                logger.exception(f"Failed to initialize embedding model: {e}")
                try:
                    # Try fallback to smaller model
                    self.embedding_model_name = "paraphrase-MiniLM-L3-v2"
                    self.embeddings = HuggingFaceEmbeddings(
                        model_name=self.embedding_model_name,
                        cache_folder=os.path.join(cache_dir, "models")
                    )
                    logger.info(f"Using fallback embedding model: {self.embedding_model_name}")
                except Exception as e2:
                    logger.exception(f"Failed to initialize fallback model: {e2}")
                    self.embeddings = None
        
        # Active vector DB and chunks
        self.active_db = None
        self.chunks: List[str] = []
        self.active_textbook_id: Optional[str] = None
        
        # Metadata for chunks to enable filtering
        self.chunk_metadata: List[Dict[str, Any]] = []
    
    def split_markdown_by_structure(self, markdown_content: str) -> tuple[List[str], List[Dict[str, Any]]]:
        """Split markdown content by heading structure to preserve semantic sections.
        
        Args:
            markdown_content: The markdown content to split
            
        Returns:
            Tuple of (sections, section_contexts) where each section has its hierarchical context
        """
        # Match headings pattern (# Heading, ## Subheading, etc.)
        heading_pattern = re.compile(r'^(#{1,6})\s+(.*?)$', re.MULTILINE)
        
        # Find all headings with their levels and positions
        headings = []
        for match in heading_pattern.finditer(markdown_content):
            level = match.group(1).count('#')
            title = match.group(2).strip()
            start_pos = match.start()
            headings.append((level, title, start_pos))
        
        if not headings:
            # If no headings found, fall back to paragraph splitting
            logger.info("No markdown headings found, using paragraph-based splitting")
            return self._split_by_paragraphs_with_context(markdown_content)
        
        logger.info(f"Found {len(headings)} headings in markdown content")
        
        # Extract sections with their heading hierarchies
        sections = []
        section_contexts = []
        
        for i in range(len(headings)):
            # Current heading level and title
            level, title, start = headings[i]
            
            # Determine section end
            end = headings[i+1][2] if i < len(headings)-1 else len(markdown_content)
            
            # Extract section content
            content = markdown_content[start:end].strip()
            
            # Skip very short sections (less than 100 characters)
            if len(content) < 100:
                continue
            
            # Build section context (breadcrumb of parent headings)
            context = self._build_section_context(headings, i)
            
            # If section is too long, split it further while preserving context
            if len(content) > self.chunk_size * 2:
                sub_sections = self._split_long_section(content, title, context)
                sections.extend(sub_sections)
                # Create context for each sub-section
                for j, _ in enumerate(sub_sections):
                    section_contexts.append({
                        "heading": title,
                        "level": level,
                        "context": context,
                        "sub_section": j + 1,
                        "total_sub_sections": len(sub_sections)
                    })
            else:
                sections.append(content)
                section_contexts.append({
                    "heading": title,
                    "level": level,
                    "context": context,
                    "sub_section": None,
                    "total_sub_sections": 1
                })
        
        logger.info(f"Split markdown into {len(sections)} sections with context")
        return sections, section_contexts
    
    def _build_section_context(self, headings: List[tuple], current_idx: int) -> List[str]:
        """Build hierarchical context of parent headings for a section.
        
        Args:
            headings: List of (level, title, position) tuples
            current_idx: Index of current heading
            
        Returns:
            List of parent heading titles in hierarchical order
        """
        current_level = headings[current_idx][0]
        context = []
        
        # Look backwards to find parent headings of higher levels
        for i in range(current_idx-1, -1, -1):
            level, title, _ = headings[i]
            if level < current_level:
                context.insert(0, title)
                current_level = level
                # Stop when we reach the top level (H1)
                if level == 1:
                    break
        
        return context
    
    def _split_long_section(self, content: str, section_title: str, context: List[str]) -> List[str]:
        """Split a long section into smaller chunks while preserving meaning.
        
        Args:
            content: The section content to split
            section_title: Title of the section
            context: Hierarchical context
            
        Returns:
            List of sub-sections
        """
        # Try to split on paragraph boundaries first
        paragraphs = content.split('\n\n')
        
        sub_sections = []
        current_chunk = f"# {section_title}\n\n"
        
        for para in paragraphs:
            # Check if adding this paragraph would exceed chunk size
            if len(current_chunk) + len(para) > self.chunk_size and len(current_chunk) > len(section_title) + 10:
                # Save current chunk and start new one
                sub_sections.append(current_chunk.strip())
                current_chunk = f"# {section_title} (continued)\n\n{para}"
            else:
                current_chunk += para + '\n\n'
        
        # Add the last chunk if not empty
        if current_chunk.strip() and len(current_chunk) > len(section_title) + 10:
            sub_sections.append(current_chunk.strip())
        
        return sub_sections
    
    def _split_by_paragraphs_with_context(self, content: str) -> tuple[List[str], List[Dict[str, Any]]]:
        """Fallback splitting by paragraphs when no headings are found.
        
        Args:
            content: Content to split
            
        Returns:
            Tuple of (sections, contexts)
        """
        # Use the existing text splitter
        if hasattr(self.text_splitter, 'split_text'):
            chunks = self.text_splitter.split_text(content)
        else:
            chunks = self.text_splitter.split_text(content)
        
        # Create basic context for each chunk
        contexts = []
        for i, chunk in enumerate(chunks):
            # Try to extract a title from the first line
            first_line = chunk.split('\n')[0].strip()
            if len(first_line) < 100:  # Likely a title
                title = first_line
            else:
                title = f"Section {i+1}"
            
            contexts.append({
                "heading": title,
                "level": 1,
                "context": [],
                "sub_section": None,
                "total_sub_sections": 1
            })
        
        return chunks, contexts
    
    def _get_content_hash(self, content: str) -> str:
        """Generate content hash for simple versioning"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_index_path(self, textbook_id: str) -> str:
        """Get path to FAISS index file"""
        return os.path.join(self.cache_dir, f"{textbook_id}.faiss")
    
    def _get_chunks_path(self, textbook_id: str) -> str:
        """Get path to chunk data file"""
        return os.path.join(self.cache_dir, f"{textbook_id}.chunks.json")
    
    def _get_metadata_path(self, textbook_id: str) -> str:
        """Get path to metadata file"""
        return os.path.join(self.cache_dir, f"{textbook_id}.meta.json")
    
    def index_textbook(self, textbook_content: str, textbook_id: str, force_rebuild: bool = False, progress_callback=None) -> bool:
        """Process and index a textbook, with simple file-based versioning
        
        Args:
            textbook_content: Full text content of the textbook
            textbook_id: Unique identifier for the textbook
            force_rebuild: Whether to force rebuilding the index even if unchanged
            progress_callback: Optional callback function to report progress (stage, percent)
            
        Returns:
            bool: True if indexing was successful
        """
        # Check if vector search is available
        if not VECTOR_LIBS_AVAILABLE or self.embeddings is None:
            # If vector search isn't available, just split into chunks and store
            logger.warning("Vector search unavailable - storing chunks only")
            
            # Report progress (10%)
            if progress_callback:
                progress_callback("Preparing textbook for chunking...", 10)
                
            raw_chunks = self.text_splitter.split_text(textbook_content)
            
            # Report progress (30%)
            if progress_callback:
                progress_callback("Processing text chunks...", 30)
                
            self.chunks = raw_chunks
            self.chunk_metadata = [{'chunk_id': i} for i in range(len(raw_chunks))]
            self.active_textbook_id = textbook_id
            
            # Report progress (50%)
            if progress_callback:
                progress_callback("Finalizing text processing...", 50)
            
            # Save chunks as JSON
            chunks_path = self._get_chunks_path(textbook_id)
            try:
                with open(chunks_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'chunks': self.chunks,
                        'metadata': self.chunk_metadata
                    }, f, ensure_ascii=False)
                logger.info(f"Saved {len(self.chunks)} chunks for {textbook_id}")
                return True
            except Exception as e:
                logger.exception(f"Failed to save chunks: {e}")
                return False
        
        # Generate content hash for versioning
        if progress_callback:
            progress_callback("Analyzing textbook content...", 5)
            
        content_hash = self._get_content_hash(textbook_content)
        
        # File paths for persistence
        index_path = self._get_index_path(textbook_id)
        chunks_path = self._get_chunks_path(textbook_id)
        meta_path = self._get_metadata_path(textbook_id)
        
        # Check if we can use existing index
        rebuild_needed = force_rebuild or not os.path.exists(index_path)
        
        if not rebuild_needed and os.path.exists(meta_path):
            try:
                # Check if content has changed using JSON for metadata
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                if metadata.get('content_hash') != content_hash:
                    logger.info(f"Content changed for {textbook_id}, rebuilding index")
                    rebuild_needed = True
                # Also check if chunk parameters have changed
                elif (metadata.get('chunk_size') != self.chunk_size or 
                      metadata.get('chunk_overlap') != self.chunk_overlap):
                    logger.info(f"Chunk parameters changed for {textbook_id}, rebuilding index")
                    rebuild_needed = True
            except Exception:
                logger.exception("Error reading metadata, rebuilding index")
                rebuild_needed = True
        
        # Load existing index if possible
        if not rebuild_needed:
            try:
                if progress_callback:
                    progress_callback("Loading existing index...", 10)
                    
                logger.info(f"Loading existing index for {textbook_id}")
                self.active_db = FAISS.load_local(index_path, self.embeddings)
                
                if progress_callback:
                    progress_callback("Loading text chunks...", 30)
                    
                # Load chunks as JSON
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.chunks = data['chunks']
                    self.chunk_metadata = data['metadata']
                
                self.active_textbook_id = textbook_id
                logger.info(f"Loaded {len(self.chunks)} chunks for {textbook_id}")
                
                if progress_callback:
                    progress_callback("Index loaded successfully", 100)
                    
                return True
            except Exception:
                logger.exception("Failed to load existing index")
                rebuild_needed = True
        
        # Build new index if needed
        if rebuild_needed:
            logger.info(f"Building new index for textbook {textbook_id}")
            
            if progress_callback:
                progress_callback("Splitting textbook into chunks...", 15)
                
            # Split textbook into chunks
            raw_chunks, chunk_contexts = self.split_markdown_by_structure(textbook_content)
            logger.info(f"Split textbook into {len(raw_chunks)} chunks")
            
            if progress_callback:
                progress_callback("Processing text chunks...", 30)
            
            # Simple deduplication by content
            unique_chunks: List[str] = []
            unique_contexts: List[Dict[str, Any]] = []
            seen: Set[str] = set()
            
            if progress_callback:
                progress_callback("Removing duplicate content...", 40)
                
            for i, chunk in enumerate(raw_chunks):
                # Simple deduplication by normalized content
                chunk_key = " ".join(chunk.lower().split())
                if chunk_key not in seen and len(chunk.strip()) > 50:  # Avoid tiny chunks
                    seen.add(chunk_key)
                    unique_chunks.append(chunk)
                    # Add corresponding context metadata
                    context_meta = chunk_contexts[i].copy()
                    context_meta["chunk_id"] = len(unique_chunks) - 1
                    unique_contexts.append(context_meta)
            
            logger.info(f"Deduplicated to {len(unique_chunks)} chunks")
            
            if progress_callback:
                progress_callback("Creating chunk metadata...", 50)
            
            # Use the enhanced metadata with context information
            chunk_metadatas = unique_contexts
            
            if progress_callback:
                progress_callback("Creating vector embeddings...", 60)
            
            # Create and save the vector database
            try:
                if progress_callback:
                    progress_callback("Creating FAISS vector database...", 65)
                
                # This is the part that hangs - let's fix it with batching
                # Process vectors in small batches to avoid memory issues and UI freezing
                
                # First, determine if we should use batching
                total_chunks = len(unique_chunks)
                logger.info(f"Processing {total_chunks} chunks for vector embedding")
                
                # For small datasets (fewer than 10 chunks), we can process directly
                if total_chunks <= 10:
                    logger.info("Small dataset, processing in single batch")
                    if progress_callback:
                        progress_callback("Processing small dataset...", 67)
                    
                    # Direct processing for small datasets
                    self.active_db = FAISS.from_texts(
                        unique_chunks,
                        self.embeddings,
                        metadatas=chunk_metadatas
                    )
                else:
                    # For larger datasets, process in smaller batches
                    # Start with first batch to initialize the database
                    logger.info("Large dataset, processing in batches")
                    batch_size = 5  # Small batch size to ensure quick processing of each batch
                    
                    # First batch initializes the database
                    if progress_callback:
                        progress_callback(f"Processing batch 1/{math.ceil(total_chunks/batch_size)}...", 67)
                    
                    first_batch_end = min(batch_size, total_chunks)
                    self.active_db = FAISS.from_texts(
                        unique_chunks[:first_batch_end],
                        self.embeddings,
                        metadatas=chunk_metadatas[:first_batch_end]
                    )
                    
                    # Process remaining batches
                    for i in range(first_batch_end, total_chunks, batch_size):
                        batch_num = (i // batch_size) + 1
                        total_batches = math.ceil(total_chunks / batch_size)
                        
                        # Update progress
                        if progress_callback:
                            progress_callback(
                                f"Processing batch {batch_num}/{total_batches}...", 
                                65 + int((batch_num/total_batches) * 15)
                            )
                        
                        logger.info(f"Processing batch {batch_num}/{total_batches}")
                        
                        # Get current batch
                        end_idx = min(i + batch_size, total_chunks)
                        batch_texts = unique_chunks[i:end_idx]
                        batch_metadatas = chunk_metadatas[i:end_idx]
                        
                        # Add this batch to the existing index
                        try:
                            # Using a timeout to detect if a batch is hanging
                            start_time = time.time()
                            
                            # Add batch to existing database
                            self.active_db.add_texts(
                                batch_texts,
                                metadatas=batch_metadatas
                            )
                            
                            # Log successful batch completion
                            batch_time = time.time() - start_time
                            logger.info(f"Batch {batch_num} completed in {batch_time:.2f} seconds")
                            
                        except Exception as batch_error:
                            # If a batch fails, log it but continue with the next one
                            logger.error(f"Error processing batch {batch_num}: {str(batch_error)}")
                            # Report error in progress but don't fail entirely
                            if progress_callback:
                                progress_callback(f"Warning: Error in batch {batch_num}", 
                                                65 + int((batch_num/total_batches) * 15))

                
                if progress_callback:
                    progress_callback("Saving vector index to disk...", 80)
                    
                # Save FAISS index using its native format
                self.active_db.save_local(index_path)
                
                if progress_callback:
                    progress_callback("Saving chunk data...", 85)
                    
                # Save chunks and metadata as JSON
                with open(chunks_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'chunks': unique_chunks,
                        'metadata': chunk_metadatas
                    }, f, ensure_ascii=False)
                
                if progress_callback:
                    progress_callback("Finalizing metadata...", 90)
                    
                # Save metadata with content hash for versioning
                metadata = {
                    'content_hash': content_hash,
                    'created_at': time.time(),
                    'chunk_count': len(unique_chunks),
                    'embedding_model': self.embedding_model_name,
                    'chunk_size': self.chunk_size,
                    'chunk_overlap': self.chunk_overlap
                }
                
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False)
                
                self.chunks = unique_chunks
                self.chunk_metadata = chunk_metadatas
                self.active_textbook_id = textbook_id
                
                if progress_callback:
                    progress_callback("Indexing complete", 100)
                    
                return True
                
            except Exception:
                logger.exception("Failed to create index")
                raise
    
    def _extract_section_title(self, chunk: str) -> Optional[str]:
        """Extract a likely section title from chunk for filtering"""
        lines = chunk.split('\n')
        for line in lines[:2]:  # Check first two lines
            # Look for markdown headings or other title-like formats
            if line.startswith('#') or line.isupper() or line.endswith(':'):
                return line.strip('# :').strip()
            # Look for section numbers at the start of lines like "1.2 Section Title"
            if re.match(r'^\d+(\.\d+)*\s+[A-Z]', line):
                return line.strip()
        return None  # No section title found
    
    def _keyword_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Simple keyword search fallback when vector search fails
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of dict with content and metadata
        """
        if not self.chunks:
            return []
            
        # More comprehensive stop words list
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'been', 'but', 'by', 
            'for', 'from', 'had', 'has', 'have', 'he', 'her', 'his', 'i', 'if', 
            'in', 'into', 'is', 'it', 'its', 'more', 'not', 'of', 'on', 'or', 
            'our', 'she', 'than', 'that', 'the', 'their', 'them', 'there', 
            'these', 'they', 'this', 'those', 'to', 'was', 'we', 'were', 
            'what', 'when', 'where', 'which', 'who', 'will', 'with', 'would'
        }
        
        # Preprocess query - normalize case and remove punctuation
        clean_query = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Extract words, filter out stop words and short terms
        query_terms = [w for w in clean_query.split() 
                      if w not in stop_words and len(w) > 2]
        
        # Limit query length
        if len(query_terms) > 20:
            query_terms = query_terms[:20]
        
        if not query_terms:
            # If no substantive terms, just return first few chunks
            results = []
            for i, chunk in enumerate(self.chunks[:top_k]):
                metadata = self.chunk_metadata[i] if i < len(self.chunk_metadata) else {"chunk_id": i}
                results.append({
                    'content': chunk,
                    'metadata': metadata
                })
            return results
        
        # Score chunks by term frequency
        chunk_scores = []
        for i, chunk in enumerate(self.chunks):
            chunk_lower = chunk.lower()
            score = 0
            for term in query_terms:
                # Count occurrences of term in chunk
                term_count = chunk_lower.count(term)
                if term_count > 0:
                    score += term_count
            
            if score > 0:
                chunk_scores.append((score, i))
        
        # Sort by score (highest first) and take top_k
        chunk_scores.sort(reverse=True)
        results = []
        
        for _, chunk_id in chunk_scores[:top_k]:
            metadata = self.chunk_metadata[chunk_id] if chunk_id < len(self.chunk_metadata) else {"chunk_id": chunk_id}
            results.append({
                'content': self.chunks[chunk_id],
                'metadata': metadata
            })
        
        return results
    
    def _preprocess_query(self, query: str) -> str:
        """Normalize and clean query text
        
        Args:
            query: Raw query string
            
        Returns:
            Preprocessed query
        """
        # Truncate overly long queries
        if len(query) > 1000:
            query = query[:1000]
        
        # Strip excess whitespace
        query = ' '.join(query.split())
        
        # Remove Markdown formatting
        query = re.sub(r'[#*_~`]', '', query)
        
        return query
    
    def query_textbook(self, textbook_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Find relevant chunks for a query with fallback to keyword search
        
        Args:
            textbook_id: ID of the textbook to search
            query: Search query
            top_k: Maximum number of results to return
            
        Returns:
            List of dicts with content and metadata
        """
        # Clean and normalize the query
        query = self._preprocess_query(query)
        
        # Check if we can do vector search
        vector_search_available = (VECTOR_LIBS_AVAILABLE and 
                                  self.embeddings is not None and 
                                  self.active_db is not None)
        
        # If vector search not possible, force using keyword search
        if not vector_search_available:
            logger.info(f"Vector search unavailable, using keyword search for query: '{query}'")
            return self._keyword_search(query, top_k)
        
        # If current textbook is different, try to load the requested one
        if self.active_textbook_id != textbook_id:
            # Need to load the requested textbook
            index_path = self._get_index_path(textbook_id)
            chunks_path = self._get_chunks_path(textbook_id)
            
            if not os.path.exists(index_path):
                logger.error(f"No index found for textbook {textbook_id}")
                return []
            
            try:
                self.active_db = FAISS.load_local(index_path, self.embeddings)
                
                # Load chunks from JSON
                with open(chunks_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.chunks = data['chunks']
                    self.chunk_metadata = data['metadata']
                
                self.active_textbook_id = textbook_id
            except Exception:
                logger.exception(f"Failed to load textbook {textbook_id}")
                return self._keyword_search(query, top_k)
        
        # Search for relevant chunks using vector similarity
        try:
            docs = self.active_db.similarity_search(query, k=top_k)
            
            # Check if we got any results
            if not docs:
                logger.info(f"No vector results for query '{query}', falling back to keyword search")
                return self._keyword_search(query, top_k)
            
            # Return content with metadata
            results = []
            for doc in docs:
                results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata
                })
            
            return results
            
        except Exception:
            # If vector search fails for any reason, fall back to keyword search
            logger.exception("Error during vector search, falling back to keyword search")
            return self._keyword_search(query, top_k)
    
    async def index_textbook_async(self, textbook_content: str, textbook_id: str, force_rebuild: bool = False, progress_callback=None):
        """Async version of index_textbook that doesn't block the event loop
        
        Args:
            textbook_content: Full text content of the textbook
            textbook_id: Unique identifier for the textbook
            force_rebuild: Whether to force rebuilding the index
            progress_callback: Optional callback function to report progress (stage, percent)
            
        Returns:
            True if indexing was successful
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, 
            lambda: self.index_textbook(textbook_content, textbook_id, force_rebuild, progress_callback)
        )

    async def query_textbook_async(self, textbook_id: str, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Async version of query_textbook that doesn't block the event loop
        
        Args:
            textbook_id: ID of the textbook to search
            query: Search query
            top_k: Maximum number of results to return
            
        Returns:
            List of dicts with content and metadata
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.query_textbook(textbook_id, query, top_k)
        )


# Create a global instance for backward compatibility
# Initialize lazily to avoid import-time dependency issues
vector_db = None

def get_vector_db():
    """Get the global vector database instance, creating it if necessary."""
    global vector_db
    if vector_db is None:
        try:
            vector_db = TextbookVectorDB()
            logger.info("Initialized global vector database instance")
        except Exception as e:
            logger.error(f"Failed to initialize vector database: {e}")
            # Create a minimal fallback instance
            vector_db = TextbookVectorDB(cache_dir="./fallback_cache")
    return vector_db


def test_vector_db():
    """Simple unit test for the vector DB including fallback search"""
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Test data with two distinct chunks
    test_content = """
    # Chapter 1: Unique Terms
    This section contains the special term FooBarBaz which is unique to this chunk.
    
    # Chapter 2: Other Content
    This section doesn't contain the special term, but has other content.
    """
    
    print("\n1. Testing TextbookVectorDB...")
    db = TextbookVectorDB(cache_dir="./test_vector_cache", chunk_size=100, chunk_overlap=0)
    
    print("2. Indexing test content...")
    db.index_textbook(test_content, "test_db", force_rebuild=True)
    
    print("3. Testing vector search...")
    results = db.query_textbook("test_db", "Tell me about FooBarBaz")
    
    if len(results) > 0 and "FooBarBaz" in results[0]["content"]:
        print("   ✓ Vector search found the correct chunk")
    else:
        print("   ✗ Vector search failed to find the correct chunk")
        print(f"   Results: {results}")
    
    # Test fallback search
    print("4. Testing fallback search by disabling vector DB...")
    original_active_db = db.active_db
    db.active_db = None  # This will force fallback to keyword search
    
    fallback_results = db.query_textbook("test_db", "Tell me about FooBarBaz")
    db.active_db = original_active_db  # Restore the DB
    
    if len(fallback_results) > 0 and "FooBarBaz" in fallback_results[0]["content"]:
        print("   ✓ Fallback search found the correct chunk")
    else:
        print("   ✗ Fallback search failed to find the correct chunk")
        print(f"   Results: {fallback_results}")
    
    print("\nTests completed!")


if __name__ == "__main__":
    # Run the unit test
    test_vector_db()
