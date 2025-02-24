import requests
from pprint import pprint


def run_semantic_search(query: str = "animals", page: int = 1, limit: int = 5):
    """Test the semantic search endpoint"""
    url = f"http://127.0.0.1:8000/api/semantic-search?query={query}&page={page}&limit={limit}"

    print(f"\nTesting semantic search for query: '{query}'")
    print(f"URL: {url}\n")

    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes

        data = response.json()
        total = data.get('total', 0)
        artworks = data.get('artworks', [])

        print(f"Found {total} total results")
        print("\nTop {limit} results:")
        print("-" * 50)

        for i, artwork in enumerate(artworks, 1):
            print(f"\n{i}. {artwork['title']}")
            print(f"   Artist: {artwork.get('artist_name', 'Unknown')}")
            print(f"   Museum: {artwork.get('museum', 'Unknown')}")
            print(f"   Score: {artwork.get('score', 0):.3f}")
            print(f"   URL: {artwork.get('web_url', 'Unknown')}")

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    run_semantic_search("animals")
    run_semantic_search("men")
    run_semantic_search("swan")
