"""
Utility functions for Brain.

This module provides general utility functions used by other modules.
"""

import os
import sys
import shutil
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Union, Iterator


def ensure_directory_exists(path: str) -> None:
    """
    Description:
        Ensure a directory exists, creating it if necessary.
    
    Parameters:
        path (str): Directory path to check and create if needed.

    Returns:
        None
    """
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def copy_file_or_directory(
    source: str,
    destination: str,
    overwrite: bool = True
) -> bool:
    """
    Description:
        Copy a file or directory from source to destination.
    
    Parameters:
        source (str): Source path to copy from.
        destination (str): Destination path to copy to.
        overwrite (bool): Whether to overwrite existing files (default: True).
    
    Returns:
        success (bool): True if successful, False otherwise.
    """
    # --------------------------------------------------------------
    # STEP 1: Validate the source exists.
    # --------------------------------------------------------------
    if not os.path.exists(source):
        return False
    
    # --------------------------------------------------------------
    # STEP 2: Check if destination exists and handle overwrite flag.
    # --------------------------------------------------------------
    # Check if destination exists and we're not overwriting
    if os.path.exists(destination) and not overwrite:
        return False
    
    # --------------------------------------------------------------
    # STEP 3: Create parent directory if needed.
    # --------------------------------------------------------------
    # Create parent directory if needed
    parent_dir = os.path.dirname(destination)
    if parent_dir:
        ensure_directory_exists(parent_dir)
    
    # --------------------------------------------------------------
    # STEP 4: Copy file or directory.
    # --------------------------------------------------------------
    # Copy file or directory
    if os.path.isdir(source):
        # Remove existing directory if it exists
        if os.path.exists(destination):
            shutil.rmtree(destination)
        # Copy the entire directory
        shutil.copytree(source, destination)
    else:
        # Copy a single file
        shutil.copy2(source, destination)
    
    return True


def read_file_content(file_path: str, binary: bool = False) -> Union[str, bytes]:
    """
    Description:
        Read content from a file, either as text or binary data.
    
    Parameters:
        file_path (str): Path to the file to read.
        binary (bool): Whether to read in binary mode (default: False).
    
    Returns:
        content (Union[str, bytes]): File content as string or bytes.
    """
    mode = 'rb' if binary else 'r'
    with open(file_path, mode) as f:
        return f.read()


def write_file_content(
    file_path: str,
    content: Union[str, bytes],
    binary: bool = False
) -> None:
    """
    Description:
        Write content to a file, either as text or binary data.
    
    Parameters:
        file_path (str): Path to the file to write.
        content (Union[str, bytes]): Content to write to the file.
        binary (bool): Whether to write in binary mode (default: False).
    
    Returns:
        None
    """
    # --------------------------------------------------------------
    # STEP 1: Create parent directory if needed.
    # --------------------------------------------------------------
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        ensure_directory_exists(parent_dir)
    
    # --------------------------------------------------------------
    # STEP 2: Write content to file.
    # --------------------------------------------------------------
    # Determine the appropriate mode based on content type
    mode = 'wb' if binary else 'w'
    with open(file_path, mode) as f:
        f.write(content)


def is_binary_file(file_path: str) -> bool:
    """
    Description:
        Check if a file is binary by attempting to read it as text.
    
    Parameters:
        file_path (str): Path to the file to check.
    
    Returns:
        is_binary (bool): True if the file is binary, False if it's text.
    """
    try:
        with open(file_path, 'r') as f:
            f.read(1024)
        return False
    except UnicodeDecodeError:
        return True


def walk_files(
    directory: str,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Iterator[str]:
    """
    Description:
        Walk a directory and yield file paths matching specified patterns.
    
    Parameters:
        directory (str): Directory to walk through.
        include_patterns (Optional[List[str]]): Patterns to include (default: None, include all).
        exclude_patterns (Optional[List[str]]): Patterns to exclude (default: None, exclude none).
    
    Returns:
        file_paths (Iterator[str]): File paths relative to the directory.
    """
    import fnmatch
    
    # --------------------------------------------------------------
    # STEP 1: Walk through the directory tree.
    # --------------------------------------------------------------
    for root, dirs, files in os.walk(directory):
        # Get path relative to base directory
        rel_root = os.path.relpath(root, directory)
        
        # --------------------------------------------------------------
        # STEP 2: Process each file in the current directory.
        # --------------------------------------------------------------
        for file in files:
            rel_path = os.path.normpath(os.path.join(rel_root, file))
            
            # ===============
            # Sub step 2.1: Check exclude patterns.
            # ===============
            # Skip if excluded
            if exclude_patterns:
                excluded = False
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(rel_path, pattern):
                        excluded = True
                        break
                if excluded:
                    continue
            
            # ===============
            # Sub step 2.2: Check include patterns.
            # ===============
            # Include if matched or no include patterns
            if not include_patterns:
                yield rel_path
            else:
                for pattern in include_patterns:
                    if fnmatch.fnmatch(rel_path, pattern):
                        yield rel_path
                        break


def parse_mapping(mapping_str: str) -> Tuple[str, str, str]:
    """
    Description:
        Parse a neuron mapping string in the format "brain_id::source::destination".
    
    Parameters:
        mapping_str (str): Mapping string to parse.
    
    Returns:
        mapping (Tuple[str, str, str]): Tuple containing (brain_id, source, destination).
    
    Raises:
        ValueError: If the mapping format is invalid.
    """
    # --------------------------------------------------------------
    # STEP 1: Split and validate the mapping string.
    # --------------------------------------------------------------
    parts = mapping_str.split('::')
    if len(parts) != 3:
        # Raise error if the format is invalid
        raise ValueError(f"Invalid mapping format: {mapping_str}")
    
    return parts[0], parts[1], parts[2]


def create_temporary_directory() -> Tuple[str, Any]:
    """
    Description:
        Create a temporary directory and provide a cleanup function.
    
    Parameters:
        None
    
    Returns:
        result (Tuple[str, Any]): Tuple containing:
            - temp_dir (str): Path to the created temporary directory.
            - cleanup (function): Function to call to remove the directory.
    """
    temp_dir = tempfile.mkdtemp(prefix='brain-')
    
    def cleanup():
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    
    return temp_dir, cleanup


def find_mapping_for_neuron(
    neurons_config: Dict[str, Any],
    neuron_path: str
) -> Optional[Dict[str, str]]:
    """
    Description:
        Find the mapping configuration for a neuron file.
    
    Parameters:
        neurons_config (Dict[str, Any]): Neurons configuration dictionary.
        neuron_path (str): Path to the neuron file.
    
    Returns:
        mapping (Optional[Dict[str, str]]): Mapping if found, None otherwise.
    """
    # --------------------------------------------------------------
    # STEP 1: Normalize the neuron path.
    # --------------------------------------------------------------
    # Normalize path for consistent comparison
    neuron_path = os.path.normpath(neuron_path)
    
    # --------------------------------------------------------------
    # STEP 2: Check each mapping for a match.
    # --------------------------------------------------------------
    # Check each mapping
    for mapping in neurons_config.get('MAP', []):
        dest = mapping['destination']
        
        # ===============
        # Sub step 2.1: Handle directory mappings.
        # ===============
        if dest.endswith('/'):
            # Directory mapping - check if neuron path starts with this directory
            if neuron_path.startswith(dest):
                return mapping
        # ===============
        # Sub step 2.2: Handle file mappings.
        # ===============
        elif dest == neuron_path:
            # Exact file match
            return mapping
    
    # No mapping found
    return None


def get_brain_name_for_neuron(
    neurons_config: Dict[str, Any],
    neuron_path: str
) -> Optional[str]:
    """
    Description:
        Get the brain name for a neuron file from the configuration.
    
    Parameters:
        neurons_config (Dict[str, Any]): Neurons configuration dictionary.
        neuron_path (str): Path to the neuron file.
    
    Returns:
        brain_name (Optional[str]): Brain name if found, None otherwise.
    """
    mapping = find_mapping_for_neuron(neurons_config, neuron_path)
    if mapping:
        return mapping['brain_id']
    return None


def format_size(size_bytes: int) -> str:
    """
    Description:
        Format a size in bytes to a human-readable string with appropriate units.
    
    Parameters:
        size_bytes (int): Size in bytes to format.
    
    Returns:
        formatted_size (str): Formatted size string with units (B, KB, MB, GB).
    """
    # --------------------------------------------------------------
    # STEP 1: Convert bytes to appropriate unit based on size.
    # --------------------------------------------------------------
    if size_bytes < 1024:
        # Size in bytes
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        # Size in kilobytes
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        # Size in megabytes
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        # Size in gigabytes
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"