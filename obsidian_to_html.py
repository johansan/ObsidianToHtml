from tqdm import tqdm
import os
import subprocess
import tempfile
import re
from pathlib import Path
from datetime import datetime


# Source and destination folders
source_directory = '/Users/johan/Documents/Notes-test'
output_directory = '/Users/johan/Documents/Notes-html'

# The following folders will be excluded from processing
excluded_dirs = {'_excalidraw', '_resources', '_templates', '.obsidian', '.trash'}

# Your HTML template file (located in same folder as this script)
template = 'template.html'


def get_file_modification_date(file_path):
    """Get the file modification date."""
    stat = os.stat(file_path)
    return datetime.fromtimestamp(stat.st_mtime)


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
    # Clean up Obsidian media links:
    pattern = r'!\[\[(.*?)\]\]'
    modified_content = re.sub(pattern, cleanup_image_link, content)

    # Clean up document WIKI links:
    # [[../Folder/Document]] -> [../Folder/Document](../Folder/Document.html)
    pattern = r'\[\[(.*?)\]\]'
    modified_content = re.sub(pattern, cleanup_wiki_link, modified_content)

    # Change Markdown style highlights into HTML span elements
    pattern = r'==(.*?)=='
    replacement = r'<span class="highlight">\1</span>'
    modified_content = re.sub(pattern, replacement, modified_content)

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


if __name__ == "__main__":
    current_file = os.path.realpath(__file__)
    current_folder = os.path.dirname(current_file)
    template_file = current_folder + '/' + template

    # Call the process_directory function with command line arguments
    process_directory(source_directory, output_directory, template_file)

