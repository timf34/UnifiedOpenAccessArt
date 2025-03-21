#!/usr/bin/env python3
"""
Search Artwork Embeddings

This script allows searching for artworks using natural language queries
against CLIP embeddings stored in ChromaDB.
"""

import os
import sys
import argparse
import torch
import chromadb
import logging
from pathlib import Path
from typing import List, Dict, Optional
import matplotlib.pyplot as plt
from PIL import Image
import requests
from io import BytesIO
import time
import readline  # For better command line input experience

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

# Configuration
CHROMA_PATH = str(project_root / "data" / "processed_datasets" / "chroma_db")
MODEL_NAME = "openai/clip-vit-base-patch32"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('clip_search.log')
    ]
)
logger = logging.getLogger(__name__)


class CLIPSearcher:
    def __init__(self, chroma_path=CHROMA_PATH, use_gpu=True):
        """Initialize the CLIP model for text embedding using Hugging Face Transformers."""
        from transformers import CLIPProcessor, CLIPModel
        
        self.chroma_path = chroma_path
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
            collections = self.chroma_client.list_collections()
            logger.info(f"Available collections: {collections}")
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB: {e}")
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
    
    def search(self, query: str, collection_name: str, top_k: int = 5) -> List[Dict]:
        """Search for artworks similar to the query text."""
        logger.info(f"Searching for: '{query}' in collection '{collection_name}'")
        start_time = time.time()
        
        # Get text embedding
        text_embedding = self.get_text_embedding(query)
        logger.info(f"Generated text embedding in {time.time() - start_time:.2f}s")
        
        # Get collection
        try:
            collection = self.chroma_client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' contains {collection.count()} items")
        except Exception as e:
            logger.error(f"Error getting collection '{collection_name}': {e}")
            logger.info(f"Available collections: {self.chroma_client.list_collections()}")
            return []
        
        # Query the collection
        try:
            query_start = time.time()
            results = collection.query(
                query_embeddings=[text_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            logger.info(f"Query completed in {time.time() - query_start:.2f}s")
        except Exception as e:
            logger.exception(f"Error querying collection: {e}")
            return []
        
        # Process results
        processed_results = []
        
        if not results["ids"] or len(results["ids"][0]) == 0:
            logger.warning("No results found")
            return []
            
        for i in range(min(top_k, len(results["ids"][0]))):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results else None
            similarity = 1 - distance if distance is not None else None
            
            processed_results.append({
                "id": results["ids"][0][i],
                "title": metadata.get("title", "Unknown Title"),
                "artist": metadata.get("artist", "Unknown Artist"),
                "museum": metadata.get("museum", "Unknown Museum"),
                "type": metadata.get("type", "Unknown Type"),
                "date_text": metadata.get("date_text", "Unknown Date"),
                "artist_birth": metadata.get("artist_birth", ""),
                "artist_death": metadata.get("artist_death", ""),
                "url": metadata.get("url", ""),
                "image_url": metadata.get("image_url", ""),
                "distance": distance,
                "similarity": similarity,
                "description": results["documents"][0][i] if "documents" in results else ""
            })
        
        logger.info(f"Found {len(processed_results)} results in {time.time() - start_time:.2f}s")
        return processed_results
    
    def display_results(self, query: str, results: List[Dict], show_images: bool = True):
        """Display search results."""
        if not results:
            print("No results found.")
            return
        
        print(f"\nSearch Results for: '{query}'")
        print("=" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   Artist: {result['artist']}")
            
            # Show artist dates if available
            artist_dates = []
            if result['artist_birth']:
                artist_dates.append(f"b. {result['artist_birth']}")
            if result['artist_death']:
                artist_dates.append(f"d. {result['artist_death']}")
            if artist_dates:
                print(f"   Artist Dates: {', '.join(artist_dates)}")
                
            print(f"   Museum: {result['museum']}")
            print(f"   Type: {result['type']}")
            print(f"   Date: {result['date_text']}")
            
            if result['similarity'] is not None:
                print(f"   Similarity: {result['similarity']:.4f}")
                
            if result['url']:
                print(f"   URL: {result['url']}")
                
            if result['image_url']:
                print(f"   Image URL: {result['image_url']}")
                
            print("-" * 80)
        
        if show_images:
            self.display_images(query, results)
    
    def display_images(self, query: str, results: List[Dict]):
        """Display images in a grid using matplotlib."""
        n = len(results)
        
        # Calculate grid size
        if n <= 3:
            rows, cols = 1, n
        elif n <= 6:
            rows, cols = 2, 3
        else:
            rows, cols = 3, 3
        
        # Create figure
        plt.figure(figsize=(cols * 4, rows * 4))
        plt.suptitle(f"Results for: '{query}'", fontsize=16)
        
        # Add each image to the grid
        for i, result in enumerate(results):
            if i >= rows * cols:
                break
            
            # Skip if no image URL
            if not result['image_url']:
                continue
            
            # Load image
            try:
                response = requests.get(result['image_url'], timeout=10)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                
                # Create subplot
                plt.subplot(rows, cols, i + 1)
                plt.imshow(img)
                
                # Create title with similarity score
                title = f"{i+1}. {result['title']}"
                if result['similarity'] is not None:
                    title += f"\nSimilarity: {result['similarity']:.4f}"
                plt.title(title, fontsize=10)
                
                # Add artist name as subtitle
                if result['artist']:
                    plt.figtext(plt.gca().get_position().x0, 
                               plt.gca().get_position().y0 - 0.02, 
                               f"Artist: {result['artist']}", 
                               fontsize=8)
                
                plt.axis('off')
            except Exception as e:
                logger.warning(f"Error displaying image {result['image_url']}: {e}")
                # Create empty subplot with error message
                plt.subplot(rows, cols, i + 1)
                plt.text(0.5, 0.5, f"Error loading image:\n{str(e)}", 
                         horizontalalignment='center', verticalalignment='center')
                plt.axis('off')
        
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)  # Make room for the suptitle
        plt.show(block=False)  # Non-blocking to allow continued interaction


def interactive_cli(searcher, collection_name, top_k, show_images, save_results_path=None):
    """Run an interactive CLI for searching artworks."""
    print("\n" + "=" * 80)
    print("Interactive Artwork Search CLI")
    print("=" * 80)
    print("Type your search query and press Enter.")
    print("Type 'help' for available commands.")
    print("Type 'exit' or 'quit' to exit.")
    print("=" * 80)
    
    history = []
    
    while True:
        try:
            # Get user input
            user_input = input("\nSearch query> ").strip()
            
            # Process commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Exiting...")
                break
                
            elif user_input.lower() in ['help', '?', 'h']:
                print("\nAvailable commands:")
                print("  help, ?, h       - Show this help message")
                print("  exit, quit, q    - Exit the program")
                print("  clear, cls       - Clear the screen")
                print(f"  top N            - Change number of results (current: {top_k})")
                print("  history          - Show search history")
                print("  save FILENAME    - Save last results to JSON file")
                print("  collections      - List available collections")
                print(f"  collection NAME  - Change collection (current: {collection_name})")
                print("  images on/off    - Turn image display on/off")
                print("  Any other input will be treated as a search query")
                
            elif user_input.lower() in ['clear', 'cls']:
                os.system('cls' if os.name == 'nt' else 'clear')
                
            elif user_input.lower().startswith('top '):
                try:
                    new_top_k = int(user_input.split()[1])
                    if new_top_k > 0:
                        top_k = new_top_k
                        print(f"Number of results changed to {top_k}")
                    else:
                        print("Number of results must be positive")
                except (IndexError, ValueError):
                    print("Invalid format. Use 'top N' where N is a positive integer.")
                    
            elif user_input.lower() == 'history':
                if not history:
                    print("No search history yet.")
                else:
                    print("\nSearch history:")
                    for i, query in enumerate(history, 1):
                        print(f"{i}. {query}")
                        
            elif user_input.lower().startswith('save '):
                if not history:
                    print("No search results to save.")
                    continue
                    
                try:
                    filename = user_input[5:].strip()
                    if not filename:
                        if save_results_path:
                            filename = save_results_path
                        else:
                            print("Please specify a filename.")
                            continue
                            
                    # Get last results and save them
                    if 'last_results' in locals():
                        import json
                        with open(filename, 'w') as f:
                            json.dump(last_results, f, indent=2)
                        print(f"Results saved to {filename}")
                    else:
                        print("No results available to save.")
                except Exception as e:
                    print(f"Error saving results: {e}")
                    
            elif user_input.lower() == 'collections':
                try:
                    collections = searcher.chroma_client.list_collections()
                    print("\nAvailable collections:")
                    for i, coll in enumerate(collections, 1):
                        print(f"{i}. {coll.name}")
                except Exception as e:
                    print(f"Error listing collections: {e}")
                    
            elif user_input.lower().startswith('collection '):
                try:
                    new_collection = user_input[11:].strip()
                    # Verify collection exists
                    collections = [c.name for c in searcher.chroma_client.list_collections()]
                    if new_collection in collections:
                        collection_name = new_collection
                        print(f"Collection changed to '{collection_name}'")
                    else:
                        print(f"Collection '{new_collection}' not found. Available collections:")
                        for c in collections:
                            print(f"  - {c}")
                except Exception as e:
                    print(f"Error changing collection: {e}")
                    
            elif user_input.lower() in ['images on', 'images off']:
                show_images = user_input.lower() == 'images on'
                print(f"Image display turned {'on' if show_images else 'off'}")
                
            elif user_input.strip():
                # Treat as search query
                try:
                    # Close any existing plot windows
                    plt.close('all')
                    
                    # Perform search
                    results = searcher.search(
                        query=user_input,
                        collection_name=collection_name,
                        top_k=top_k
                    )
                    
                    # Store results for potential saving
                    last_results = results
                    
                    # Display results
                    searcher.display_results(user_input, results, show_images=show_images)
                    
                    # Add to history
                    history.append(user_input)
                    
                except Exception as e:
                    logger.exception(f"Error during search: {e}")
                    print(f"Error: {str(e)}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except EOFError:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Search for artworks using natural language")
    parser.add_argument("--query", type=str, 
                        help="Natural language query to search for artworks (optional in interactive mode)")
    parser.add_argument("--interactive", "-i", action="store_true",
                        help="Run in interactive mode")
    parser.add_argument("--chroma_path", type=str, default=CHROMA_PATH,
                        help=f"Path to ChromaDB embeddings (default: {CHROMA_PATH})")
    parser.add_argument("--collection_name", type=str, default="artwork_images",
                        help="Name of the ChromaDB collection to search")
    parser.add_argument("--top_k", type=int, default=5,
                        help="Number of results to return")
    parser.add_argument("--no_images", action="store_true",
                        help="Don't display images")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage even if GPU is available")
    parser.add_argument("--save_results", type=str, default=None,
                        help="Save results to the specified JSON file")
    
    args = parser.parse_args()
    
    # If no query is provided, default to interactive mode
    if not args.query and not args.interactive:
        args.interactive = True
        print("No query provided, defaulting to interactive mode.")
    
    try:
        # Initialize searcher
        searcher = CLIPSearcher(
            chroma_path=args.chroma_path,
            use_gpu=not args.cpu
        )
        
        if args.interactive:
            # Run interactive CLI
            interactive_cli(
                searcher=searcher,
                collection_name=args.collection_name,
                top_k=args.top_k,
                show_images=not args.no_images,
                save_results_path=args.save_results
            )
        else:
            # Single search mode
            results = searcher.search(
                query=args.query,
                collection_name=args.collection_name,
                top_k=args.top_k
            )
            
            # Display results
            searcher.display_results(args.query, results, show_images=not args.no_images)
            
            # Save results if requested
            if args.save_results and results:
                import json
                with open(args.save_results, 'w') as f:
                    json.dump(results, f, indent=2)
                logger.info(f"Results saved to {args.save_results}")
            
    except Exception as e:
        logger.exception(f"Error during search: {e}")
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 