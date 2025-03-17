# data_processing/dataset_manager.py
import os
import pandas as pd
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import sys

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from data_processing.registry import ProcessorRegistry
from models.data_models import UnifiedArtwork

class DatasetManager:
    """Manager for multiple art museum datasets with focus on image accessibility."""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = str(project_root / "data" / "source_datasets")
        self.data_dir = Path(data_dir)
        self.registry = ProcessorRegistry()
        self.datasets = self.registry.supported_museums
        print(f"Found {len(self.datasets)} supported datasets: {', '.join(self.datasets)}")
    
    def list_datasets(self) -> Dict:
        """List all available datasets with their properties."""
        results = {}
        for dataset_id in self.datasets:
            file_pattern = self.registry.get_source_file_pattern(dataset_id)
            file_path = self.data_dir / file_pattern if file_pattern else None
            exists = file_path.exists() if file_path else False
            
            results[dataset_id] = {
                "file": file_pattern,
                "path": str(file_path) if file_path else None,
                "exists": exists,
                "processor": self.registry.get_processor(dataset_id).__class__.__name__ if exists else None
            }
        return results
    
    def get_dataset(self, 
                    dataset_id: str, 
                    limit: Optional[int] = None, 
                    with_images_only: bool = False) -> List[UnifiedArtwork]:
        """
        Get processed data from a specific dataset.
        
        Args:
            dataset_id: ID of the dataset to process
            limit: Maximum number of artworks to return
            with_images_only: Only return artworks with image URLs
            
        Returns:
            List of UnifiedArtwork objects
        """
        if dataset_id not in self.datasets:
            raise ValueError(f"Dataset {dataset_id} not found")
        
        # Get file path and processor
        file_pattern = self.registry.get_source_file_pattern(dataset_id)
        if not file_pattern:
            raise ValueError(f"No file pattern defined for {dataset_id}")
            
        file_path = self.data_dir / file_pattern
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset file not found: {file_path}")
            
        # Process the dataset
        processor = self.registry.get_processor(dataset_id)
        artworks = processor.get_unified_data(
            str(file_path),
            dev_mode=limit is not None
        )
        
        # Apply limit if specified
        if limit and limit < len(artworks):
            artworks = artworks[:limit]
            
        # Filter for artworks with images if requested
        if with_images_only:
            artworks = [a for a in artworks if a.images and len(a.images) > 0 and a.images[0].url]
            
        return artworks
    
    def get_all_datasets(self, 
                         limit_per_dataset: Optional[int] = None, 
                         with_images_only: bool = False) -> List[UnifiedArtwork]:
        """
        Get processed data from all available datasets.
        
        Args:
            limit_per_dataset: Maximum number of artworks per dataset
            with_images_only: Only return artworks with image URLs
            
        Returns:
            List of UnifiedArtwork objects from all datasets
        """
        all_artworks = []
        
        for dataset_id in self.datasets:
            try:
                print(f"Processing {dataset_id}...")
                artworks = self.get_dataset(
                    dataset_id,
                    limit=limit_per_dataset,
                    with_images_only=with_images_only
                )
                all_artworks.extend(artworks)
                print(f"Added {len(artworks)} artworks from {dataset_id}")
            except Exception as e:
                print(f"Error processing {dataset_id}: {e}")
                continue
                
        return all_artworks
    
    def check_image_accessibility(self, 
                                 dataset_id: Optional[str] = None, 
                                 sample_size: int = 5,
                                 timeout: int = 5) -> Dict:
        """
        Check if images from datasets can be accessed (not blocked by Cloudflare, etc.)
        
        Args:
            dataset_id: Specific dataset to check (None for all)
            sample_size: Number of images to check per dataset
            timeout: Timeout in seconds for each request
            
        Returns:
            Dict with accessibility statistics for each dataset
        """
        results = {}
        datasets_to_check = [dataset_id] if dataset_id else self.datasets
        
        def check_url(url):
            try:
                # Make a GET request with stream=True to only download headers and a small part of the content
                response = requests.get(url, timeout=timeout, stream=True)
                
                # Check if status code indicates success
                if response.status_code >= 400:
                    return url, False, f"HTTP error: {response.status_code}"
                
                # Check Content-Type header to verify it's an image
                content_type = response.headers.get('Content-Type', '')
                if not content_type.startswith('image/'):
                    return url, False, f"Not an image: {content_type}"
                
                # Download just the first few bytes to verify it's a valid image
                # Most image formats have recognizable signatures in the first few bytes
                content_start = next(response.iter_content(chunk_size=32), b'')
                
                # Check for common image format signatures
                is_valid_image = False
                
                # JPEG starts with FF D8
                if content_start.startswith(b'\xFF\xD8'):
                    is_valid_image = True
                # PNG starts with 89 50 4E 47 0D 0A 1A 0A
                elif content_start.startswith(b'\x89PNG\r\n\x1a\n'):
                    is_valid_image = True
                # GIF starts with GIF87a or GIF89a
                elif content_start.startswith(b'GIF87a') or content_start.startswith(b'GIF89a'):
                    is_valid_image = True
                # WebP starts with RIFF....WEBP
                elif content_start.startswith(b'RIFF') and b'WEBP' in content_start:
                    is_valid_image = True
                # SVG is an XML file that should contain "<svg"
                elif b'<svg' in content_start:
                    is_valid_image = True
                
                if not is_valid_image:
                    return url, False, "Invalid image format"
                
                # Close the response to free up resources
                response.close()
                
                return url, True, response.status_code
            except Exception as e:
                return url, False, str(e)
        
        for dataset_id in datasets_to_check:
            try:
                print(f"Checking images for {dataset_id}...")
                
                # Get artworks with images
                artworks = self.get_dataset(dataset_id, limit=sample_size*2, with_images_only=True)
                
                if not artworks:
                    results[dataset_id] = {
                        "status": "No images found",
                        "total_artworks": 0,
                        "total_images": 0,
                        "accessible_images": 0,
                        "accessibility_rate": 0,
                        "samples": []
                    }
                    continue
                
                # Extract URLs
                urls = []
                art_map = {}  # Map URLs to artwork info
                
                for artwork in artworks:
                    for image in artwork.images:
                        if image.url:
                            url = str(image.url)
                            urls.append(url)
                            art_map[url] = {
                                "id": artwork.id,
                                "title": artwork.object.name,
                                "artist": artwork.artist.name,
                                "museum": artwork.museum.name
                            }
                            
                # Limit to sample size
                if len(urls) > sample_size:
                    urls = urls[:sample_size]
                    
                if not urls:
                    results[dataset_id] = {
                        "status": "No image URLs found",
                        "total_artworks": len(artworks),
                        "total_images": 0,
                        "accessible_images": 0,
                        "accessibility_rate": 0,
                        "samples": []
                    }
                    continue
                
                # Check URLs
                samples = []
                with ThreadPoolExecutor(max_workers=min(10, len(urls))) as executor:
                    for url, success, status in tqdm(
                        executor.map(check_url, urls),
                        total=len(urls),
                        desc=f"Checking {dataset_id}"
                    ):
                        artwork_info = art_map.get(url, {})
                        samples.append({
                            "url": url,
                            "accessible": success,
                            "status": status,
                            "artwork": artwork_info
                        })
                
                # Compute statistics
                accessible = sum(1 for s in samples if s["accessible"])
                results[dataset_id] = {
                    "status": "OK",
                    "total_artworks": len(artworks),
                    "total_images": len(urls),
                    "accessible_images": accessible,
                    "accessibility_rate": (accessible / len(urls)) * 100 if urls else 0,
                    "samples": samples
                }
                
            except Exception as e:
                results[dataset_id] = {
                    "status": f"Error: {str(e)}",
                    "total_artworks": 0,
                    "total_images": 0,
                    "accessible_images": 0,
                    "accessibility_rate": 0,
                    "samples": []
                }
                
        return results
    
    def display_image_summary(self, results: Dict):
        """Pretty print the image accessibility results."""
        print("\n=== IMAGE ACCESSIBILITY SUMMARY ===")
        print(f"{'Dataset':<25} | {'Access Rate':<10} | {'Success/Total':<12} | {'Status'}")
        print("-" * 75)
        
        for dataset_id, result in results.items():
            rate = f"{result['accessibility_rate']:.1f}%" if result['total_images'] > 0 else "N/A"
            counts = f"{result['accessible_images']}/{result['total_images']}" if result['total_images'] > 0 else "0/0"
            status = result['status']
            print(f"{dataset_id:<25} | {rate:<10} | {counts:<12} | {status}")
        
        # Collect error types for a summary
        error_categories = {
            "HTTP error": 0,
            "Not an image": 0,
            "Invalid image format": 0,
            "Connection error": 0,
            "Timeout": 0,
            "Other": 0
        }
        
        print("\n=== ERROR SUMMARY ===")
        for dataset_id, result in results.items():
            for sample in result['samples']:
                if not sample['accessible']:
                    status = str(sample['status'])
                    if status.startswith("HTTP error"):
                        error_categories["HTTP error"] += 1
                    elif status.startswith("Not an image"):
                        error_categories["Not an image"] += 1
                    elif status == "Invalid image format":
                        error_categories["Invalid image format"] += 1
                    elif "ConnectionError" in status or "ConnectTimeout" in status:
                        error_categories["Connection error"] += 1
                    elif "Timeout" in status:
                        error_categories["Timeout"] += 1
                    else:
                        error_categories["Other"] += 1
        
        # Print error summary
        total_errors = sum(error_categories.values())
        if total_errors > 0:
            print(f"Total errors: {total_errors}")
            for category, count in error_categories.items():
                if count > 0:
                    percentage = (count / total_errors) * 100
                    print(f"  - {category}: {count} ({percentage:.1f}%)")
        else:
            print("No errors found!")
            
        print("\n=== DETAILED SAMPLES ===")
        for dataset_id, result in results.items():
            if not result['samples']:
                continue
                
            print(f"\n{dataset_id}:")
            for i, sample in enumerate(result['samples'], 1):
                status = "✓" if sample['accessible'] else "✗"
                artwork = sample['artwork']
                print(f"  {i}. {status} {artwork.get('title', 'Untitled')} by {artwork.get('artist', 'Unknown')}")
                print(f"     URL: {sample['url']}")
                if not sample['accessible']:
                    print(f"     Error: {sample['status']}")
                print()
                
    def get_dataset_statistics(self, dataset_id: Optional[str] = None) -> Dict:
        """
        Get statistics about the number of objects in each dataset.
        
        Args:
            dataset_id: Specific dataset to check (None for all)
            
        Returns:
            Dict with statistics for each dataset
        """
        results = {}
        datasets_to_check = [dataset_id] if dataset_id else self.datasets
        
        for dataset_id in tqdm(datasets_to_check, desc="Processing datasets"):
            try:
                print(f"\nCounting objects in {dataset_id}...")
                
                # Get file path and processor
                file_pattern = self.registry.get_source_file_pattern(dataset_id)
                if not file_pattern:
                    results[dataset_id] = {
                        "status": "No file pattern defined",
                        "total_objects": 0,
                        "objects_with_images": 0
                    }
                    continue
                    
                file_path = self.data_dir / file_pattern
                if not file_path.exists():
                    results[dataset_id] = {
                        "status": "File not found",
                        "total_objects": 0,
                        "objects_with_images": 0
                    }
                    continue
                
                # Process the dataset
                processor = self.registry.get_processor(dataset_id)
                artworks = processor.get_unified_data(str(file_path))
                
                # Count objects with images
                objects_with_images = sum(1 for a in artworks if a.images and len(a.images) > 0 and a.images[0].url)
                
                results[dataset_id] = {
                    "status": "OK",
                    "total_objects": len(artworks),
                    "objects_with_images": objects_with_images,
                    "image_rate": (objects_with_images / len(artworks)) * 100 if artworks else 0
                }
                
            except Exception as e:
                results[dataset_id] = {
                    "status": f"Error: {str(e)}",
                    "total_objects": 0,
                    "objects_with_images": 0,
                    "image_rate": 0
                }
                
        return results