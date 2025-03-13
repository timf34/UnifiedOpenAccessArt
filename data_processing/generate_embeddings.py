# generate_embeddings.py
import os
import chromadb
import sqlite3
import requests
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import torch
from transformers import CLIPProcessor, CLIPModel
import argparse

# Configuration
DB_PATH = "../data/processed_datasets/unified_art.db"
CHROMA_PATH = "../data/processed_datasets/chroma_db"
BATCH_SIZE = 8  # Adjust based on GPU memory
MODEL_NAME = "openai/clip-vit-base-patch32"


class CLIPEmbedder:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        # Load model with half precision for GPU
        self.model = CLIPModel.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
        ).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(MODEL_NAME)

        # Set to eval mode
        self.model.eval()

    def get_embeddings(self, texts: list[str], images: list[Image.Image | None]) -> tuple[
        list[list[float]], list[list[float] | None]]:
        """Get both text and image embeddings for a batch."""
        text_embeddings = self._get_text_embeddings(texts)
        image_embeddings = self._get_image_embeddings(images)
        return text_embeddings, image_embeddings

    def _get_text_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get text embeddings."""
        with torch.no_grad():
            inputs = self.processor(
                text=texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            ).to(self.device)

            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(dim=1, keepdim=True)

            return text_features.cpu().numpy().tolist()

    def _get_image_embeddings(self, images: list[Image.Image | None]) -> list[list[float] | None]:
        """Get image embeddings, handling None values."""
        with torch.no_grad():
            # Filter out None values
            valid_pairs = [(i, img) for i, img in enumerate(images) if img is not None]
            if not valid_pairs:
                return [None] * len(images)

            indices, valid_images = zip(*valid_pairs)

            inputs = self.processor(
                images=valid_images,
                return_tensors="pt"
            ).to(self.device)

            image_features = self.model.get_image_features(**inputs)
            image_features = image_features / image_features.norm(dim=1, keepdim=True)
            embeddings_list = image_features.cpu().numpy().tolist()

            # Place embeddings back in original positions
            result = [None] * len(images)
            for idx, embedding in zip(indices, embeddings_list):
                result[idx] = embedding

            return result


def fetch_image(url: str) -> Image.Image | None:
    """Safely fetch and validate an image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return img.convert('RGB') if img.mode != 'RGB' else img
    except Exception as e:
        print(f"Error fetching image {url}: {e}")
        return None


def get_text_description(row: tuple) -> str:
    """Create rich text description from artwork data."""
    parts = []
    
    # Extract core fields
    id, museum, title, artwork_type, artist, artist_birth, artist_death = row[:7]
    date_text, start_year, end_year, is_bce = row[7:11]
    url, image_url = row[11:13]
    
    if title:
        parts.append(f"Title: {title}")
    if artwork_type:
        parts.append(f"Type: {artwork_type}")
    if artist:
        parts.append(f"Artist: {artist}")
        # Add artist lifespan if available
        if artist_birth and artist_death:
            parts.append(f"Artist lived: {artist_birth}-{artist_death}")
    if museum:
        parts.append(f"Museum: {museum}")
    if date_text:
        parts.append(f"Date: {date_text}")
        
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for art collection")
    parser.add_argument("--db_path", type=str, default=DB_PATH,
                        help=f"Path to SQLite database (default: {DB_PATH})")
    parser.add_argument("--chroma_path", type=str, default=CHROMA_PATH,
                        help=f"Path to store ChromaDB embeddings (default: {CHROMA_PATH})")
    parser.add_argument("--batch_size", type=int, default=BATCH_SIZE,
                        help=f"Batch size for processing (default: {BATCH_SIZE})")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of artworks to process (for testing)")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage even if GPU is available")
    parser.add_argument("--reset", action="store_true",
                        help="Reset existing collections in ChromaDB")
    
    args = parser.parse_args()
    
    # Initialize embedder
    clip = CLIPEmbedder()

    # Track successful image embeddings
    successful_embeddings = []

    # Initialize ChromaDB collections
    chroma_client = chromadb.PersistentClient(path=args.chroma_path)

    # Create separate collections for text and image embeddings
    if args.reset:
        try:
            chroma_client.delete_collection("artwork_text")
            chroma_client.delete_collection("artwork_images")
            print("Existing collections deleted.")
        except:
            pass
    
    text_collection = chroma_client.get_or_create_collection(
        name="artwork_text",
        metadata={"hnsw:space": "cosine"}
    )

    image_collection = chroma_client.get_or_create_collection(
        name="artwork_images",
        metadata={"hnsw:space": "cosine"}
    )

    # Get artworks from SQLite
    conn = sqlite3.connect(args.db_path)
    cursor = conn.cursor()
    
    # Build query with optional limit
    query = """
        SELECT id, museum, title, type, artist_name, artist_birth, artist_death,
               date_text, start_year, end_year, is_bce, url, image_url
        FROM artworks
    """
    
    if args.limit:
        query += f" LIMIT {args.limit}"
    
    cursor.execute(query)
    artworks = cursor.fetchall()
    total_artworks = len(artworks)
    
    print(f"Processing {total_artworks} artworks in batches of {args.batch_size}")

    # Process in batches
    for i in tqdm(range(0, total_artworks, args.batch_size), desc="Processing batches"):
        batch = artworks[i:i + args.batch_size]

        # Prepare batch data
        ids = [str(row[0]) for row in batch]
        texts = [get_text_description(row) for row in batch]
        images = [fetch_image(row[12]) if row[12] else None for row in batch]

        # Clean metadata (remove None values)
        metadatas = []
        for row in batch:
            metadata = {
                "id": row[0],
                "museum": row[1] or "",
                "title": row[2] or "",
                "type": row[3] or "",
                "artist_name": row[4] or "",
                "artist_birth": str(row[5]) if row[5] is not None else "",
                "artist_death": str(row[6]) if row[6] is not None else "",
                "date_text": row[7] or "",
                "start_year": str(row[8]) if row[8] is not None else "",
                "end_year": str(row[9]) if row[9] is not None else "",
                "is_bce": bool(row[10]),
                "url": row[11] or "",
                "image_url": row[12] or ""
            }
            metadatas.append(metadata)

        # Get embeddings
        text_embeddings, image_embeddings = clip.get_embeddings(texts, images)

        # Add text embeddings
        text_collection.upsert(
            ids=ids,
            embeddings=text_embeddings,
            documents=texts,
            metadatas=metadatas
        )

        # Add image embeddings (only for valid images)
        valid_image_data = [
            (id_, emb, text, meta)
            for id_, emb, text, meta in zip(ids, image_embeddings, texts, metadatas)
            if emb is not None
        ]

        if valid_image_data:
            # Store successful embeddings info
            for id_, _, text, meta in valid_image_data:
                successful_embeddings.append({
                    'id': id_,
                    'title': meta['title'],
                    'artist': meta['artist_name'],
                    'museum': meta['museum'],
                    'url': meta['url'],
                    'image_url': meta['image_url']
                })

            image_collection.upsert(
                ids=[d[0] for d in valid_image_data],
                embeddings=[d[1] for d in valid_image_data],
                documents=[d[2] for d in valid_image_data],
                metadatas=[d[3] for d in valid_image_data]
            )

    conn.close()
    print(f"\nProcessed {total_artworks} artworks")
    print(f"Text embeddings: {text_collection.count()}")
    print(f"Image embeddings: {image_collection.count()}")
    
    print("\nArtworks with successful image embeddings:")
    print("==========================================")
    for artwork in successful_embeddings:
        print(f"\nID: {artwork['id']}")
        print(f"Title: {artwork['title']}")
        print(f"Artist: {artwork['artist']}")
        print(f"Museum: {artwork['museum']}")
        print(f"URL: {artwork['url']}")
        print(f"Image URL: {artwork['image_url']}")
    
    # Optionally save to file
    if successful_embeddings:
        import json
        output_file = "successful_image_embeddings.json"
        with open(output_file, 'w') as f:
            json.dump(successful_embeddings, f, indent=2)
        print(f"\nSuccessful embeddings list saved to {output_file}")


if __name__ == "__main__":
    main()