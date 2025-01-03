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
    is_bce: bool = False
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
        is_bce=row[10],
        url=row[11],
        image_url=row[12],
    )
    return artwork


@app.get("/api/artworks")
def get_artworks(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    min_year: Optional[int] = Query(None),
    max_year: Optional[int] = Query(None),
    min_is_bce: bool = Query(False),
    max_is_bce: bool = Query(False)
):
    """
    Return a paginated list of artworks.
    Optional `search` across title, museum, or artist_name.
    Optional year range filter with separate BCE flags for start and end years.
    `page` is 1-based; `limit` is how many items per page.
    """
    offset = (page - 1) * limit

    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()

    # --- Build the WHERE clause ---
    conditions = []
    params = []

    if search:
        conditions.append("(title LIKE ? OR museum LIKE ? OR artist_name LIKE ?)")
        for _ in range(3):
            params.append(f"%{search}%")

    if min_year is not None or max_year is not None:
        year_conditions = []
        
        if min_year is not None:
            if min_is_bce:
                # For BCE start date
                year_conditions.extend([
                    "(is_bce = 1 AND start_year <= ?)",  # BCE dates: larger numbers are earlier
                ])
                params.extend([min_year])
            else:
                # For CE start date
                year_conditions.extend([
                    "((is_bce = 0 AND start_year >= ?) OR (start_year IS NULL AND end_year >= ?))",
                ])
                params.extend([min_year, min_year])
            
        if max_year is not None:
            if max_is_bce:
                # For BCE end date
                year_conditions.extend([
                    "(is_bce = 1 AND end_year >= ?)",  # BCE dates: smaller numbers are later
                ])
                params.extend([max_year])
            else:
                # For CE end date
                year_conditions.extend([
                    "((is_bce = 0 AND end_year <= ?) OR (end_year IS NULL AND start_year <= ?))",
                ])
                params.extend([max_year, max_year])
            
        if year_conditions:
            conditions.append(f"({' OR '.join(year_conditions)})")  # Use OR to allow BCE to CE ranges

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
            is_bce=row[10],
            url=row[11],
            image_url=row[12],
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

@app.get("/api/time-range")
def get_time_range():
    """
    Return the minimum and maximum years in the dataset
    """
    conn = sqlite3.connect("../data/processed_datasets/unified_art.db")
    cursor = conn.cursor()
    
    query = """
        SELECT 
            MIN(CASE 
                WHEN start_year IS NOT NULL THEN start_year 
                WHEN end_year IS NOT NULL THEN end_year 
                END) as min_year,
            MAX(CASE 
                WHEN end_year IS NOT NULL THEN end_year
                WHEN start_year IS NOT NULL THEN start_year 
                END) as max_year
        FROM artworks 
        WHERE start_year IS NOT NULL 
           OR end_year IS NOT NULL
    """
    
    cursor.execute(query)
    min_year, max_year = cursor.fetchone()
    conn.close()
    
    return {"min_year": min_year, "max_year": max_year}
