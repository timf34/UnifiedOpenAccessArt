# backend/main.py
from fastapi import FastAPI, Query, HTTPException
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


@app.get("/api/artworks/{art_id}", response_model=Artwork)
def get_artwork(art_id: str):
    """
    Return a single Artwork by its `id`.
    Raise 404 if not found.
    """
    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()
    # Query by ID:
    cursor.execute("SELECT * FROM artworks WHERE id = ?", (art_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Artwork not found")

    # Build Artwork from row
    artwork = Artwork(
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
    )
    return artwork


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


@app.get("/api/artists")
def get_artists():
    """
    Return a list of all artists and their artwork counts, sorted by name
    """
    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()
    
    query = """
        SELECT artist_name, COUNT(*) as count 
        FROM artworks 
        WHERE artist_name IS NOT NULL 
        GROUP BY artist_name 
        ORDER BY artist_name
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    artists = [{"name": row[0], "count": row[1]} for row in rows]
    return artists

@app.get("/api/museums")
def get_museums():
    """
    Return a list of all museums and their artwork counts, sorted by name
    """
    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()
    
    query = """
        SELECT museum, COUNT(*) as count 
        FROM artworks 
        WHERE museum IS NOT NULL 
        GROUP BY museum 
        ORDER BY museum
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return [{"name": row[0], "count": row[1]} for row in rows]

@app.get("/api/time-periods")
def get_time_periods():
    """
    Return a list of time periods (by century) and their artwork counts
    """
    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()
    
    query = """
        WITH century_data AS (
            SELECT 
                CASE 
                    WHEN start_year IS NOT NULL THEN ((start_year / 100) + 1) || 'th Century'
                    WHEN end_year IS NOT NULL THEN ((end_year / 100) + 1) || 'th Century'
                    ELSE NULL 
                END as century,
                COUNT(*) as count
            FROM artworks 
            WHERE start_year IS NOT NULL OR end_year IS NOT NULL
            GROUP BY century
            HAVING century IS NOT NULL
            ORDER BY MIN(COALESCE(start_year, end_year))
        )
        SELECT century, count FROM century_data
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    return [{"name": row[0], "count": row[1]} for row in rows]
