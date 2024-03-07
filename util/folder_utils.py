import os


def folder_exists(folder_path, folder_name):
    """Check if a specific folder exists inside the given path."""
    full_path = os.path.join(folder_path, folder_name)
    return os.path.isdir(full_path)


def folder_empty(folder_path):
    """Check if the given folder is empty, ignoring .DS_Store file."""
    for item in os.listdir(folder_path):
        if item.lower() != ".ds_store":
            return False
    return True


def remove_trailing_slash(folder_path):
    """Remove trailing slash from the folder path."""
    return folder_path.rstrip('/')
