Example SQLite queries you can run:

        # Count artworks by museum:
        SELECT * FROM artwork_counts_by_museum;

        # Find all artworks by a specific artist:
        SELECT * FROM artworks WHERE artist_name LIKE '%Van Gogh%';

        # Count artworks with images by museum:
        SELECT museum, COUNT(*) as count
        FROM artworks_with_images
        GROUP BY museum;