from tqdm import tqdm
import json
import os
import subprocess
import tempfile
import re
import sys
from pathlib import Path
from datetime import datetime

from util import folder_utils as fu

# Configuration file for obsidian vault and destination folder
config_file_name = 'config.json'

# The following folders will be excluded from processing
excluded_dirs = {'_excalidraw', '_resources', '_templates', '.obsidian', '.trash'}

# Your HTML template file (located in same folder as this script)
template = 'template.html'


# Clean up Obsidian media links:
# ![[../../_resources/image.png|450]] -> ![](_resources/image.png)
def cleanup_image_link(match):
    inner_text = match.group(1)
    # Remove all occurrences of "../" within the matched text
    cleaned_text = re.sub(r'\.\./', '', inner_text)
    # Remove "|number" at the end of the string
    cleaned_text = re.sub(r'\|\d+$', '', cleaned_text)
    return '![](' + cleaned_text + ')'


# Clean up Obsidian WIKI links:
# [[../Folder/My document|My document]] -> [My document](../Folder/My document)
# [[My second document]] -> [My second document](My second document)
def cleanup_wiki_link(match):
    inner_text = match.group(1)
    title = ''
    # Check to see if the wiki link has a title, like "|Title" at the end of the string
    title_match = re.search(r'\|(.+?)$', inner_text)
    # Remove "|Title" at the end of the string.
    cleaned_text = re.sub(r'\|.+?$', '', inner_text)
    if title_match:
        title = title_match.group(1)
    else:
        title = cleaned_text
    return '[' + title + '](' + cleaned_text + '.html)'


def modify_content_with_regex(content):

    # Don't touch content within code blocks
    pattern = r'(```.*?```)'  # Match everything between ``` and ```
    parts = re.split(pattern, content, flags=re.DOTALL)

    for i in range(len(parts)):
        # Process only the parts outside the ``` blocks
        if not parts[i].startswith('```'):
            # Clean up Obsidian media links:
            pattern = r'!\[\[(.*?)\]\]'
            parts_content = re.sub(pattern, cleanup_image_link, parts[i])

            # Clean up document WIKI links:
            # [[../Folder/Document]] -> [../Folder/Document](../Folder/Document.html)
            pattern = r'\[\[(.*?)\]\]'
            parts_content = re.sub(pattern, cleanup_wiki_link, parts_content)

            # Change Markdown style highlights into HTML span elements
            pattern = r'==(.*?)=='
            replacement = r'<span class="highlight">\1</span>'
            parts_content = re.sub(pattern, replacement, parts_content)

            parts[i] = parts_content

    # Reassemble the content
    modified_content = ''.join(parts)

    return modified_content


def modify_and_convert_file(file_path, source_base, output_base, template_file):

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

        # Get filename
        filename = Path(file.name).stem

        # Modify the file content using regular expressions
        modified_content = modify_content_with_regex(content)

        # Create a temporary file to save modified content
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.md') as temp_file:
            temp_file.write(modified_content)
            temp_file_path = temp_file.name

        # Construct output path preserving the directory structure
        relative_path = os.path.relpath(file_path, source_base)
        output_html_path = os.path.join(output_base, Path(relative_path).with_suffix('.html'))
        output_directory = os.path.dirname(output_html_path)
        os.makedirs(output_directory, exist_ok=True)

        command = [
            'pandoc', '--standalone', '--embed-resources', '-f', 'markdown+hard_line_breaks',
            '-t', 'html', '--resource-path', source_base,
            '--template', template_file,
            '--metadata', 'title=' + filename,
            '--fail-if-warnings',
            temp_file_path, '-o', output_html_path
        ]

        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Pandoc failed, error: {e}")
            print('File: ' + filename)

        # Get the creation date of source file
        stat = os.stat(file.name)
        creation_time = stat.st_birthtime
        formatted_time = datetime.fromtimestamp(creation_time).strftime('%m/%d/%Y %H:%M:%S')
        command = ['SetFile', '-d', formatted_time, output_html_path]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error changing creation date: {e}")

        # Remove the temporary file
        os.remove(temp_file_path)


def process_directory(source_base, output_base, template_file):
    # First, create a list of all files that need to be processed
    files_to_process = []
    for root, dirs, files in os.walk(source_base, topdown=True):
        dirs[:] = [d for d in dirs if d not in excluded_dirs]  # Assuming 'excluded_dirs' is defined somewhere
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                files_to_process.append((file_path, source_base, output_base, template_file))

    # Now process the files with a progress bar
    for file_path, source_base, output_base, template_file in tqdm(files_to_process, desc="Processing files"):
        modify_and_convert_file(file_path, source_base, output_base, template_file)


def save_paths(obsidian_folder, destination_folder):
    """Save the folder paths to the config file in JSON format."""
    config_data = {'obsidian_folder': obsidian_folder, 'destination_folder': destination_folder}
    with open(config_file_name, 'w') as file:
        json.dump(config_data, file)


def load_paths():
    """Load the folder paths from the config file."""
    with open(config_file_name, 'r') as file:
        config_data = json.load(file)
    return config_data['obsidian_folder'], config_data['destination_folder']


if __name__ == "__main__":
    current_file = os.path.realpath(__file__)
    current_folder = os.path.dirname(current_file)
    template_file = current_folder + '/' + template

    # Check if the config file exists
    if os.path.exists(config_file_name):
        obsidian_folder, destination_folder = load_paths()
        print("Loaded paths from config file.\nObsidian vault: ", obsidian_folder, "\nDestination folder: ", destination_folder)
    else:
        obsidian_folder = fu.remove_trailing_slash(input("Enter source path to your Obsidian vault: "))

        # Check for .obsidian folder in Obsidian_folder
        if not fu.folder_exists(obsidian_folder, ".obsidian"):
            print("Error: No '.obsidian' folder found in the specified Obsidian vault, please check your path.")
            sys.exit(1)

        destination_folder = fu.remove_trailing_slash(input("Enter destination folder for generated HTML: "))

        # Check if Destination_folder is empty
        if not fu.folder_empty(destination_folder):
            proceed = input("Warning: The destination folder is not empty. Do you want to continue? (y/n): ")
            if proceed.lower() != 'y':
                print("Operation cancelled by the user.")
                sys.exit(1)

        save_paths(obsidian_folder, destination_folder)
        print("Paths have been saved to '" + config_file_name + "'")

    # Call the process_directory function with command line arguments
    process_directory(obsidian_folder, destination_folder, template_file)

