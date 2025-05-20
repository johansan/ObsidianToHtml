# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ObsidianToHtml is a Python script that converts Obsidian vault markdown documents into HTML documents, preserving the folder structure. It uses Pandoc to convert files and handles various Obsidian-specific formats.

Key features:
- Converts all markdown files to HTML
- Preserves file structure
- Embeds images in-place for self-contained notes
- Converts Obsidian-specific syntax (wiki links, image formatting)
- Handles YouTube links by embedding them
- Preserves file creation dates
- Converts Obsidian highlights to HTML

## Requirements

- Python 3.x
- Pandoc (external dependency)
- Python packages in requirements.txt

## Setup Development Environment

### Setting up a Virtual Environment

1. Create a virtual environment:
   ```bash
   # Create a virtual environment in the .venv directory
   python -m venv .venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source .venv/bin/activate
   # On Windows:
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   # Install required packages
   pip install -r requirements.txt
   ```

3. External dependencies:
   - Install Pandoc from https://pandoc.org/installing.html

### Running the Script with Virtual Environment

Always activate the virtual environment before running the script:

```bash
# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Run the script
python obsidian_to_html.py
```

On first run, you'll be prompted to provide:
1. Path to your Obsidian vault
2. Destination folder for HTML output

These paths are saved to `config.json` for subsequent runs.

## File Structure

- `obsidian_to_html.py` - Main script
- `template.html` - HTML template used for conversion
- `util/folder_utils.py` - Utility functions for folder operations
- `config.json` - Created on first run to store folder paths
- `requirements.txt` - Python package dependencies

## Key Components

1. **File Processing**:
   - `modify_and_convert_file()` - Processes individual files
   - `process_directory()` - Walks through the directory tree processing markdown files

2. **Content Transformation**:
   - `modify_content_with_regex()` - Applies regex transformations to convert Obsidian-specific syntax
   - `cleanup_image_link()` - Converts Obsidian image links to standard markdown
   - `cleanup_wiki_link()` - Converts Obsidian wiki links to standard markdown links
   - `get_youtube_embed_code()` - Generates HTML for embedding YouTube videos

3. **Utility Functions**:
   - `folder_exists()` - Checks if a folder exists
   - `folder_empty()` - Checks if a folder is empty (ignoring .DS_Store)
   - `remove_trailing_slash()` - Sanitizes path inputs

## Customization

- Modify `template.html` to change the HTML output style and formatting
- Adjust `excluded_dirs` in `obsidian_to_html.py` to exclude additional folders
- Frontmatter properties can be added to the template using `$property$` syntax

## Common Tasks

### Adding Support for New Obsidian Formats

1. Identify the format pattern in Obsidian markdown
2. Add a new regex pattern and replacement function in `modify_content_with_regex()`
3. Test with sample content

### Modifying HTML Output

Edit the `template.html` file to change the styling or structure of generated HTML files.