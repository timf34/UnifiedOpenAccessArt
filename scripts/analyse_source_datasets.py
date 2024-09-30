import os
import pandas as pd

DATA_DIR: str = "../data/source_datasets"


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


def print_aligned_headers(headers_dict):
    # Find the maximum length of the filename and headers for padding
    max_filename_length = max(len(filename) for filename in headers_dict)
    max_header_length = max(max(len(header) for header in headers) for headers in headers_dict.values())

    # Print headers in a tabular format
    print("\nHeaders in a unified format:")
    for filename, headers in headers_dict.items():
        print(f"{filename.ljust(max_filename_length)} : ", end="")
        for header in headers:
            print(f"{header.ljust(max_header_length)}", end=" | ")
        print()  # New line after each file's headers


def list_all_headers(headers_dict):
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

    # Print the headers in a unified format
    print_aligned_headers(headers_dict)

    # # List all unique headers across all files
    # list_all_headers(headers_dict)


if __name__ == "__main__":
    main()
