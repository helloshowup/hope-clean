# ShowupSquared Vector RAG System

A lean, local vector database and retrieval system for reducing token usage when generating content with the Claude API.

## Features

- **Efficient Textbook Chunking**: Breaks textbooks into optimally-sized chunks with minimal overlap
- **Vector-Based Retrieval**: Uses FAISS and HuggingFace embeddings for semantic search
- **Keyword Fallback**: Includes a reliable fallback when vector search isn't available
- **Two-Tier Caching**: Memory + disk caching for fast repeat access
- **Accurate Token Counting**: Optimized for Claude API with calibration
- **Async-Friendly**: Non-blocking I/O operations for event loop safety
- **Minimal Dependencies**: Works with local models, no cloud services required

## Integration with ShowupSquared

This system is designed to reduce token usage in the `simplified_app.py` workflow by replacing full textbook submission with relevant chunk retrieval.

## Getting Started

### Requirements

Install the required packages:

```bash
pip install langchain langchain-community sentence-transformers faiss-cpu tiktoken
```

### Basic Usage

```python
# Import the RAG system
from rag_system import enhanced_generate_content

# Use in place of your current content generation function
async def generate_content(variables, template, settings=None):
    return await enhanced_generate_content(variables, template, settings)
```

### Example in the Content Generation Workflow

Replace your existing Claude API call in `simplified_workflow.py` with the RAG-enhanced version:

```python
# Before:
# content = await generate_with_claude(prompt, max_tokens, temperature, model)

# After:
from rag_system import enhanced_generate_content

# This function handles template substitution, RAG, and API calls
content = await enhanced_generate_content(variables, template, settings)
```

## Components

### TextbookVectorDB

Handles textbook chunking, embedding, and retrieval. Uses a file-based versioning system to avoid rebuilding indices unnecessarily.

```python
from rag_system import vector_db

# Index a textbook
await vector_db.index_textbook_async(textbook_content, "my_textbook_id")

# Query for relevant chunks 
results = await vector_db.query_textbook_async("my_textbook_id", "What is academic integrity?")
```

### SimpleCacheManager

Provides two-tier caching (memory + disk) with JSON persistence.

```python
from rag_system import cache

# Generate a cache key
cache_key = cache.get_cache_key("content_type", {"param1": "value1"})

# Check cache before expensive operations
cached_result = cache.get(cache_key)
if cached_result:
    return cached_result
    
# Store results
cache.set(cache_key, result)
```

### ClaudeTokenizer

Accurately counts tokens for Claude API calls.

```python
from rag_system import count_tokens

# Count tokens in a string
token_count = count_tokens("This is a test string")
```

## Testing the System

Run the included test script to validate the vector DB functionality:

```bash
python -m rag_system.textbook_vector_db
```

Or to test the full RAG pipeline with a sample handbook:

```bash
python -m rag_system.rag_integration
```

## Troubleshooting

- If you see errors about missing dependencies, install the required packages
- If vector search fails, the system will automatically fall back to keyword search
- For accuracy issues, try adjusting `chunk_size` and `chunk_overlap` in the TextbookVectorDB initialization

## Indexing a Handbook Locally

After installing the tools package in editable mode, you can build a
vector index for a PDF or Markdown handbook using the provided CLI:

```bash
pip install -e ./showup-tools  # if not already installed
python -m showup_tools.simplified_app.rag_system.ingest_textbook \
    --file path/to/handbook.pdf
```

Use `--force` to rebuild an existing index. The generated vectors and
chunk data are stored under `vector_cache/` in your working directory.
The database operates entirely on the local machine—there is no remote
search capability. Indexing very large handbooks (200+ pages) may take
several minutes to complete.
