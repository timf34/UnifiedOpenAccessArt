#!/usr/bin/env python3
"""
Script to embed sample paintings from a local folder and create a searchable vector database.
"""

import os
import argparse
import json
from pathlib import Path
from tqdm import tqdm
import torch
import numpy as np
from PIL import Image
import chromadb
from transformers import CLIPProcessor, CLIPModel

# Configuration
SAMPLE_PAINTINGS_DIR = "../data/sample_paintings"
OUTPUT_CHROMA_DIR = "../data/sample_paintings_db"
MODEL_NAME = "openai/clip-vit-base-patch32"  # Using a larger model for better quality


class SamplePaintingEmbedder:
    def __init__(self, use_gpu=True):
        """Initialize the embedder with CLIP model."""
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # Load model with half precision for GPU
        print(f"Loading CLIP model: {MODEL_NAME}")
        self.model = CLIPModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        # Set to eval mode
        self.model.eval()
        
        # Initialize ChromaDB
        self.chroma_client = None
        self.image_collection = None
        
    def init_chroma_db(self, chroma_path, reset=False):
        """Initialize ChromaDB collection."""
        self.chroma_client = chromadb.PersistentClient(path=chroma_path)
        
        # Reset collection if requested
        if reset and "sample_paintings" in self.chroma_client.list_collections():
            self.chroma_client.delete_collection("sample_paintings")
            print("Existing collection deleted.")
        
        # Create collection
        self.image_collection = self.chroma_client.get_or_create_collection(
            name="sample_paintings",
            metadata={"hnsw:space": "cosine"}
        )
        
    def load_image(self, image_path):
        """Load an image from a local file path."""
        try:
            img = Image.open(image_path)
            return img.convert('RGB')
        except Exception as e:
            print(f"Error loading image {image_path}: {e}")
            return None
    
    def generate_text_embedding(self, text):
        """Generate embedding for text using CLIP."""
        with torch.no_grad():
            inputs = self.processor(
                text=text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            ).to(self.device)
            
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)
            
            return text_features.cpu().numpy()[0].tolist()
    
    def generate_image_embedding(self, image):
        """Generate embedding for an image using CLIP."""
        with torch.no_grad():
            inputs = self.processor(
                images=image,
                return_tensors="pt"
            ).to(self.device)
            
            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)
            
            return image_features.cpu().numpy()[0].tolist()
    
    def embed_sample_paintings(self, sample_dir):
        """Embed all sample paintings in the given directory."""
        # Get list of image files
        image_files = []
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.webp"]:
            image_files.extend(list(Path(sample_dir).glob(ext)))
        
        if not image_files:
            print(f"No image files found in {sample_dir}")
            return []
        
        print(f"Found {len(image_files)} image files")
        
        # Process each image
        sample_data = []
        ids = []
        embeddings = []
        descriptions = []
        metadatas = []
        
        for img_path in tqdm(image_files, desc="Embedding sample paintings"):
            # Load image
            image = self.load_image(img_path)
            if image is None:
                continue
            
            # Generate embedding
            embedding = self.generate_image_embedding(image)
            
            # Create metadata
            file_name = img_path.name
            title = file_name.replace("_", " ").replace("-", " ").split(".")[0].title()
            description = f"Sample painting: {title}"
            
            # Create record
            sample_info = {
                "id": str(img_path),
                "file_name": file_name,
                "title": title,
                "path": str(img_path),
            }
            sample_data.append(sample_info)
            
            # Prepare for ChromaDB
            ids.append(sample_info["id"])
            embeddings.append(embedding)
            descriptions.append(description)
            metadatas.append({
                "title": title,
                "file_name": file_name,
                "path": str(img_path),
            })
        
        # Save to ChromaDB
        if embeddings:
            self.image_collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=descriptions,
                metadatas=metadatas
            )
            
        # Save sample data as JSON for reference
        with open(Path(OUTPUT_CHROMA_DIR) / "sample_paintings_info.json", "w") as f:
            json.dump(sample_data, f, indent=2)
            
        return sample_data


def main():
    parser = argparse.ArgumentParser(description="Embed sample paintings")
    parser.add_argument("--input_dir", type=str, default=SAMPLE_PAINTINGS_DIR,
                        help=f"Directory containing sample paintings (default: {SAMPLE_PAINTINGS_DIR})")
    parser.add_argument("--output_dir", type=str, default=OUTPUT_CHROMA_DIR,
                        help=f"Directory to store ChromaDB embeddings (default: {OUTPUT_CHROMA_DIR})")
    parser.add_argument("--reset", action="store_true",
                        help="Reset existing collection in ChromaDB")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage even if GPU is available")
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    # Initialize embedder
    embedder = SamplePaintingEmbedder(use_gpu=not args.cpu)
    embedder.init_chroma_db(args.output_dir, reset=args.reset)
    
    # Embed sample paintings
    sample_data = embedder.embed_sample_paintings(args.input_dir)
    
    print(f"\nEmbedded {len(sample_data)} sample paintings")
    print(f"Embeddings stored in {args.output_dir}")
    
    # Print sample data
    for sample in sample_data:
        print(f"\nTitle: {sample['title']}")
        print(f"File: {sample['file_name']}")
        print(f"Path: {sample['path']}")
    

if __name__ == "__main__":
    main()