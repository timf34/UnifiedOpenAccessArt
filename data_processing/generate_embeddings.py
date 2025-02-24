# generate_embeddings.py
import chromadb
import sqlite3
import requests
from PIL import Image
from io import BytesIO
from tqdm import tqdm
import torch
from transformers import CLIPProcessor, CLIPModel

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
        list[list[float]], list[list[float]]]:
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

            text_embeddings = self.model.get_text_features(**inputs)
            text_embeddings = text_embeddings / text_embeddings.norm(dim=1, keepdim=True)

            return text_embeddings.cpu().numpy().tolist()

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

            image_embeddings = self.model.get_image_features(**inputs)
            image_embeddings = image_embeddings / image_embeddings.norm(dim=1, keepdim=True)
            embeddings_list = image_embeddings.cpu().numpy().tolist()

            # Place embeddings back in original positions
            result = [None] * len(images)
            for idx, embedding in zip(indices, embeddings_list):
                result[idx] = embedding

            return result


def fetch_image(url: str) -> Image.Image | None:
    """Safely fetch and validate an image from URL."""
    try:
        response = requests.get(url, timeout=10)
        img = Image.open(BytesIO(response.content))
        return img.convert('RGB') if img.mode != 'RGB' else img
    except Exception as e:
        print(f"Error fetching image {url}: {e}")
        return None


def get_text_description(row: tuple) -> str:
    """Create text description from artwork data."""
    title, type_, artist, museum, date = row[1:6]
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if type_:
        parts.append(f"Type: {type_}")
    if artist:
        parts.append(f"Artist: {artist}")
    if museum:
        parts.append(f"Museum: {museum}")
    if date:
        parts.append(f"Date: {date}")
    return " | ".join(parts)


def main():
    # Initialize embedder
    clip = CLIPEmbedder()

    # Initialize ChromaDB collections
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

    # Create separate collections for text and image embeddings
    text_collection = chroma_client.get_or_create_collection(
        name="artwork_text",
        metadata={"hnsw:space": "cosine"}
    )

    image_collection = chroma_client.get_or_create_collection(
        name="artwork_images",
        metadata={"hnsw:space": "cosine"}
    )

    # Get artworks from SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, type, artist_name, museum, date_text, image_url 
        FROM artworks
    """)
    artworks = cursor.fetchall()

    # Process in batches
    for i in tqdm(range(0, len(artworks), BATCH_SIZE)):
        batch = artworks[i:i + BATCH_SIZE]

        # Prepare batch data
        ids = [str(row[0]) for row in batch]
        texts = [get_text_description(row) for row in batch]
        images = [fetch_image(row[6]) if row[6] else None for row in batch]

        # Clean metadata (remove None values)
        metadatas = []
        for row in batch:
            metadata = {
                "title": row[1] or "",
                "type": row[2] or "",
                "artist": row[3] or "",
                "museum": row[4] or "",
                "date": row[5] or "",
                "image_url": row[6] or ""
            }
            metadatas.append(metadata)

        # Get embeddings
        text_embeddings, image_embeddings = clip.get_embeddings(texts, images)

        # Add text embeddings
        text_collection.add(
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
            image_collection.add(
                ids=[d[0] for d in valid_image_data],
                embeddings=[d[1] for d in valid_image_data],
                documents=[d[2] for d in valid_image_data],
                metadatas=[d[3] for d in valid_image_data]
            )

    conn.close()
    print(f"Processed {len(artworks)} artworks")
    print(f"Text embeddings: {text_collection.count()}")
    print(f"Image embeddings: {image_collection.count()}")


if __name__ == "__main__":
    main()