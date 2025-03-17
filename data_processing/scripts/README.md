# Artwork CLIP Embedding and Search

This directory contains scripts for generating CLIP embeddings for artworks and searching through them using natural language queries.

## Overview

The pipeline consists of two main scripts:

1. `generate_clip_embeddings.py`: Loads artworks from Cleveland Museum of Art and CMOA datasets, fetches their images, and creates CLIP embeddings stored in ChromaDB.
2. `search_embeddings.py`: Allows searching for artworks using natural language queries against the CLIP embeddings stored in ChromaDB.

## Features

- **Efficient Batch Processing**: Images are processed in batches to maximize GPU utilization
- **Concurrent Image Fetching**: Multiple images are downloaded in parallel using ThreadPoolExecutor
- **Batch Upserts**: Embeddings are inserted into ChromaDB in batches for better performance
- **Robust Error Handling**: Comprehensive logging and error recovery mechanisms
- **Half-Precision Support**: Uses FP16 on compatible GPUs for faster processing
- **Detailed Performance Metrics**: Tracks and reports processing time for optimization

## Requirements

- Python 3.7+
- PyTorch
- transformers
- chromadb
- PIL
- requests
- matplotlib
- tqdm

## Usage

### 1. Generate Embeddings

To generate CLIP embeddings for artworks from Cleveland Museum of Art and CMOA datasets:

```bash
# Development mode (limit to 100 artworks per dataset)
python generate_clip_embeddings.py --limit 100 --collection_name "dev_artwork_images"

# Production mode (no limit)
python generate_clip_embeddings.py --collection_name "prod_artwork_images"
```

Options:
- `--data_dir`: Directory containing source datasets (default: project's data/source_datasets)
- `--chroma_path`: Path to store ChromaDB embeddings (default: project's data/processed_datasets/chroma_db)
- `--collection_name`: Name of the ChromaDB collection to store embeddings (default: "artwork_images")
- `--limit`: Limit number of artworks per dataset (for testing)
- `--batch_size`: Batch size for embedding generation (default: 16)
- `--upsert_batch_size`: Batch size for ChromaDB upserts (default: 100)
- `--max_workers`: Maximum number of threads for image fetching (default: 8)
- `--cpu`: Force CPU usage even if GPU is available
- `--reset`: Reset existing collection in ChromaDB

### 2. Search Embeddings

To search for artworks using natural language queries:

```bash
# Search in development collection
python search_embeddings.py --query "A painting of a child" --collection_name "dev_artwork_images"

# Search in production collection
python search_embeddings.py --query "A painting of a child" --collection_name "prod_artwork_images"
```

Options:
- `--query`: Natural language query to search for artworks (required)
- `--chroma_path`: Path to ChromaDB embeddings (default: project's data/processed_datasets/chroma_db)
- `--collection_name`: Name of the ChromaDB collection to search (default: "artwork_images")
- `--top_k`: Number of results to return (default: 5)
- `--no_images`: Don't display images
- `--cpu`: Force CPU usage even if GPU is available
- `--save_results`: Save results to the specified JSON file

## Examples

### Generate embeddings for 100 artworks from each dataset with custom batch sizes

```bash
python generate_clip_embeddings.py --limit 100 --collection_name "dev_artwork_images" --reset --batch_size 32 --upsert_batch_size 50 --max_workers 12
```

### Search for landscape paintings and save results

```bash
python search_embeddings.py --query "A landscape painting with mountains" --collection_name "dev_artwork_images" --top_k 10 --save_results landscape_results.json
```

### Search for portraits

```bash
python search_embeddings.py --query "A portrait of a woman" --collection_name "dev_artwork_images"
```

## Performance Optimization

The scripts include several optimizations for better performance:

1. **Batch Processing**: Images are processed in batches to maximize GPU utilization
2. **Concurrent Image Fetching**: Multiple images are downloaded in parallel
3. **Batch Upserts**: Embeddings are inserted into ChromaDB in batches
4. **Half-Precision**: Uses FP16 on compatible GPUs for faster processing
5. **Fallback Mechanisms**: If batch processing fails, falls back to individual processing

## Output

The `generate_clip_embeddings.py` script will output:
- `successful_embeddings.json`: Contains information about artworks that were successfully embedded
- `failed_embeddings.json`: Contains information about artworks that failed to be embedded and the reason for failure
- `clip_embedding_generation.log`: Detailed log of the embedding generation process

The `search_embeddings.py` script will:
- Display the search results in the terminal
- Show the images in a matplotlib window (unless `--no_images` is specified)
- Save results to a JSON file if `--save_results` is specified
- Log details to `clip_search.log` 