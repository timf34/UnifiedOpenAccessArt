#!/usr/bin/env python3
"""
Evaluate Artwork Embeddings

This script evaluates the quality of CLIP embeddings stored in ChromaDB using two methods:
1. Retrieval Consistency: Measures how consistent the results are for similar queries
2. Synthetic Query Generation: Measures how well the system retrieves known artworks for synthetic queries
"""

import os
import sys
import argparse
import torch
import chromadb
import logging
import json
import csv
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from tqdm import tqdm
import time
from collections import defaultdict

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

# Configuration
CHROMA_PATH = str(project_root / "data" / "processed_datasets" / "chroma_db")
MODEL_NAME = "openai/clip-vit-base-patch32"
DEFAULT_COLLECTION = "prod_artwork_images"
DEFAULT_TOP_K = 100

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clip_evaluation.log')
    ]
)
logger = logging.getLogger(__name__)


class CLIPEvaluator:
    def __init__(self, chroma_path=CHROMA_PATH, collection_name=DEFAULT_COLLECTION, use_gpu=True):
        """Initialize the CLIP model for text embedding using Hugging Face Transformers."""
        from transformers import CLIPProcessor, CLIPModel
        
        self.chroma_path = chroma_path
        self.collection_name = collection_name
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {self.device}")

        # Load model with half precision for GPU if available
        dtype = torch.float16 if self.device == "cuda" else torch.float32
        logger.info(f"Loading CLIP model: {MODEL_NAME}")
        self.model = CLIPModel.from_pretrained(MODEL_NAME, torch_dtype=dtype).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        
        # Set to eval mode
        self.model.eval()
        
        # Initialize ChromaDB client
        try:
            self.chroma_client = chromadb.PersistentClient(path=chroma_path)
            logger.info(f"Connected to ChromaDB at {chroma_path}")
            
            # Get the collection
            self.collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' contains {self.collection.count()} items")
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB or getting collection: {e}")
            raise
    
    def get_text_embedding(self, query: str) -> List[float]:
        """Get embedding for a text query."""
        try:
            with torch.no_grad():
                inputs = self.processor(
                    text=[query],
                    return_tensors="pt",
                    padding=True
                ).to(self.device)
                
                text_features = self.model.get_text_features(**inputs)
                text_features = text_features / text_features.norm(dim=1, keepdim=True)
                
                return text_features.cpu().numpy()[0].tolist()
        except Exception as e:
            logger.exception(f"Error generating text embedding for query '{query}': {e}")
            raise
    
    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[str]:
        """
        Search for artworks similar to the query text.
        Returns a list of artwork IDs.
        """
        # Get text embedding
        text_embedding = self.get_text_embedding(query)
        
        # Query the collection
        try:
            # Use valid include parameters - "ids" is not valid, but we can get IDs from the results
            results = self.collection.query(
                query_embeddings=[text_embedding],
                n_results=top_k,
                include=["metadatas"]  # We'll extract IDs from metadata
            )
            
            # Extract IDs from the results
            if results["ids"] and len(results["ids"][0]) > 0:
                return results["ids"][0]  # ChromaDB still returns ids even if not explicitly included
            else:
                return []
                
        except Exception as e:
            logger.exception(f"Error querying collection: {e}")
            return []
    
    def jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0  # Both empty sets are considered identical
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def evaluate_retrieval_consistency(self, query_sets: Dict[str, List[str]], 
                                      top_k: int = DEFAULT_TOP_K,
                                      output_file: Optional[str] = None) -> Dict[str, float]:
        """
        Evaluate retrieval consistency using Jaccard similarity.
        
        Args:
            query_sets: Dictionary mapping set names to lists of similar queries
            top_k: Number of results to retrieve for each query
            output_file: Optional CSV file to write results to
            
        Returns:
            Dictionary mapping set names to average Jaccard similarity
        """
        logger.info(f"Evaluating retrieval consistency with {len(query_sets)} query sets")
        results = {}
        
        for set_name, queries in tqdm(query_sets.items(), desc="Processing query sets"):
            if len(queries) < 2:
                logger.warning(f"Skipping set '{set_name}' as it has fewer than 2 queries")
                continue
            
            # Get results for each query
            query_results = {}
            for query in queries:
                query_results[query] = set(self.search(query, top_k=top_k))
            
            # Calculate pairwise Jaccard similarities
            similarities = []
            for i, query1 in enumerate(queries):
                for j, query2 in enumerate(queries):
                    if i < j:  # Only calculate each pair once
                        sim = self.jaccard_similarity(
                            query_results[query1], 
                            query_results[query2]
                        )
                        similarities.append(sim)
            
            # Calculate average similarity
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            results[set_name] = avg_similarity
            
            logger.info(f"Set '{set_name}': Average Jaccard similarity = {avg_similarity:.4f}")
        
        # Write results to CSV if requested
        if output_file:
            with open(output_file, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Query Set', 'Average Jaccard Similarity'])
                for set_name, avg_similarity in results.items():
                    writer.writerow([set_name, f"{avg_similarity:.4f}"])
            logger.info(f"Retrieval consistency results written to {output_file}")
        
        return results
    
    def evaluate_synthetic_queries(self, artwork_queries: Dict[str, List[str]], 
                                  top_k: int = DEFAULT_TOP_K,
                                  output_file: Optional[str] = None) -> Dict[str, Dict]:
        """
        Evaluate synthetic queries by checking if the target artwork is retrieved.
        
        Args:
            artwork_queries: Dictionary mapping artwork IDs to lists of synthetic queries
            top_k: Number of results to retrieve for each query
            output_file: Optional JSON file to write results to
            
        Returns:
            Dictionary with evaluation metrics
        """
        logger.info(f"Evaluating synthetic queries for {len(artwork_queries)} artworks")
        
        # Track metrics
        ranks = []
        success_counts = defaultdict(int)
        total_queries = 0
        
        # Process each artwork and its queries
        artwork_results = {}
        
        for artwork_id, queries in tqdm(artwork_queries.items(), desc="Processing artworks"):
            artwork_ranks = []
            
            for query in queries:
                total_queries += 1
                results = self.search(query, top_k=top_k)
                
                # Check if artwork is in results
                if artwork_id in results:
                    rank = results.index(artwork_id) + 1  # Convert to 1-indexed rank
                    artwork_ranks.append(rank)
                    ranks.append(rank)
                    
                    # Count successes at different K values
                    for k in range(1, top_k + 1):
                        if rank <= k:
                            success_counts[k] += 1
            
            # Store results for this artwork
            if artwork_ranks:
                mrr = sum(1.0 / rank for rank in artwork_ranks) / len(artwork_ranks)
                success_rate = len(artwork_ranks) / len(queries)
                
                artwork_results[artwork_id] = {
                    "mrr": mrr,
                    "success_rate": success_rate,
                    "avg_rank": sum(artwork_ranks) / len(artwork_ranks) if artwork_ranks else None,
                    "ranks": artwork_ranks,
                    "num_queries": len(queries)
                }
            else:
                artwork_results[artwork_id] = {
                    "mrr": 0.0,
                    "success_rate": 0.0,
                    "avg_rank": None,
                    "ranks": [],
                    "num_queries": len(queries)
                }
        
        # Calculate overall metrics
        overall_mrr = sum(1.0 / rank for rank in ranks) / total_queries if ranks else 0.0
        success_at_k = {k: count / total_queries for k, count in success_counts.items()}
        
        # Prepare final results
        results = {
            "overall": {
                "mrr": overall_mrr,
                "success_at_k": success_at_k,
                "total_queries": total_queries,
                "total_artworks": len(artwork_queries)
            },
            "per_artwork": artwork_results
        }
        
        # Print summary
        logger.info(f"Overall MRR: {overall_mrr:.4f}")
        for k in sorted(success_at_k.keys()):
            logger.info(f"Success@{k}: {success_at_k[k]:.4f}")
        
        # Write results to JSON if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Synthetic query results written to {output_file}")
        
        return results


# Example query sets for retrieval consistency - appropriate for Cleveland Museum of Art
# TODO: We need to update these to be more specific... there must be sooo many portrait paintins for example
RETRIEVAL_CONSISTENCY_QUERY_SETS = {
    "sunset": [
        "painting with sunset", 
        "sunset scene", 
        "artwork showing sunset",
        "landscape with setting sun"
    ],
    "portrait": [
        "portrait painting", 
        "face portrait", 
        "portrait of a person",
        "formal portrait artwork"
    ],
    "landscape": [
        "landscape painting", 
        "natural landscape", 
        "countryside scene",
        "scenic view artwork"
    ],
    "still_life": [
        "still life painting", 
        "fruit bowl artwork", 
        "floral arrangement painting",
        "table with objects"
    ],
    "religious": [
        "religious artwork", 
        "biblical scene", 
        "christian iconography",
        "religious figure painting"
    ],
    "medieval": [
        "medieval artwork", 
        "medieval manuscript", 
        "gothic art",
        "early christian art"
    ],
    "blue_vase": [
        "blue porcelain vase", 
        "blue glazed container", 
        "blue ceramic vase",
        "blue pottery vessel"
    ],
    "van gogh": [
        "van gogh painting",
        "painting in the style of van gogh",
        "artwork by van gogh",
        "van gogh style artwork",
        "a painting that looks like it was by van gogh"
    ],
    "monet": [
        "monet painting",
        "painting in the style of monet",
        "artwork by monet",
        "monet style artwork",
        "a painting that looks like it was by monet"
        "monet style impressionist painting"
    ]
}

# Example synthetic queries for Cleveland Museum of Art collection
# These should be replaced with actual artwork IDs from your collection
# TODO: We need to add actual IDs here! 
SYNTHETIC_QUERIES = {
    # Example format - replace with actual IDs from your collection
    "CMA_123": [
        "medieval armor",
        "knight's suit of armor",
        "medieval battle equipment",
        "european plate armor"
    ],
    "CMA_456": [
        "impressionist landscape",
        "french countryside painting",
        "pastoral scene with trees",
        "rural landscape with river"
    ],
    "CMA_789": [
        "chinese porcelain vase",
        "blue and white ceramic vessel",
        "ming dynasty pottery",
        "asian decorative vessel"
    ],
    "CMA_101": [
        "religious triptych",
        "altar panel painting",
        "christian devotional artwork",
        "religious scene with saints"
    ],
    "CMA_202": [
        "egyptian sarcophagus",
        "ancient egyptian burial container",
        "pharaonic funeral artifact",
        "decorated mummy case"
    ]
}


def load_synthetic_queries(file_path: str) -> Dict[str, List[str]]:
    """Load synthetic queries from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading synthetic queries from {file_path}: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Evaluate artwork embeddings")
    parser.add_argument("evaluation_type", choices=["consistency", "synthetic", "both"],
                        help="Type of evaluation to perform")
    parser.add_argument("--chroma_path", type=str, default=CHROMA_PATH,
                        help=f"Path to ChromaDB embeddings (default: {CHROMA_PATH})")
    parser.add_argument("--collection_name", type=str, default=DEFAULT_COLLECTION,
                        help=f"Name of the ChromaDB collection to search (default: {DEFAULT_COLLECTION})")
    parser.add_argument("--top_k", type=int, default=DEFAULT_TOP_K,
                        help=f"Number of results to retrieve (default: {DEFAULT_TOP_K})")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage even if GPU is available")
    parser.add_argument("--output_dir", type=str, default="evaluation_results",
                        help="Directory to save evaluation results")
    parser.add_argument("--synthetic_queries_file", type=str, default=None,
                        help="JSON file containing synthetic queries (artwork_id -> [queries])")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Initialize evaluator
    evaluator = CLIPEvaluator(
        chroma_path=args.chroma_path,
        collection_name=args.collection_name,
        use_gpu=not args.cpu
    )
    
    # Run evaluations
    if args.evaluation_type in ["consistency", "both"]:
        consistency_output = os.path.join(args.output_dir, "retrieval_consistency.csv")
        evaluator.evaluate_retrieval_consistency(
            RETRIEVAL_CONSISTENCY_QUERY_SETS,
            top_k=args.top_k,
            output_file=consistency_output
        )
    
    if args.evaluation_type in ["synthetic", "both"]:
        # Load synthetic queries from file if provided
        if args.synthetic_queries_file:
            synthetic_queries = load_synthetic_queries(args.synthetic_queries_file)
            if not synthetic_queries:
                logger.warning("No synthetic queries loaded. Using default examples.")
                synthetic_queries = SYNTHETIC_QUERIES
        else:
            logger.info("Using default example synthetic queries")
            synthetic_queries = SYNTHETIC_QUERIES
        
        synthetic_output = os.path.join(args.output_dir, "synthetic_queries.json")
        evaluator.evaluate_synthetic_queries(
            synthetic_queries,
            top_k=args.top_k,
            output_file=synthetic_output
        )


if __name__ == "__main__":
    main() 