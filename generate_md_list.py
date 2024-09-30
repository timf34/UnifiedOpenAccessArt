#!/usr/bin/env python

import os
import yaml


# Main function to create the Markdown file
def create_markdown(yaml_file, output_file):
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    with open(output_file, 'w') as md:
        # Header
        md.write('# Museum Datasets\n')
        md.write('*A curated list of museums offering open access datasets.*\n\n')

        # Table header
        md.write('### Datasets\n')
        md.write('| Museum | Location | Data Formats | Links |\n')
        md.write('| --- | --- | --- | --- |\n')

        # Generate table rows from YAML data
        for museum in data['museums']:
            name = museum['name']
            location = museum['location']
            formats = ', '.join(museum.get('data_formats', []))  # Join the formats as a comma-separated string
            url = museum.get('url', '')
            github = museum.get('github', '')
            dataset_links = museum.get('dataset_download_link', [])

            # Links to website, GitHub, and dataset
            link_str = ''
            if url:
                link_str += f'[Website]({url}) '
            if github:
                link_str += f'[GitHub]({github}) '
            for idx, link in enumerate(dataset_links):
                link_str += f'[Dataset {idx + 1}]({link}) '

            # Write row to Markdown
            md.write(f'| {name} | {location} | {formats} | {link_str} |\n')


if __name__ == '__main__':
    # Path to the input YAML file and the output Markdown file
    input_yaml = 'data/museums.yml'
    output_md = 'museums.md'

    # Create the Markdown file from the YAML file
    create_markdown(input_yaml, output_md)
