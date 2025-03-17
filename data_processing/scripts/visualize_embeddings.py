#!/usr/bin/env python3
"""
Visualize CLIP Embeddings for Museum Artworks

This script connects to our ChromaDB collection ("prod_artwork_images"),
retrieves the image embeddings along with metadata,
reduces the dimensionality of the embeddings (using UMAP),
and produces a 2D scatter plot using matplotlib.
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import umap  # Install via: pip install umap-learn
import chromadb
from pathlib import Path

# Add project root to sys.path if needed
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.append(str(project_root))

# Configuration
CHROMA_PATH = str(project_root / "data" / "processed_datasets" / "chroma_db")
print(f"CHROMA_PATH: {CHROMA_PATH}")
COLLECTION_NAME = "prod_artwork_images"  # Our production collection

def load_embeddings(chroma_path, collection_name):
    """
    Connects to ChromaDB, retrieves all items from the specified collection,
    and returns a tuple of (embeddings, metadata).
    """
    # Initialize the ChromaDB client
    client = chromadb.PersistentClient(path=chroma_path)
    
    try:
        collection = client.get_collection(collection_name)
    except Exception as e:
        print(f"Error getting collection '{collection_name}': {e}")
        # List available collections to help troubleshoot
        print("Available collections:", [c.name for c in client.list_collections()])
        sys.exit(1)
    
    # Retrieve all items from the collection.
    # (Assuming that calling .get() without specifying ids returns all items.
    #  If not, you may need to implement paging or use a stored file.)
    try:
        # Try using collection.get() to fetch all items with embeddings and metadata
        data = collection.get(include=["embeddings", "metadatas"])
    except Exception as e:
        print(f"Error retrieving items from collection: {e}")
        sys.exit(1)
    
    embeddings = data.get("embeddings", [])
    metadatas = data.get("metadatas", [])
    
    # For safety, convert embeddings to a NumPy array
    embeddings_array = np.array(embeddings)
    
    return embeddings_array, metadatas

def reduce_dimensions(embeddings, n_components=2, random_state=42):
    """
    Use UMAP to reduce the dimensionality of the embeddings to n_components.
    """
    reducer = umap.UMAP(n_components=n_components, random_state=random_state)
    embedding_2d = reducer.fit_transform(embeddings)
    return embedding_2d

def plot_embeddings(embedding_2d, metadatas, title_field="title", color_field=None, save_path=None):
    """
    Create a scatter plot of the 2D embeddings.
    
    - title_field: key in metadata to use for annotating points.
    - color_field: key in metadata to use for coloring points (optional).
    """
    plt.figure(figsize=(12, 8))
    x = embedding_2d[:, 0]
    y = embedding_2d[:, 1]
    
    if color_field:
        # If a color field is provided, convert to categorical numerical labels
        labels = [md.get(color_field, "Unknown") for md in metadatas]
        unique_labels = list(set(labels))
        color_map = {label: idx for idx, label in enumerate(unique_labels)}
        colors = [color_map[label] for label in labels]
        scatter = plt.scatter(x, y, c=colors, cmap='tab10', alpha=0.7)
        plt.colorbar(scatter, ticks=range(len(unique_labels)), label=color_field)
        # Create a legend manually
        for label, idx in color_map.items():
            plt.scatter([], [], c=scatter.cmap(scatter.norm(idx)), label=label)
        plt.legend(title=color_field)
    else:
        plt.scatter(x, y, alpha=0.7)
    
    # Optionally, annotate a few points (if not too many)
    for i, md in enumerate(metadatas):
        text = md.get(title_field, "")
        # Annotate only if text is short
        if len(text) < 20:
            plt.annotate(text, (x[i], y[i]), fontsize=8, alpha=0.8)
    
    plt.title("2D Visualization of Artwork Embeddings")
    plt.xlabel("UMAP 1")
    plt.ylabel("UMAP 2")
    plt.grid(True)
    
    if save_path:
        plt.savefig(save_path, dpi=300)
        print(f"Plot saved to {save_path}")
    
    plt.show()

def main():
    # Load embeddings and metadata from ChromaDB
    print("Loading embeddings from ChromaDB...")
    embeddings, metadatas = load_embeddings(CHROMA_PATH, COLLECTION_NAME)
    print(f"Retrieved {len(embeddings)} embeddings.")
    
    if embeddings.size == 0:
        print("No embeddings found. Exiting.")
        return
    
    # Optionally, take a sample if too many points (e.g., sample 1000 points)
    sample_size = 10000
    if len(embeddings) > sample_size:
        indices = np.random.choice(len(embeddings), size=sample_size, replace=False)
        embeddings = embeddings[indices]
        metadatas = [metadatas[i] for i in indices]
        print(f"Using a sample of {sample_size} embeddings for visualization.")
    
    # Reduce dimensions to 2D
    print("Reducing dimensionality with UMAP...")
    embedding_2d = reduce_dimensions(embeddings, n_components=2)
    
    # Plot the results
    print("Plotting embeddings...")
    # For example, annotate by artwork title and color by museum (if available)
    plot_embeddings(embedding_2d, metadatas, title_field="title", color_field="museum", save_path="embeddings_plot.png")

if __name__ == "__main__":
    main()
