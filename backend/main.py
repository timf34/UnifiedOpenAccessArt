# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from typing import List, Optional
from pydantic import BaseModel

app = FastAPI()

# Configure CORS so SvelteKit (on different port) can access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["http://localhost:5173"] etc.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Example Pydantic model for a single Artwork record
class Artwork(BaseModel):
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
    url: Optional[str] = None
    image_url: Optional[str] = None


@app.get("/api/artworks")
def get_artworks(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Return a paginated list of artworks.
    Optional `search` across title, museum, or artist_name.
    `page` is 1-based; `limit` is how many items per page.
    """
    offset = (page - 1) * limit

    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()

    # --- Build the WHERE clause (super naive example) ---
    conditions = []
    params = []

    if search:
        # Use parameter binding to avoid injection:
        # We'll match search against 3 columns.
        conditions.append("(title LIKE ? OR museum LIKE ? OR artist_name LIKE ?)")
        for _ in range(3):
            params.append(f"%{search}%")

    # Combine conditions with AND if we had more. But here we have only search or none.
    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    # 1) Get total
    count_query = f"SELECT COUNT(*) FROM artworks {where_clause}"
    cursor.execute(count_query, tuple(params))
    total = cursor.fetchone()[0]

    # 2) Get rows with LIMIT/OFFSET
    data_query = f"""
        SELECT *
        FROM artworks
        {where_clause}
        ORDER BY ROWID
        LIMIT ? OFFSET ?
    """
    # Add limit/offset to the params
    query_params = params + [limit, offset]

    cursor.execute(data_query, tuple(query_params))
    rows = cursor.fetchall()
    conn.close()

    # Convert DB rows to list of dicts/Pydantic models
    # Make sure the order of columns matches your DB table:
    # (id, museum, title, type, artist_name, artist_birth, artist_death, date_text, start_year, end_year, url, image_url)
    artworks = []
    for row in rows:
        artworks.append(Artwork(
            id=row[0],
            museum=row[1],
            title=row[2],
            type=row[3],
            artist_name=row[4],
            artist_birth=row[5],
            artist_death=row[6],
            date_text=row[7],
            start_year=row[8],
            end_year=row[9],
            url=row[10],
            image_url=row[11],
        ))

    # Return total + artworks array
    return {"total": total, "artworks": artworks}
