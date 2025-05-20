# v1.0.0

from tqdm import tqdm
import io
import json
import os
import platform
import subprocess
import tempfile
import re
import sys
import shutil
from pathlib import Path
from datetime import datetime
import urllib.parse

from util import folder_utils as fu

# Configuration file for obsidian vault and destination folder
config_file_name = 'config.json'

# The following folders will be excluded from processing
excluded_dirs = {'_excalidraw', '_resources', '_templates', '.obsidian', '.trash'}

def check_pandoc_installed():
    """
    Check if pandoc is installed and accessible from the command line.
    If not, provide installation instructions based on the operating system.
    Returns True if pandoc is installed, False otherwise.
    """
    if shutil.which('pandoc') is not None:
        return True
    
    print("Error: Pandoc is not installed or not in your PATH.")
    print("\nPandoc is required for this script to run. Installation instructions:")
    
    if platform.system() == 'Darwin':  # macOS
        # Check if Homebrew is installed
        if shutil.which('brew') is not None:
            print("\nHomebrew is installed. Install Pandoc using:")
            print("    brew install pandoc")
        else:
            print("\nHomebrew is not installed. You can:")
            print("1. Install Homebrew first with:")
            print("    /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("   Then install Pandoc with: brew install pandoc")
            print("2. Or download Pandoc directly from: https://pandoc.org/installing.html")
    elif platform.system() == 'Windows':
        print("\nWindows installation options:")
        print("1. Download the installer from: https://pandoc.org/installing.html")
        print("2. Or use Chocolatey: choco install pandoc")
        print("3. Or use Winget: winget install pandoc")
    else:  # Linux and others
        print("\nLinux installation options:")
        print("1. Use your package manager, e.g.:")
        print("   - Debian/Ubuntu: sudo apt-get install pandoc")
        print("   - Fedora: sudo dnf install pandoc")
        print("   - Arch Linux: sudo pacman -S pandoc")
        print("2. Or download from: https://pandoc.org/installing.html")
    
    print("\nAfter installation, restart your terminal and try running this script again.")
    return False

# Your HTML template file (located in same folder as this script)
template = 'template.html'


# Clean up Obsidian media links:
# ![[../../_resources/my image.png|450]] -> ![](_resources/my%20image.png){ width=450px }
def cleanup_image_link(match):
    inner_text = match.group(1)
    # Extract the width if present
    width_match = re.search(r'\|(\d+)$', inner_text)
    width = width_match.group(1) if width_match else None
    
    # Remove "|width" at the end of the string
    cleaned_text = re.sub(r'\|\d+$', '', inner_text)
    
    # Format the URL in standard markdown format with width attribute if present
    if width:
        return f'![]({cleaned_text}){{ width={width}px }}'
    else:
        return f'![]({cleaned_text})'


# Clean up Obsidian WIKI links:
# [[../Folder/My document|My document]] -> [My document](../Folder/My%20document)
# [[My second document]] -> [My%20second%20document](My%20second%20document)
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


def modify_content_with_regex(content, youtube_placeholders=None):
    # Don't touch content within code blocks
    parts = re.split(r'(```.*?```)', content, flags=re.DOTALL)
    yt_index = 0  # Counter for YouTube placeholders
    if youtube_placeholders is None:
        youtube_placeholders = {}

    for i in range(len(parts)):
        # Process only the parts outside the ``` blocks
        if not parts[i].startswith('```'):
            
            # Detect YouTube image links and process them before other image transforms.
            def replace_youtube(match):
                nonlocal yt_index
                alt_text = match.group(1)
                url = match.group(2)
                placeholder = f"YOUTUBEPLACEHOLDER_{yt_index}"
                yt_index += 1
                youtube_placeholders[placeholder] = {'url': url, 'alt': alt_text}
                # Remove the "!" so pandoc treats it as a normal link with the placeholder text.
                return f'[{placeholder}]({url})'
            
            pattern_youtube = r'!\[([^\]]*)\]\((https?://(?:www\.youtube\.com/watch\?v=[^)]+|https?://youtu\.be/[^)]+))\)'
            parts[i] = re.sub(pattern_youtube, replace_youtube, parts[i])
            
            # Clean up Obsidian media links:
            pattern_media = r'!\[\[(.*?)\]\]'
            parts[i] = re.sub(pattern_media, cleanup_image_link, parts[i])
            
            # Clean up document WIKI links:
            pattern_wiki = r'\[\[(.*?)\]\]'
            parts[i] = re.sub(pattern_wiki, cleanup_wiki_link, parts[i])
            
            # Change Markdown style highlights into HTML span elements:
            pattern_highlight = r'==(.*?)=='
            parts[i] = re.sub(pattern_highlight, r'<span class="highlight">\1</span>', parts[i])
            
            # TODO: Add more regex patterns to modify the content as you like

    modified_content = ''.join(parts)
    return modified_content


def get_youtube_embed_code(url):
    """
    Given a YouTube URL, extract the video ID and return the corresponding embed iframe HTML code.
    """
    parsed_url = urllib.parse.urlparse(url)
    video_id = None

    if 'youtube.com' in parsed_url.netloc:
        query_params = urllib.parse.parse_qs(parsed_url.query)
        video_id = query_params.get('v', [None])[0]
    elif 'youtu.be' in parsed_url.netloc:
        video_id = parsed_url.path.lstrip('/')

    if video_id:
        return f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
    
    return None


def modify_and_convert_file(file_path, source_base, output_base, template_file):
    youtube_placeholders = {}  # Dictionary to store YouTube link details for this file
    with open(file_path, 'r', encoding='utf-8') as file:
        # Get content
        content = file.read()

    # Modify file content using regex while capturing YouTube placeholders
    modified_content = modify_content_with_regex(content, youtube_placeholders)

    # Create an in-memory buffer for the modified content
    with io.StringIO(modified_content) as temp_buffer:

        # Get filename
        filename = Path(file_path).stem

        # Get folderpath
        foldername = os.path.dirname(file_path)

        # Construct output path preserving the directory structure
        relative_path = os.path.relpath(file_path, source_base)
        output_html_path = os.path.join(output_base, Path(relative_path).with_suffix('.html'))
        output_directory = os.path.dirname(output_html_path)
        os.makedirs(output_directory, exist_ok=True)

        command = [
            'pandoc', '--standalone', '--embed-resources', '-f', 'markdown+hard_line_breaks',
            '-t', 'html', '--resource-path', f"{source_base}:{foldername}",
            '--template', template_file,
            '--metadata', 'title=' + filename,
            '--fail-if-warnings',
            '-', '-o', output_html_path
        ]

        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            _, stderr = process.communicate(input=temp_buffer.getvalue())                
            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, command, stderr=stderr)
        except FileNotFoundError:
            # This might happen if pandoc is not in the PATH or not installed
            print(f"Error: Could not execute pandoc command. Please ensure pandoc is installed and in your PATH.")
            print("Run this script again to see installation instructions.")
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            # Pandoc failed. Probably due to invalid relative path.
            print(f"Pandoc failed, writing filename to error.txt. Error: {e}")

            # Write the name of the failed file to error.txt
            with open("error.txt", "a", encoding='utf-8') as output_file:
                output_file.write(f"{file_path}\n")

    # Post-process the generated HTML file to replace YouTube placeholders with embed code
    if youtube_placeholders:
        try:
            with open(output_html_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()
            for placeholder, info in youtube_placeholders.items():
                url = info['url']
                embed_code = get_youtube_embed_code(url)
                if embed_code:
                    # Pandoc converts the markdown link to an anchor tag like:
                    # <a href="url">PLACEHOLDER</a>
                    # Replace this with the YouTube embed code.
                    pattern = r'<a\s+href="' + re.escape(url) + r'">' + re.escape(placeholder) + r'</a>'
                    html_content = re.sub(pattern, embed_code, html_content)
            with open(output_html_path, 'w', encoding='utf-8') as html_file:
                html_file.write(html_content)
        except Exception as e:
            print(f"Error during post-processing YouTube links in {output_html_path}: {e}")

    # Get the creation date of the source file
    stat_info = os.stat(file_path)
    # For systems where st_birthtime is not available, fallback to st_mtime
    creation_time = getattr(stat_info, 'st_birthtime', stat_info.st_mtime)
    formatted_time = datetime.fromtimestamp(creation_time).strftime('%m/%d/%Y %H:%M:%S')

    # Change the creation date of the output file to match the source file
    if platform.system() == 'Darwin':  # macOS
        command = ['SetFile', '-d', formatted_time, output_html_path]
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error changing creation date: {e}")
    elif platform.system() == 'Windows':
        try:
            import win32_setfiletime
            # Convert formatted_time back to a timestamp
            creation_timestamp = datetime.strptime(formatted_time, '%m/%d/%Y %H:%M:%S').timestamp()
            # Set creation, modified, and access times to the same value
            win32_setfiletime.setctime(output_html_path, creation_timestamp)
            win32_setfiletime.setmtime(output_html_path, creation_timestamp)
            win32_setfiletime.setatime(output_html_path, creation_timestamp)
        except ImportError:
            print("You need to install pywin32. Run 'pip install pywin32' and then 'pip install win32-setfiletime'")
        except Exception as e:
            print(f"Error changing creation date: {e}")
    else:
        print("Unsupported OS")


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
    # Check if pandoc is installed
    if not check_pandoc_installed():
        sys.exit(1)
        
    current_file = os.path.realpath(__file__)
    current_folder = os.path.dirname(current_file)
    template_file = current_folder + '/' + template

    # Check if error file exists, then remove it
    err_file = "error.txt"
    if os.path.exists(err_file):
        try:
            os.remove(err_file)
        except Exception as e:
            print(f"Error removing {err_file}: {e}")
            exit(1)

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

