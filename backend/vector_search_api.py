# backend/vector_search_api.py
import chromadb
from typing import List, Optional
from pydantic import BaseModel
from transformers import CLIPTokenizer, CLIPTextModel
import torch


class SearchResult(BaseModel):
    id: str
    museum: str
    title: str
    type: Optional[str] = None
    artist_name: Optional[str] = None
    artist_birth: Optional[int] = None
    artist_death: Optional[int] = None
    date_text: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    is_bce: bool = False
    url: Optional[str] = None
    image_url: Optional[str] = None
    score: float


class VectorSearchAPI:
    def __init__(self, chroma_path: str = "../data/processed_datasets/chroma_db"):
        self.client = chromadb.PersistentClient(path=chroma_path)
        self.text_collection = self.client.get_collection("artwork_text")

        # Initialize CLIP text model for consistent embeddings
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "openai/clip-vit-base-patch32"
        self.tokenizer = CLIPTokenizer.from_pretrained(model_name)
        self.text_model = CLIPTextModel.from_pretrained(model_name).to(self.device)

        if torch.cuda.is_available():
            self.text_model = self.text_model.half()  # Use half precision on GPU

        # Set to eval mode
        self.text_model.eval()

    def _get_text_embedding(self, text: str) -> List[float]:
        """Get CLIP text embedding with proper dimension."""
        with torch.no_grad():
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=77
            ).to(self.device)

            text_features = self.text_model(**inputs).last_hidden_state[:, 0, :]
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            return text_features.cpu().numpy()[0].tolist()

    def search(
            self,
            query: str,
            page: int = 1,
            limit: int = 20,
    ) -> tuple[List[SearchResult], int]:
        """
        Search artwork by semantic similarity to query text.
        Returns tuple of (results, total_count).
        """
        try:
            # Get query embedding using CLIP
            query_embedding = self._get_text_embedding(query)

            # Calculate offset
            offset = (page - 1) * limit
            search_limit = offset + limit

            # Query the collection
            results = self.text_collection.query(
                query_embeddings=[query_embedding],  # Use embedding instead of text
                n_results=search_limit
            )

            # Process results into Pydantic models
            search_results = []
            if results['metadatas']:
                for metadata, distance in zip(results['metadatas'][0], results['distances'][0]):
                    # Convert distance to similarity score (1 - distance)
                    score = 1 - distance

                    result = SearchResult(
                        id=metadata.get("id", ""),
                        museum=metadata.get("museum", ""),
                        title=metadata.get("title", ""),
                        type=metadata.get("type", ""),
                        artist_name=metadata.get("artist_name", ""),
                        artist_birth=metadata.get("artist_birth"),
                        artist_death=metadata.get("artist_death"),
                        date_text=metadata.get("date_text", ""),
                        start_year=metadata.get("start_year"),
                        end_year=metadata.get("end_year"),
                        is_bce=metadata.get("is_bce", False),
                        url=metadata.get("url", ""),
                        image_url=metadata.get("image_url", ""),
                        score=score
                    )
                    search_results.append(result)

            # Get total count and apply pagination
            total = len(search_results)
            search_results = search_results[offset:offset + limit]

            return search_results, total

        except Exception as e:
            print(f"Error in semantic search: {str(e)}")
            return [], 0