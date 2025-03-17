import argparse
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.absolute()
sys.path.append(str(project_root))

from data_processing.dataset_manager import DatasetManager

def main():
    parser = argparse.ArgumentParser(description="Check dataset image accessibility")
    parser.add_argument("--dataset", type=str, default=None, help="Specific dataset to check (omit for all)")
    parser.add_argument("--samples", type=int, default=5, help="Number of samples per dataset")
    parser.add_argument("--timeout", type=int, default=5, help="Request timeout in seconds")
    parser.add_argument("--data-dir", type=str, 
                        default=str(project_root / "data" / "source_datasets"), 
                        help="Directory containing source datasets")
    parser.add_argument("--skip-counts", action="store_true", 
                        help="Skip counting objects in datasets (faster)")
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = DatasetManager(data_dir=args.data_dir)
    
    # List available datasets
    print("Available datasets:")
    for dataset_id, info in manager.list_datasets().items():
        status = "Available" if info["exists"] else "Missing file"
        print(f"  - {dataset_id}: {status}")
    
    # Get and display dataset statistics
    dataset_stats = {}
    if not args.skip_counts:
        print("\nDataset Statistics:")
        dataset_stats = manager.get_dataset_statistics(dataset_id=args.dataset)
        
        # Display statistics
        print(f"{'Dataset':<25} | {'Total Objects':<12} | {'With Images':<12} | {'Image Rate'}")
        print("-" * 75)
        
        for dataset_id, stats in dataset_stats.items():
            total = stats.get("total_objects", 0)
            with_images = stats.get("objects_with_images", 0)
            image_rate = f"{(with_images / total * 100):.1f}%" if total > 0 else "N/A"
            print(f"{dataset_id:<25} | {total:<12} | {with_images:<12} | {image_rate}")
    
    # Check image accessibility
    print("\nChecking image accessibility...")
    results = manager.check_image_accessibility(
        dataset_id=args.dataset,
        sample_size=args.samples,
        timeout=args.timeout
    )
    
    # Display results
    manager.display_image_summary(results)
    
    # Optionally save results to a file
    import json
    from datetime import datetime
    
    output_file = Path(__file__).parent / "image_accessibility_results.json"
    
    # Combine dataset statistics and image accessibility results
    output_data = {
        "dataset_statistics": dataset_stats if not args.skip_counts else {},
        "image_accessibility": results
    }
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    main()