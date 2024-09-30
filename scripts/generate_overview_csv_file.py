import os
import pandas as pd

DATA_DIR: str = "../data/source_datasets"  # Specify your directory path here
OUTPUT_FILE: str = "../data/overview.csv"  # Output file for the overview


def write_overview_to_csv(directory_path, output_file):
    # Create or overwrite the output CSV file
    with open(output_file, mode='w') as output:
        # Iterate through all files in the directory
        for filename in os.listdir(directory_path):
            if filename.endswith(".csv"):
                file_path = os.path.join(directory_path, filename)
                try:
                    # Read the first 5 lines of the CSV file
                    df = pd.read_csv(file_path, nrows=5)

                    # Write the filename as a header
                    output.write(f"Filename: {filename}\n")

                    # Write the first 5 lines of the CSV file to the overview CSV
                    df.to_csv(output, index=False)

                    # Write a blank line to separate different CSV files
                    output.write("\n\n")
                    print(f"Processed {filename}")
                except Exception as e:
                    print(f"Error processing {filename}: {e}")


def main():
    write_overview_to_csv(DATA_DIR, OUTPUT_FILE)
    print(f"Overview CSV created at {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
