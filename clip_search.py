#!/usr/bin/env python3
"""
Direct CLIP Search for Sample Paintings

This script uses the CLIP model directly without ChromaDB to search through sample paintings.
"""

import os
import sys
import glob
import argparse
import torch
from PIL import Image
import matplotlib.pyplot as plt
from transformers import CLIPProcessor, CLIPModel

# Configuration
SAMPLE_PAINTINGS_DIR = "data/sample_paintings"
MODEL_NAME = "openai/clip-vit-base-patch32"  # Using the larger model for better quality


class DirectCLIPSearch:
    def __init__(self, images_dir=SAMPLE_PAINTINGS_DIR, use_gpu=True):
        """Initialize CLIP model and load images."""
        self.images_dir = images_dir
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")
        
        # Load CLIP model
        print(f"Loading CLIP model: {MODEL_NAME}")
        self.model = CLIPModel.from_pretrained(MODEL_NAME).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)
        
        # Set to eval mode
        self.model.eval()
        
        # Load and process images
        self.images = []
        self.image_paths = []
        self.load_images()
    
    def load_images(self):
        """Load all images from the directory."""
        print(f"Loading images from {self.images_dir}")
        
        # Find all image files
        image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
        image_files = []
        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(self.images_dir, ext)))
        
        if not image_files:
            print(f"No image files found in {self.images_dir}")
            sys.exit(1)
        
        # Load each image
        for img_path in image_files:
            try:
                img = Image.open(img_path).convert('RGB')
                self.images.append(img)
                self.image_paths.append(img_path)
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
        
        print(f"Loaded {len(self.images)} images")
    
    def search(self, query, n_results=5):
        """Search for images similar to the query text."""
        if len(self.images) == 0:
            print("No images loaded. Cannot search.")
            return []
        
        with torch.no_grad():
            # Process query and images
            inputs = self.processor(
                text=[query], 
                images=self.images,
                return_tensors="pt",
                padding=True
            )
            
            # Move inputs to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get image and text features
            outputs = self.model(**inputs)
            
            # Get logits and convert to similarity scores
            logits = outputs.logits_per_image.squeeze()  # [n_images]
            similarities = logits.softmax(dim=0)  # Normalize scores
            
            # Get indices of top matches
            if n_results > len(self.images):
                n_results = len(self.images)
                
            top_indices = similarities.argsort(descending=True)[:n_results].cpu().numpy()
            
            # Prepare results
            results = []
            for idx in top_indices:
                file_path = self.image_paths[idx]
                file_name = os.path.basename(file_path)
                title = os.path.splitext(file_name)[0].replace("_", " ").replace("-", " ").title()
                
                results.append({
                    "title": title,
                    "file_name": file_name,
                    "path": file_path,
                    "score": similarities[idx].item()
                })
            
            return results
    
    def display_results(self, query, results, show_images=True):
        """Display search results."""
        if not results:
            print("No results found.")
            return
        
        print(f"\nResults for query: '{query}'")
        print("-" * 80)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title']}")
            print(f"   File: {result['file_name']}")
            print(f"   Score: {result['score']:.4f}")
            print("-" * 80)
        
        if show_images:
            self.display_images(results)
    
    def display_images(self, results):
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
        
        # Add each image to the grid
        for i, result in enumerate(results):
            if i >= rows * cols:
                break
                
            # Load image
            try:
                img = Image.open(result['path'])
                
                # Create subplot
                plt.subplot(rows, cols, i + 1)
                plt.imshow(img)
                plt.title(f"{i+1}. {result['title']}\nScore: {result['score']:.4f}")
                plt.axis('off')
            except Exception as e:
                print(f"Error displaying image {result['path']}: {e}")
        
        plt.tight_layout()
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Direct CLIP search for sample paintings")
    parser.add_argument("--query", type=str, required=True, help="Search query")
    parser.add_argument("--results", type=int, default=5, help="Number of results to show")
    parser.add_argument("--images_dir", type=str, default=SAMPLE_PAINTINGS_DIR,
                        help=f"Directory containing images (default: {SAMPLE_PAINTINGS_DIR})")
    parser.add_argument("--no_display", action="store_true", help="Don't display images")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage")
    
    args = parser.parse_args()
    
    # Create search object
    search = DirectCLIPSearch(
        images_dir=args.images_dir,
        use_gpu=not args.cpu
    )
    
    # Perform search
    results = search.search(args.query, n_results=args.results)
    
    # Display results
    search.display_results(args.query, results, show_images=not args.no_display)


if __name__ == "__main__":
    main()