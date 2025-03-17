#!/usr/bin/env python3
"""
Generate CLIP Embeddings for Museum Artworks

This script loads artworks from Cleveland Museum of Art and CMOA datasets,
fetches their images, and creates CLIP embeddings stored in a vector database (ChromaDB).
"""

import os
import sys
import argparse
import requests
import logging
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import torch
import chromadb
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple, Any
import time
import textwrap

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

# Import directly from the file path
sys.path.insert(0, str(project_root))
from data_processing.dataset_manager import DatasetManager
from models.data_models import UnifiedArtwork

# Configuration
CHROMA_PATH = str(project_root / "data" / "processed_datasets" / "chroma_db")
BATCH_SIZE = 16  # Adjust based on GPU memory
MODEL_NAME = "openai/clip-vit-base-patch32"
MAX_WORKERS = 8  # For concurrent image fetching
UPSERT_BATCH_SIZE = 100  # Number of items to upsert at once

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clip_embedding_generation.log')
    ]
)
logger = logging.getLogger(__name__)


class CLIPEmbedder:
    def __init__(self, use_gpu=True):
        """Initialize the CLIP model for embedding generation using Hugging Face Transformers."""
        from transformers import CLIPProcessor, CLIPModel
        
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")
        
        # Load model with half precision for GPU if available
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        logger.info(f"Loading CLIP model: {MODEL_NAME}")
        self.model = CLIPModel.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        
        # Set to eval mode
        self.model.eval()

    def embed_images_batch(self, images: List[Optional[Image.Image]]) -> List[Optional[List[float]]]:
        """
        Embed a batch of images at once.
        Returns a list of embeddings, with None for any images that couldn't be processed.
        """
        # Filter out None images and keep track of their positions
        valid_images = []
        valid_indices = []
        
        for i, img in enumerate(images):
            if img is not None:
                valid_images.append(img)
                valid_indices.append(i)
        
        if not valid_images:
            return [None] * len(images)
        
        # Process all valid images in one batch
        try:
            with torch.no_grad():
                inputs = self.processor(
                    images=valid_images,
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
                
                image_features = self.model.get_image_features(**inputs)
                image_features = image_features / image_features.norm(dim=1, keepdim=True)
                embeddings = image_features.cpu().numpy().tolist()
                
                # Reconstruct the original list with None for invalid images
                result = [None] * len(images)
                for i, idx in enumerate(valid_indices):
                    result[idx] = embeddings[i]
                
                return result
        except Exception as e:
            logger.exception(f"Error embedding batch of {len(valid_images)} images: {e}")
            # If batch processing fails, try one by one as fallback
            return self._embed_images_individually(images)
    
    def _embed_images_individually(self, images: List[Optional[Image.Image]]) -> List[Optional[List[float]]]:
        """Fallback method to embed images one by one if batch processing fails."""
        results = []
        for img in images:
            if img is None:
                results.append(None)
                continue
                
            try:
                with torch.no_grad():
                    inputs = self.processor(
                        images=img,
                        return_tensors="pt"
                    ).to(self.device)
                    
                    image_features = self.model.get_image_features(**inputs)
                    image_features = image_features / image_features.norm(dim=1, keepdim=True)
                    results.append(image_features.cpu().numpy()[0].tolist())
            except Exception as e:
                logger.warning(f"Error embedding individual image: {e}")
                results.append(None)
        
        return results
    
    def get_text_embedding(self, text: str) -> List[float]:
        """Get embedding for a text query."""
        with torch.no_grad():
            inputs = self.processor(
                text=[text],
                return_tensors="pt",
                padding=True
            ).to(self.device)
            
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=1, keepdim=True)
            
            return text_features.cpu().numpy()[0].tolist()


def fetch_image(url: str, timeout: int = 10) -> Optional[Image.Image]:
    """Fetch an image from a URL and return a PIL Image object."""
    if not url:
        return None
    
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return Image.open(BytesIO(response.content)).convert('RGB')
    except Exception as e:
        logger.warning(f"Error fetching image from {url}: {e}")
        return None


def fetch_images_concurrently(urls: List[str], max_workers: int = MAX_WORKERS) -> List[Optional[Image.Image]]:
    """Fetch multiple images concurrently using ThreadPoolExecutor."""
    images = [None] * len(urls)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all fetch tasks
        future_to_index = {}
        for i, url in enumerate(urls):
            if url:
                future = executor.submit(fetch_image, url)
                future_to_index[future] = i
        
        # Process results as they complete
        for future in tqdm(as_completed(future_to_index), total=len(future_to_index), desc="Fetching images"):
            idx = future_to_index[future]
            try:
                images[idx] = future.result()
            except Exception as e:
                logger.warning(f"Error in future for image {idx}: {e}")
    
    return images


def get_artwork_description(artwork: UnifiedArtwork) -> str:
    """Create a text description of the artwork for embedding."""
    parts = []
    
    # Add title
    if artwork.object.name:
        parts.append(f"Title: {artwork.object.name}")
    
    # Add artist
    if artwork.artist.name:
        parts.append(f"Artist: {artwork.artist.name}")
    
    # Add date
    if artwork.object.creation_date:
        parts.append(f"Date: {artwork.object.creation_date.display_text}")
    
    # Add type
    if artwork.object.type:
        parts.append(f"Type: {artwork.object.type}")
    
    # Add museum
    if artwork.museum.name:
        parts.append(f"Museum: {artwork.museum.name}")
    
    # Join all parts with separator
    return " | ".join(parts)


def create_artwork_metadata(artwork: UnifiedArtwork) -> Dict:
    """Create metadata dictionary for ChromaDB from artwork."""
    metadata = {
        "id": artwork.id,
        "title": artwork.object.name or "",
        "artist": artwork.artist.name or "",
        "museum": artwork.museum.name or "",
        "type": artwork.object.type or "",
        "url": str(artwork.web_url) if artwork.web_url else "",
        "image_url": str(artwork.images[0].url) if artwork.images and artwork.images[0].url else ""
    }
    
    # Add date information if available
    if artwork.object.creation_date:
        metadata["date_text"] = artwork.object.creation_date.display_text
        if artwork.object.creation_date.start_year:
            metadata["start_year"] = str(artwork.object.creation_date.start_year)
        if artwork.object.creation_date.end_year:
            metadata["end_year"] = str(artwork.object.creation_date.end_year)
        metadata["is_bce"] = str(artwork.object.creation_date.is_bce)
    
    # Add artist birth/death years if available
    if artwork.artist.birth_year:
        metadata["artist_birth"] = str(artwork.artist.birth_year)
    if artwork.artist.death_year:
        metadata["artist_death"] = str(artwork.artist.death_year)
    
    return metadata


def process_artwork_batches(
    embedder: CLIPEmbedder,
    artworks: List[UnifiedArtwork],
    collection_name: str,
    batch_size: int = BATCH_SIZE,
    upsert_batch_size: int = UPSERT_BATCH_SIZE,
    max_workers: int = MAX_WORKERS,
    chroma_path: str = CHROMA_PATH
) -> Tuple[List[Dict], List[Dict]]:
    """Process artworks in batches to generate embeddings and upsert to ChromaDB."""
    # Initialize ChromaDB client and collection
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    image_collection = chroma_client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )
    
    # Track successful and failed embeddings
    successful_embeddings = []
    failed_embeddings = []
    
    # Prepare for batch processing
    total_batches = (len(artworks) + batch_size - 1) // batch_size
    
    # Process artworks in batches
    for batch_idx in tqdm(range(total_batches), desc="Processing batches"):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(artworks))
        batch_artworks = artworks[start_idx:end_idx]
        
        # Extract image URLs from batch
        batch_urls = []
        for artwork in batch_artworks:
            url = str(artwork.images[0].url) if artwork.images and artwork.images[0].url else None
            batch_urls.append(url)
        
        # Fetch images concurrently
        batch_images = fetch_images_concurrently(batch_urls, max_workers=max_workers)
        
        # Generate embeddings for the batch
        batch_embeddings = embedder.embed_images_batch(batch_images)
        
        # Prepare data for ChromaDB upsert
        upsert_ids = []
        upsert_embeddings = []
        upsert_documents = []
        upsert_metadatas = []
        
        # Process each artwork in the batch
        for i, (artwork, image, embedding) in enumerate(zip(batch_artworks, batch_images, batch_embeddings)):
            artwork_id = artwork.id
            
            # Skip if no image URL
            if not artwork.images or not artwork.images[0].url:
                failed_embeddings.append({
                    "id": artwork_id,
                    "title": artwork.object.name,
                    "reason": "No image URL"
                })
                continue
            
            # Skip if image fetch failed
            if image is None:
                failed_embeddings.append({
                    "id": artwork_id,
                    "title": artwork.object.name,
                    "reason": "Failed to fetch image"
                })
                continue
            
            # Skip if embedding generation failed
            if embedding is None:
                failed_embeddings.append({
                    "id": artwork_id,
                    "title": artwork.object.name,
                    "reason": "Failed to generate embedding"
                })
                continue
            
            # Create metadata and description
            metadata = create_artwork_metadata(artwork)
            description = get_artwork_description(artwork)
            
            # Add to upsert batch - Convert ID to string for ChromaDB
            upsert_ids.append(str(artwork_id))
            upsert_embeddings.append(embedding)
            upsert_documents.append(description)
            upsert_metadatas.append(metadata)
            
            # Track successful embedding
            successful_embeddings.append({
                "id": artwork_id,
                "title": artwork.object.name,
                "artist": artwork.artist.name,
                "museum": artwork.museum.name,
                "image_url": str(artwork.images[0].url)
            })
            
            # Upsert in batches to ChromaDB
            if len(upsert_ids) >= upsert_batch_size or i == len(batch_artworks) - 1:
                if upsert_ids:  # Only upsert if we have data
                    try:
                        image_collection.upsert(
                            ids=upsert_ids,
                            embeddings=upsert_embeddings,
                            documents=upsert_documents,
                            metadatas=upsert_metadatas
                        )
                        logger.info(f"Upserted batch of {len(upsert_ids)} embeddings")
                    except Exception as e:
                        logger.exception(f"Error upserting batch to ChromaDB: {e}")
                        # Add these to failed embeddings
                        for j in range(len(upsert_ids)):
                            # Get original ID (integer) from the string ID
                            original_id = int(upsert_ids[j])
                            failed_embeddings.append({
                                "id": original_id,
                                "title": upsert_metadatas[j]["title"],
                                "reason": f"ChromaDB upsert error: {str(e)}"
                            })
                        
                        # Remove from successful embeddings
                        # Convert successful embedding IDs to strings for comparison
                        successful_embeddings = [s for s in successful_embeddings 
                                               if str(s["id"]) not in upsert_ids]
                    
                    # Reset batch lists
                    upsert_ids = []
                    upsert_embeddings = []
                    upsert_documents = []
                    upsert_metadatas = []
    
    return successful_embeddings, failed_embeddings


def main():
    parser = argparse.ArgumentParser(description="Generate CLIP embeddings for museum artworks")
    parser.add_argument("--data_dir", type=str, default=None,
                        help="Directory containing source datasets")
    parser.add_argument("--chroma_path", type=str, default=CHROMA_PATH,
                        help=f"Path to store ChromaDB embeddings (default: {CHROMA_PATH})")
    parser.add_argument("--collection_name", type=str, default="artwork_images",
                        help="Name of the ChromaDB collection to store embeddings")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of artworks per dataset (for testing)")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE,
                        help=f"Batch size for embedding generation (default: {BATCH_SIZE})")
    parser.add_argument("--upsert_batch_size", type=int, default=UPSERT_BATCH_SIZE,
                        help=f"Batch size for ChromaDB upserts (default: {UPSERT_BATCH_SIZE})")
    parser.add_argument("--max_workers", type=int, default=MAX_WORKERS,
                        help=f"Maximum number of threads for image fetching (default: {MAX_WORKERS})")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage even if GPU is available")
    parser.add_argument("--reset", action="store_true",
                        help="Reset existing collection in ChromaDB")
    
    args = parser.parse_args()
    
    # Use local variables instead of modifying globals
    chroma_path = args.chroma_path
    batch_size = args.batch_size
    upsert_batch_size = args.upsert_batch_size
    max_workers = args.max_workers
    
    # Create ChromaDB directory if it doesn't exist
    os.makedirs(chroma_path, exist_ok=True)
    
    # Initialize ChromaDB client
    chroma_client = chromadb.PersistentClient(path=chroma_path)
    
    # Reset collection if requested
    if args.reset:
        try:
            chroma_client.delete_collection(args.collection_name)
            logger.info(f"Existing collection '{args.collection_name}' deleted.")
        except Exception as e:
            logger.warning(f"Error deleting collection: {e}")
    
    # Initialize dataset manager
    manager = DatasetManager(data_dir=args.data_dir)
    
    # Load artworks from Cleveland Museum of Art and CMOA
    logger.info("Loading artworks from Cleveland Museum of Art...")
    start_time = time.time()
    cleveland_artworks = manager.get_dataset("cleveland_art", limit=args.limit, with_images_only=True)
    logger.info(f"Loaded {len(cleveland_artworks)} artworks from Cleveland Museum of Art in {time.time() - start_time:.2f}s")
    
    logger.info("Loading artworks from CMOA...")
    start_time = time.time()
    cmoa_artworks = manager.get_dataset("cmoa", limit=args.limit, with_images_only=True)
    logger.info(f"Loaded {len(cmoa_artworks)} artworks from CMOA in {time.time() - start_time:.2f}s")
    
    # Combine artworks
    all_artworks = cleveland_artworks + cmoa_artworks
    logger.info(f"Total artworks to process: {len(all_artworks)}")
    
    # Initialize CLIP embedder
    embedder = CLIPEmbedder(use_gpu=not args.cpu)
    
    # Process all artworks in batches
    start_time = time.time()
    successful, failed = process_artwork_batches(
        embedder, 
        all_artworks, 
        args.collection_name,
        batch_size=batch_size,
        upsert_batch_size=upsert_batch_size,
        max_workers=max_workers,
        chroma_path=chroma_path
    )
    processing_time = time.time() - start_time
    
    # Print summary
    logger.info("\nEmbedding Generation Summary:")
    logger.info(f"Total artworks processed: {len(all_artworks)}")
    logger.info(f"Successful embeddings: {len(successful)}")
    logger.info(f"Failed embeddings: {len(failed)}")
    logger.info(f"Total processing time: {processing_time:.2f}s")
    if len(all_artworks) > 0:
        logger.info(f"Average time per artwork: {processing_time / len(all_artworks):.2f}s")
    
    # Save results to JSON
    import json
    
    # Save detailed information to a text file
    txt_output_file = f"{args.collection_name}_embedded_artworks.txt"
    with open(txt_output_file, "w", encoding="utf-8") as f:
        f.write(f"Successfully Embedded Artworks in Collection: {args.collection_name}\n")
        f.write(f"Total: {len(successful)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, artwork in enumerate(successful, 1):
            f.write(f"{i}. ID: {artwork['id']}\n")
            f.write(f"   Title: {artwork['title']}\n")
            f.write(f"   Artist: {artwork['artist']}\n")
            f.write(f"   Museum: {artwork['museum']}\n")
            f.write(f"   Image URL: {artwork['image_url']}\n")
            
            # Add a separator between artworks
            f.write("\n" + "-" * 80 + "\n\n")
    
    logger.info(f"Detailed artwork information saved to {txt_output_file}")
    
    with open("successful_embeddings.json", "w") as f:
        json.dump(successful, f, indent=2)
    
    with open("failed_embeddings.json", "w") as f:
        json.dump(failed, f, indent=2)
    
    logger.info("\nResults saved to:")
    logger.info(f"- successful_embeddings.json ({len(successful)} artworks)")
    logger.info(f"- failed_embeddings.json ({len(failed)} artworks)")
    logger.info(f"- {txt_output_file} (detailed information for querying)")


if __name__ == "__main__":
    main() 