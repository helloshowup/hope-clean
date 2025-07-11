#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Textbook Ingestion Script for RAG system.

Processes PDF and Markdown files into vector embeddings for semantic search.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ingest_textbook")

# Try to import required dependencies
try:
    from PyPDF2 import PdfReader
    PDF_READER_AVAILABLE = True
except ImportError:
    logger.warning("PyPDF2 not installed. Trying fallback PDF reader.")
    PDF_READER_AVAILABLE = False
    try:
        from pdfminer.high_level import extract_text
        PDFMINER_AVAILABLE = True
    except ImportError:
        PDFMINER_AVAILABLE = False
        logger.warning("pdfminer not installed. Will try other PDF methods.")

# Use a proper relative import for the package
from showup_tools.simplified_app.rag_system.textbook_vector_db import vector_db


def extract_text_from_file(file_path: str) -> Optional[str]:
    """Extract text from a PDF or Markdown file using available libraries
    
    Args:
        file_path: Path to the PDF or Markdown file
        
    Returns:
        Extracted text or None if extraction failed
    """
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return None
        
    extracted_text = None
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Handle Markdown files directly
    if file_ext in [".md", ".markdown"]:
        try:
            logger.info(f"Reading Markdown file: {file_path}")
            with open(file_path, "r", encoding="utf-8") as file:
                extracted_text = file.read()
            logger.info(f"Extracted {len(extracted_text)} characters from Markdown")
            return extracted_text
        except Exception as e:
            logger.error(f"Markdown reading failed: {e}")
            return None
    
    # Handle PDF files
    elif file_ext == ".pdf":
        # Try PyPDF2 first if available
        if PDF_READER_AVAILABLE:
            try:
                logger.info(f"Extracting text from PDF using PyPDF2: {file_path}")
                with open(file_path, "rb") as file:
                    reader = PdfReader(file)
                    text_parts = []
                    for page in reader.pages:
                        text_parts.append(page.extract_text())
                    extracted_text = "\n\n".join(text_parts)
                    logger.info(f"Extracted {len(text_parts)} pages, {len(extracted_text)} characters")
                    return extracted_text
            except Exception as e:
                logger.error(f"PyPDF2 extraction failed: {e}")
        
        # Try pdfminer if available
        if PDFMINER_AVAILABLE:
            try:
                logger.info(f"Extracting text from PDF using pdfminer: {file_path}")
                extracted_text = extract_text(file_path)
                logger.info(f"Extracted {len(extracted_text)} characters with pdfminer")
                return extracted_text
            except Exception as e:
                logger.error(f"pdfminer extraction failed: {e}")
        
        # Last resort - try using a subprocess call to pdftotext if installed
        try:
            import subprocess
            tmp_txt_file = file_path + ".txt"
            logger.info("Attempting extraction with pdftotext command line tool")
            result = subprocess.run(
                ["pdftotext", file_path, tmp_txt_file], 
                capture_output=True, 
                text=True, 
                check=False
            )
            
            if result.returncode == 0 and os.path.exists(tmp_txt_file):
                with open(tmp_txt_file, "r", encoding="utf-8") as f:
                    extracted_text = f.read()
                os.remove(tmp_txt_file)  # Clean up
                logger.info(f"Extracted {len(extracted_text)} characters with pdftotext")
                return extracted_text
            else:
                logger.error(f"pdftotext extraction failed: {result.stderr}")
        except Exception as e:
            logger.error(f"subprocess extraction failed: {e}")
        
        logger.error("All PDF extraction methods failed")
    else:
        logger.error(f"Unsupported file extension: {file_ext}")
    
    return None


def index_textbook(file_path: str, force_rebuild: bool = False):
    """Process a PDF or Markdown file and index it into the vector database
    
    Args:
        file_path: Path to the PDF or Markdown file
        force_rebuild: Whether to force rebuilding the index even if unchanged
        
    Returns:
        bool: True if indexing was successful
    """
    # Extract text from file
    content = extract_text_from_file(file_path)
    if not content:
        logger.error(f"Failed to extract text from {file_path}")
        return False
        
    # Create a textbook ID from the filename
    textbook_id = os.path.basename(file_path).replace(" ", "_").lower()
    
    # Index the textbook
    logger.info(f"Indexing textbook {textbook_id} with {len(content)} characters")
    success = vector_db.index_textbook(content, textbook_id, force_rebuild)
    
    if success:
        logger.info(f"Successfully indexed textbook: {textbook_id}")
    else:
        logger.error(f"Failed to index textbook: {textbook_id}")
        
    return success


def main():
    parser = argparse.ArgumentParser(description='Ingest a textbook PDF or Markdown into the vector database.')
    parser.add_argument('--file', '-f', required=True, help='Path to the PDF or Markdown file')
    parser.add_argument('--force', action='store_true', help='Force rebuild the index even if unchanged')
    
    args = parser.parse_args()
    success = index_textbook(args.file, force_rebuild=args.force)
    
    if success:
        print(f"✅ Successfully indexed textbook: {args.file}")
        return 0
    else:
        print(f"❌ Failed to index textbook: {args.file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
