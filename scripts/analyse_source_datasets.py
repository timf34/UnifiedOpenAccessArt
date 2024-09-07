import os
import pandas as pd


DATA_DIR: str = "../source_datasets"


def analyse_headers_in_directory(directory_path):
    # Dictionary to store headers from each file
    headers_dict = {}

    # Iterate through all files in the directory
    for filename in os.listdir(directory_path):
        if filename.endswith(".csv"):
            file_path = os.path.join(directory_path, filename)
            try:
                # Read the CSV file
                df = pd.read_csv(file_path, nrows=0)  # Read only headers
                headers = df.columns.tolist()

                # Store headers in the dictionary
                headers_dict[filename] = headers
                print(f"Headers for {filename}: {headers}")
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    return headers_dict

def summarize_headers(headers_dict):
    # Set to store all unique headers
    unique_headers = set()

    for headers in headers_dict.values():
        unique_headers.update(headers)

    print("\nSummary of unique headers across all files:")
    for header in sorted(unique_headers):
        print(header)


def main():
    # Analyze the headers in the specified directory
    headers_dict = analyse_headers_in_directory(DATA_DIR)

    # Summarize the headers across all files
    summarize_headers(headers_dict)


if __name__ == "__main__":
    main()
