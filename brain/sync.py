"""
Neuron synchronization for Brain.

This module provides functions for synchronizing neurons between
brain repositories and consumer repositories.
"""

import os
import sys 
import shutil
import tempfile
import hashlib
import difflib
import subprocess
import re 
from urllib.parse import urlparse, unquote 
from typing import Dict, List, Any, Optional, Union

try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    parse_version = None 
    InvalidVersion = type('InvalidVersion', (Exception,), {}) # type: ignore


from brain.git import (
    is_bare_repo,
    get_repo_root, 
    is_git_repo, 
    is_file_tracked, 
    is_file_modified, 
    get_file_hash,    
    get_changed_files,
    run_git_command,
    temp_clone_repo,
    GitError,
    _debug_log_git 
)

# --- DEBUGGING ---
ENABLE_SYNC_DEBUG_LOGGING = True

def _debug_log_sync(message: str):
    """
    Description:
        Logs debug messages related to neuron synchronization when debug logging is enabled.
    
    Parameters:
        message (str): The debug message to log.

    Returns:
        None
    """
    if ENABLE_SYNC_DEBUG_LOGGING:
        print(f"[SYNC_DEBUG] {message}", file=sys.stderr, flush=True)
# --- END DEBUGGING ---


class SyncError(Exception):
    """Exception raised for errors during neuron synchronization."""
    pass


def calculate_file_hash(file_path: str) -> str:
    """
    Description:
        Calculate the SHA-256 hash of a file. Not a Git blob hash.
    
    Parameters:
        file_path (str): Path to the file to hash.

    Returns:
        hex_digest (str): The SHA-256 hash of the file as a hexadecimal string.
    """
    _debug_log_sync(f"Calculating SHA256 hash for: {file_path}")
    hasher = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            buf = f.read(65536) 
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        hex_digest = hasher.hexdigest()
        _debug_log_sync(f"SHA256 Hash for {file_path}: {hex_digest}")
        return hex_digest
    except IOError as e:
        _debug_log_sync(f"IOError calculating SHA256 hash for {file_path}: {e}")
        raise SyncError(f"Could not calculate SHA256 hash for {file_path}: {e}") from e

def _try_decode_utf8(data_bytes: bytes) -> Optional[str]:
    """
    Description:
        Attempts to decode bytes as UTF-8.
    
    Parameters:
        data_bytes (bytes): The bytes to decode as UTF-8.

    Returns:
        decoded_string (Optional[str]): Decoded UTF-8 string or None if decoding fails.
    """
    try:
        return data_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return None

def detect_conflicts(local_content_orig: Union[str, bytes], brain_content_orig: Union[str, bytes]) -> bool:
    """
    Description:
        Detect conflicts between local and brain versions of a neuron.
        Compares byte content first. If different, and both are decodable as UTF-8, compares string content.
    
    Parameters:
        local_content_orig (Union[str, bytes]): Content of the local version of a neuron.
        brain_content_orig (Union[str, bytes]): Content of the brain version of a neuron.

    Returns:
        has_conflict (bool): True if a conflict is detected, False otherwise.
    """
    _debug_log_sync(f"Detecting conflicts: local_type={type(local_content_orig)}, brain_type={type(brain_content_orig)}")

    # Convert to bytes if content is str
    local_bytes = local_content_orig if type(local_content_orig) is bytes else local_content_orig.encode('utf-8')
    brain_bytes = brain_content_orig if type(brain_content_orig) is bytes else brain_content_orig.encode('utf-8')

    # Compare byte content
    if local_bytes == brain_bytes:
        _debug_log_sync("Byte comparison shows content is identical. No conflict.")
        return False 

    # Try to decode as UTF-8 for text comparison
    local_str_attempt = _try_decode_utf8(local_bytes)
    brain_str_attempt = _try_decode_utf8(brain_bytes)

    # If both are valid UTF-8, compare as strings
    if local_str_attempt is not None and brain_str_attempt is not None:
        is_str_conflict = local_str_attempt != brain_str_attempt
        _debug_log_sync(f"UTF-8 string comparison result: conflict={is_str_conflict}")
        return is_str_conflict 
    else:
        _debug_log_sync("Conflict: Byte content differs, and at least one part is not valid UTF-8 text (treated as binary difference).")
        return True


def handle_conflicts(
    file_path: str, 
    local_content_bytes: bytes, 
    brain_content_bytes: bytes,
    strategy: str = 'prompt'
) -> Dict[str, Any]:
    """
    Description:
        Handle conflicts between local and brain versions of a neuron.
    
    Parameters:
        file_path (str): Path to the neuron file with conflicts.
        local_content_bytes (bytes): Content of the local version of the neuron.
        brain_content_bytes (bytes): Content of the brain version of the neuron.
        strategy (str): Conflict resolution strategy: 'prompt', 'prefer_brain', or 'prefer_local'.

    Returns:
        resolution (Dict[str, Any]): Dictionary with 'resolution' key ('brain', 'local', 'merged', or
                                     'merged_with_conflicts') and 'content' key (bytes of the chosen/merged version).
    """
    _debug_log_sync(f"Handling conflict for: {file_path}, Strategy: {strategy}")
    
    # --------------------------------------------------------------
    # STEP 1: Determine if file is binary or text for display purposes.
    # --------------------------------------------------------------
    local_str_display: Optional[str] = _try_decode_utf8(local_content_bytes)
    brain_str_display: Optional[str] = _try_decode_utf8(brain_content_bytes)
    
    is_effectively_binary = local_str_display is None or brain_str_display is None
    _debug_log_sync(f"File '{file_path}' effectively binary for diffing: {is_effectively_binary}")

    # --------------------------------------------------------------
    # STEP 2: Handle automatic strategies without prompting.
    # --------------------------------------------------------------
    if strategy == 'prefer_brain':
        _debug_log_sync(f"Conflict resolution for '{file_path}': prefer_brain.")
        return {'resolution': 'brain', 'content': brain_content_bytes}
    elif strategy == 'prefer_local':
        _debug_log_sync(f"Conflict resolution for '{file_path}': prefer_local.")
        return {'resolution': 'local', 'content': local_content_bytes}
    elif strategy == 'prompt':
        # Check for non-interactive environment
        if not sys.stdin.isatty(): 
            _debug_log_sync(f"Non-interactive environment for neuron '{file_path}'. Defaulting to 'prefer_brain' for conflict resolution.")
            return {'resolution': 'brain', 'content': brain_content_bytes}

        # --------------------------------------------------------------
        # STEP 3: Handle interactive prompt strategy by showing diff and getting user input.
        # --------------------------------------------------------------
        _debug_log_sync(f"Prompting user for conflict resolution for '{file_path}'.")
        print(f"\nConflict detected in neuron: {file_path}")

        # ===============
        # Sub step 3.1: Display text diff if possible.
        # ===============
        if not is_effectively_binary and local_str_display is not None and brain_str_display is not None: 
            _debug_log_sync(f"Displaying text diff for '{file_path}'.")
            print("Diff between local and brain versions (local vs. brain):")
            diff = difflib.unified_diff(
                local_str_display.splitlines(keepends=True),
                brain_str_display.splitlines(keepends=True),
                fromfile=f"LOCAL: {file_path}", tofile=f"BRAIN: {file_path}"
            )
            diff_text = ''.join(diff)
            print(diff_text if diff_text.strip() else "(No textual differences shown, possibly line endings or only whitespace differences)")
        else:
            _debug_log_sync(f"'{file_path}' treated as binary for diff, cannot show text diff.")
            print("Binary file conflict or one version is not valid UTF-8. Local and brain versions differ.")
        
        # ===============
        # Sub step 3.2: Process user choice with temporary file handling for merges.
        # ===============
        temp_file_paths_to_clean: List[str] = []
        try:
            while True:
                choices_str = "[b]rain, [l]ocal"
                if not is_effectively_binary: choices_str += ", [m]erge (using git merge-file)"
                
                try:
                    _debug_log_sync(f"Waiting for user input for '{file_path}': {choices_str}?")
                    choice = input(f"Choose resolution for '{file_path}': {choices_str}? ").strip().lower()
                    _debug_log_sync(f"User chose: '{choice}' for '{file_path}'.")
                except EOFError: 
                    _debug_log_sync(f"EOFError on input for '{file_path}'. Defaulting to 'prefer_brain'.")
                    return {'resolution': 'brain', 'content': brain_content_bytes}

                if choice.startswith('b'): return {'resolution': 'brain', 'content': brain_content_bytes}
                if choice.startswith('l'): return {'resolution': 'local', 'content': local_content_bytes}
                
                # Handle merge option for text files
                if choice.startswith('m') and not is_effectively_binary and \
                   local_str_display is not None and brain_str_display is not None: 
                    _debug_log_sync(f"Attempting merge for text file '{file_path}'.")
                    
                    # Create temporary files for merge operation
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.local', delete=False, encoding='utf-8') as local_tf, \
                         tempfile.NamedTemporaryFile(mode='w', suffix='.base', delete=False, encoding='utf-8') as base_tf, \
                         tempfile.NamedTemporaryFile(mode='w', suffix='.brain', delete=False, encoding='utf-8') as brain_tf, \
                         tempfile.NamedTemporaryFile(mode='w+', delete=False, encoding='utf-8') as merged_target_tf: 
                        
                        local_tf_path, base_tf_path, brain_tf_path, merged_target_tf_path = \
                            local_tf.name, base_tf.name, brain_tf.name, merged_target_tf.name
                        
                        temp_file_paths_to_clean.extend([local_tf_path, base_tf_path, brain_tf_path, merged_target_tf_path])

                        _debug_log_sync(f"Writing temp files for merge: local='{local_tf_path}', base='{base_tf_path}', brain='{brain_tf_path}'")
                        local_tf.write(local_str_display)
                        base_tf.write(local_str_display) 
                        brain_tf.write(brain_str_display)
                    
                    # Prepare the merge target
                    shutil.copy2(local_tf_path, merged_target_tf_path)
                    _debug_log_sync(f"Copied local content to merge target: '{merged_target_tf_path}'")

                    # Run git merge-file to perform the merge
                    _debug_log_sync(f"Running git merge-file for '{file_path}'. Target: '{merged_target_tf_path}'")
                    
                    process = subprocess.run(
                        ['git', 'merge-file', '-L', f'LOCAL ({file_path})', '-L', 'BASE (local)', '-L', f'BRAIN ({file_path})', 
                         merged_target_tf_path, base_tf_path, brain_tf_path],
                        capture_output=True, text=True, encoding='utf-8' 
                    )
                    _debug_log_sync(f"git merge-file for '{file_path}' completed. Return code: {process.returncode}")
                    if process.stdout: _debug_log_sync(f"merge-file stdout: {process.stdout}")
                    if process.stderr: _debug_log_sync(f"merge-file stderr: {process.stderr}")
                    
                    # Read the merge result
                    with open(merged_target_tf_path, 'rb') as f_merged_read_bytes: 
                        merged_content_bytes = f_merged_read_bytes.read()
                    _debug_log_sync(f"Read {len(merged_content_bytes)} bytes from merged file '{merged_target_tf_path}'.")
                    
                    if process.returncode == 0: 
                        _debug_log_sync(f"Merge successful for '{file_path}' (no conflicts from git merge-file).")
                        return {'resolution': 'merged', 'content': merged_content_bytes}
                    else: 
                        _debug_log_sync(f"Merge for '{file_path}' resulted in conflicts (markers added by git merge-file).")
                        print("Merge resulted in conflicts (markers added by git merge-file). Please resolve them in the file.")
                        return {'resolution': 'merged_with_conflicts', 'content': merged_content_bytes}
                elif choice.startswith('m'): 
                     print("Merge option is only available for text files. Please choose 'brain' or 'local'.")
                else: 
                    print("Invalid choice. Please enter a valid option.")
        finally: 
            # Clean up temporary files
            for path_to_clean in temp_file_paths_to_clean:
                if os.path.exists(path_to_clean):
                    _debug_log_sync(f"Cleaning up temp merge file: {path_to_clean}")
                    try:
                        os.unlink(path_to_clean)
                    except OSError as e_unlink:
                         _debug_log_sync(f"Error unlinking temp file {path_to_clean}: {e_unlink}")
    
    # Default fallback if strategy is unknown or prompt failed
    _debug_log_sync(f"Unknown conflict strategy '{strategy}' for '{file_path}', or prompt failed. Defaulting to 'brain' version.")
    return {'resolution': 'brain', 'content': brain_content_bytes}


def parse_requirements(content: str) -> Dict[str, str]:
    """
    Description:
        Parses requirements.txt content into a dictionary mapping package names to version specifications.
    
    Parameters:
        content (str): Content of the requirements.txt file.

    Returns:
        dependencies (Dict[str, str]): Dictionary mapping package names to version specifications.
    """
    dependencies: Dict[str, str] = {}
    req_pattern = re.compile(
        r"^\s*([a-zA-Z0-9._-]+)"         
        r"(?:\s*(==)\s*([^#;\s]+))?"     
        r"(?:\s*[!<>]=?\s*[^#;\s]+)?"    
        r"(?:\s*;[^#]*)?"                
        r"(?:\s*#.*)?"                   
        r"\s*$"
    )
    for line_num, raw_line in enumerate(content.splitlines()):
        line = raw_line.strip()
        if not line or line.startswith('#'): continue 

        match = req_pattern.match(line)
        if not match: 
            _debug_log_sync(f"Line {line_num+1} in requirements not matched by regex: '{raw_line}'")
            simple_name_match = re.match(r"^\s*([a-zA-Z0-9._-]+)", line)
            if simple_name_match:
                 pkg_name_simple = simple_name_match.group(1)
                 if pkg_name_simple not in dependencies: 
                     dependencies[pkg_name_simple] = "" 
            continue

        pkg_name, version_operator, version_str = match.group(1), match.group(2), match.group(3)
        
        actual_version = ""
        if version_operator == '==' and version_str:
            actual_version = version_str.strip()
        
        dependencies[pkg_name] = actual_version 
    _debug_log_sync(f"Parsed requirements: {dependencies}")
    return dependencies

def merge_requirements(repo_requirements_content: str, neuron_requirements_content: str) -> str:
    """
    Description:
        Merges neuron requirements into repository requirements, upgrading versions when appropriate.
    
    Parameters:
        repo_requirements_content (str): Content of the repository's requirements.txt file.
        neuron_requirements_content (str): Content of the neuron's requirements.txt file.

    Returns:
        merged_content (str): The merged requirements content as a string.
    """
    _debug_log_sync("Merging requirements files.")
    # Parse both requirement files
    repo_deps = parse_requirements(repo_requirements_content)
    neuron_deps = parse_requirements(neuron_requirements_content)
    
    merged_deps = repo_deps.copy()

    # --------------------------------------------------------------
    # STEP 1: Process each dependency from the neuron requirements.
    # --------------------------------------------------------------
    for name, neuron_version_str in neuron_deps.items():
        repo_version_str = merged_deps.get(name)
        
        # Case 1: New dependency not in repo requirements
        if repo_version_str is None: 
            merged_deps[name] = neuron_version_str
            _debug_log_sync(f"ReqMerge: Adding new '{name}=={neuron_version_str}' from neuron.")
        else: 
            # Case 2: Neuron version is non-specific
            if not neuron_version_str: 
                _debug_log_sync(f"ReqMerge: Neuron version for '{name}' is non-specific ('{neuron_version_str}'), keeping repo version ('{repo_version_str}').")
                continue
            
            # Case 3: Repo version is non-specific
            if not repo_version_str: 
                merged_deps[name] = neuron_version_str
                _debug_log_sync(f"ReqMerge: Repo version for '{name}' was non-specific, updating to neuron's '{neuron_version_str}'.")
                continue
            
            # --------------------------------------------------------------
            # STEP 2: Compare versions and take the higher one.
            # --------------------------------------------------------------
            # Both repo and neuron have '==' version strings. Compare them.
            if parse_version:
                try:
                    neuron_ver = parse_version(neuron_version_str)
                    repo_ver = parse_version(repo_version_str)
                    if neuron_ver > repo_ver:
                        merged_deps[name] = neuron_version_str
                        _debug_log_sync(f"ReqMerge: Upgrading '{name}' from '{repo_version_str}' to '{neuron_version_str}' (parsed).")
                    elif neuron_ver < repo_ver:
                         _debug_log_sync(f"ReqMerge: Neuron version for '{name}' ('{neuron_version_str}') is older than repo version ('{repo_version_str}') (parsed). Keeping repo version.")
                    # else: versions are equal, no change needed.
                except InvalidVersion:
                    # One or both versions are not PEP 440 compliant (e.g., direct URLs, local paths).
                    # In this case, if they are different as strings, prefer the neuron's version.
                    _debug_log_sync(f"ReqMerge: InvalidVersion for '{name}' (repo:'{repo_version_str}', neuron:'{neuron_version_str}'). Comparing as strings.")
                    if repo_version_str != neuron_version_str:
                        merged_deps[name] = neuron_version_str
                        _debug_log_sync(f"ReqMerge: Taking neuron version for '{name}' ('{neuron_version_str}') due to unparseable/differing versions.")
            elif repo_version_str != neuron_version_str: # Fallback if packaging.parse_version is not available
                merged_deps[name] = neuron_version_str
                _debug_log_sync(f"ReqMerge: packaging.version not available. Taking neuron version for '{name}' ('{neuron_version_str}') as strings differ from repo's ('{repo_version_str}').")

    # --------------------------------------------------------------
    # STEP 3: Generate the merged requirements file content.
    # --------------------------------------------------------------
    merged_lines = []
    for name, version in sorted(merged_deps.items()):
        if version: 
            merged_lines.append(f"{name}=={version}")
        else: 
            # This case means the original requirement was just a name (e.g. "package")
            # or had other specifiers (e.g. "package>=1.0") which parse_requirements currently stores as ""
            # For robust reconstruction, one would need to store the original line or use a more
            # sophisticated Requirement object. For now, just the name is outputted.
            merged_lines.append(name)
            
    final_content = "\n".join(merged_lines) + ("\n" if merged_lines else "") 
    _debug_log_sync(f"Merged requirements content:\n{final_content.strip()}")
    return final_content


def sync_neuron(
    neurons_config: Dict[str, Any],
    brain_id: str,
    source_path: str, 
    dest_path: str,   
    repo_path: str = '.' 
) -> Dict[str, Any]:
    """
    Description:
        Synchronizes a neuron from a brain repository to a consumer repository.
    
    Parameters:
        neurons_config (Dict[str, Any]): Configuration for neurons.
        brain_id (str): Identifier for the brain repository.
        source_path (str): Path to the neuron in the brain repository.
        dest_path (str): Path where the neuron should be placed in the consumer repository.
        repo_path (str): Path to the consumer repository. Defaults to current directory.

    Returns:
        result (Dict[str, Any]): Dictionary containing synchronization results with keys for mapping,
                                 requirements_merged, status, action, and message.
    """
    _debug_log_sync(f"Starting sync_neuron for: Brain='{brain_id}', Source='{source_path}', Dest='{dest_path}', RepoPath='{os.path.abspath(repo_path)}'")
    
    # --------------------------------------------------------------
    # STEP 1: Initialize the result dictionary and validate brain ID.
    # --------------------------------------------------------------
    result_base: Dict[str, Any] = {
        'mapping': {'brain_id': brain_id, 'source': source_path, 'destination': dest_path},
        'requirements_merged': False, 'status': 'error', 'action': None, 'message': ''
    }

    brains = neurons_config.get('BRAINS', {})
    if brain_id not in brains:
        result_base['message'] = f"Unknown brain ID: '{brain_id}' in .neurons configuration."
        _debug_log_sync(f"Sync failed: {result_base['message']}")
        return result_base
    
    brain_cfg = brains[brain_id]
    brain_temp_dir: Optional[str] = None 

    # --------------------------------------------------------------
    # STEP 2: Determine sync policy and conflict resolution strategy.
    # --------------------------------------------------------------
    sync_policy = neurons_config.get('SYNC_POLICY', {})
    conflict_strategy = sync_policy.get('CONFLICT_STRATEGY', 'prompt').lower()
    allow_local_modifications = sync_policy.get('ALLOW_LOCAL_MODIFICATIONS', False)

    # Determine effective conflict resolution strategy
    if not allow_local_modifications and conflict_strategy == 'prompt':
        _debug_log_sync(f"Policy Override: ALLOW_LOCAL_MODIFICATIONS is false and CONFLICT_STRATEGY is 'prompt'. Effective strategy becomes 'prefer_brain' for neuron '{dest_path}'.")
        effective_conflict_strategy = 'prefer_brain'
    else:
        effective_conflict_strategy = conflict_strategy
    _debug_log_sync(f"Effective sync policy for '{dest_path}': ConflictStrategy='{effective_conflict_strategy}', AllowLocalMods='{allow_local_modifications}'")

    try:
        # --------------------------------------------------------------
        # STEP 3: Clone the brain repository and locate the source neuron.
        # --------------------------------------------------------------
        remote_url = brain_cfg.get('REMOTE')
        if not remote_url:
            raise SyncError(f"REMOTE URL for brain '{brain_id}' is not defined.")
        branch = brain_cfg.get('BRANCH') 
        _debug_log_sync(f"Attempting to clone brain for neuron sync: URL='{remote_url}', Branch='{branch or 'default'}'")
        brain_temp_dir = temp_clone_repo(remote_url, branch) 
        _debug_log_sync(f"Brain '{brain_id}' cloned to temp dir for sync: {brain_temp_dir}")
        
        brain_source_full_path = os.path.join(brain_temp_dir, source_path)
        _debug_log_sync(f"Full path to source in brain clone: {brain_source_full_path}")

        if not os.path.exists(brain_source_full_path):
            result_base['message'] = f"Source path '{source_path}' not found in brain '{brain_id}' (at URL '{remote_url}', branch '{branch or 'default'}')."
            _debug_log_sync(f"Sync failed: {result_base['message']}")
            raise SyncError(result_base['message'])

        # --------------------------------------------------------------
        # STEP 4: Find and read neuron-specific requirements file if it exists.
        # --------------------------------------------------------------
        brain_neuron_requirements_content = ""
        neuron_req_filename_in_brain = "" 
        
        if os.path.isdir(brain_source_full_path):
            # Check for requirements.txt in neuron directory
            potential_req_path_in_brain_neuron_dir = os.path.join(brain_source_full_path, "requirements.txt")
            if os.path.isfile(potential_req_path_in_brain_neuron_dir):
                 neuron_req_filename_in_brain = "requirements.txt" 
                 _debug_log_sync(f"Found neuron-specific requirements file in brain dir neuron: {potential_req_path_in_brain_neuron_dir}")
                 with open(potential_req_path_in_brain_neuron_dir, 'r', encoding='utf-8') as f_req:
                     brain_neuron_requirements_content = f_req.read()
            else:
                # Check for alternate naming pattern: <dirname>requirements.txt
                dir_base_name = os.path.basename(os.path.normpath(brain_source_full_path))
                alt_req_filename = f"{dir_base_name}requirements.txt"
                alt_req_path = os.path.join(brain_source_full_path, alt_req_filename)
                if os.path.isfile(alt_req_path):
                    neuron_req_filename_in_brain = alt_req_filename
                    _debug_log_sync(
                        f"Found neuron-specific requirements file (alt pattern) in brain dir neuron: {alt_req_path}")
                    with open(alt_req_path, 'r', encoding='utf-8') as f_req:
                        brain_neuron_requirements_content = f_req.read()
        else: 
            _debug_log_sync(f"Neuron source '{brain_source_full_path}' is a file. Neuron-specific requirements.txt merge logic primarily applies to requirements.txt inside directory neurons.")
            pass

        # --------------------------------------------------------------
        # STEP 5: Prepare destination path in consumer repository.
        # --------------------------------------------------------------
        consumer_dest_full_path = os.path.abspath(os.path.join(repo_path, dest_path)) 
        _debug_log_sync(f"Full path to destination in consumer: {consumer_dest_full_path}")
        
        consumer_dest_parent_dir = os.path.dirname(consumer_dest_full_path)
        if consumer_dest_parent_dir: 
            _debug_log_sync(f"Ensuring consumer parent directory exists: {consumer_dest_parent_dir}")
            os.makedirs(consumer_dest_parent_dir, exist_ok=True)
        
        consumer_dest_exists = os.path.exists(consumer_dest_full_path)
        _debug_log_sync(f"Consumer destination '{consumer_dest_full_path}' exists: {consumer_dest_exists}")
        
        action_taken = 'unchanged' 

        # --------------------------------------------------------------
        # STEP 6: Synchronize the neuron based on its type (directory or file).
        # --------------------------------------------------------------
        if os.path.isdir(brain_source_full_path): 
            # ===============
            # Sub step 6.1: Handle directory neuron synchronization.
            # ===============
            _debug_log_sync(f"Source '{source_path}' is a directory. Starting directory sync.")
            if not consumer_dest_exists:
                _debug_log_sync(f"Consumer dest dir '{consumer_dest_full_path}' does not exist. Copying tree from brain source.")
                shutil.copytree(brain_source_full_path, consumer_dest_full_path, dirs_exist_ok=False) 
                action_taken = 'added'
            elif not os.path.isdir(consumer_dest_full_path): 
                _debug_log_sync(f"Consumer dest '{consumer_dest_full_path}' exists but is not a dir. Removing and copying tree.")
                os.remove(consumer_dest_full_path)
                shutil.copytree(brain_source_full_path, consumer_dest_full_path, dirs_exist_ok=False)
                action_taken = 'updated'
            else: 
                _debug_log_sync(f"Consumer dest dir '{consumer_dest_full_path}' exists. Merging/updating content.")
                dir_content_changed_overall = False
                for root_in_brain, dirs_in_brain_subdir, files_in_brain_subdir in os.walk(brain_source_full_path):
                    rel_root_to_neuron_source = os.path.relpath(root_in_brain, brain_source_full_path)
                    
                    consumer_equiv_of_root = os.path.join(consumer_dest_full_path, rel_root_to_neuron_source)
                    if rel_root_to_neuron_source == '.': 
                        consumer_equiv_of_root = consumer_dest_full_path
                    
                    # Create subdirectories in consumer if they don't exist
                    for dir_name_in_brain in dirs_in_brain_subdir:
                        consumer_equiv_subdir = os.path.join(consumer_equiv_of_root, dir_name_in_brain)
                        if not os.path.exists(consumer_equiv_subdir):
                            _debug_log_sync(f"DirSync: Creating subdir {consumer_equiv_subdir}")
                            os.makedirs(consumer_equiv_subdir, exist_ok=True)
                            dir_content_changed_overall = True 

                    # Process files in the brain directory
                    for file_name_in_brain in files_in_brain_subdir:
                        # Skip direct copy of neuron requirements file as it's handled separately
                        if root_in_brain == brain_source_full_path and file_name_in_brain == neuron_req_filename_in_brain and brain_neuron_requirements_content:
                            _debug_log_sync(f"DirSync: Skipping neuron's own requirements file '{file_name_in_brain}' from direct copy as its content is merged.")
                            continue

                        brain_file_item_path = os.path.join(root_in_brain, file_name_in_brain)
                        consumer_file_item_path = os.path.join(consumer_equiv_of_root, file_name_in_brain)
                        _debug_log_sync(f"DirSync: Processing brain file '{brain_file_item_path}' -> consumer file '{consumer_file_item_path}'")
                        
                        with open(brain_file_item_path, 'rb') as bf_item: brain_item_content_bytes = bf_item.read()
                        
                        if os.path.exists(consumer_file_item_path):
                            if os.path.isdir(consumer_file_item_path): 
                                # File in brain, but directory in consumer - replace directory with file
                                _debug_log_sync(f"DirSync: Path conflict. Brain item '{brain_file_item_path}' is file, consumer item '{consumer_file_item_path}' is dir. Removing consumer dir.")
                                shutil.rmtree(consumer_file_item_path)
                                with open(consumer_file_item_path, 'wb') as cf_write: cf_write.write(brain_item_content_bytes)
                                dir_content_changed_overall = True
                            else: 
                                # File exists in both places - check for conflicts
                                _debug_log_sync(f"DirSync: Consumer file '{consumer_file_item_path}' exists. Checking for conflicts.")
                                with open(consumer_file_item_path, 'rb') as cf_item: local_item_content_bytes = cf_item.read()
                                if detect_conflicts(local_item_content_bytes, brain_item_content_bytes):
                                    _debug_log_sync(f"DirSync: Conflict detected for '{consumer_file_item_path}'. Effective Policy: Strategy='{effective_conflict_strategy}'.")
                                    item_rel_path_for_display = os.path.relpath(consumer_file_item_path, os.path.abspath(repo_path))
                                    resolution = handle_conflicts(item_rel_path_for_display, local_item_content_bytes, brain_item_content_bytes, effective_conflict_strategy)
                                    
                                    _debug_log_sync(f"DirSync: Conflict resolution for '{item_rel_path_for_display}': {resolution['resolution']}. Writing content.")
                                    if resolution['content'] != local_item_content_bytes: 
                                        with open(consumer_file_item_path, 'wb') as cf_write: cf_write.write(resolution['content'])
                                        dir_content_changed_overall = True
                                else: _debug_log_sync(f"DirSync: No conflict for '{consumer_file_item_path}'. Content identical.")
                        else: 
                            # File doesn't exist in consumer - copy it
                            _debug_log_sync(f"DirSync: Consumer file '{consumer_file_item_path}' does not exist. Copying from brain.")
                            os.makedirs(os.path.dirname(consumer_file_item_path), exist_ok=True)
                            with open(consumer_file_item_path, 'wb') as cf_write: cf_write.write(brain_item_content_bytes)
                            dir_content_changed_overall = True
                
                if dir_content_changed_overall: action_taken = 'updated'

        else: 
            # ===============
            # Sub step 6.2: Handle file neuron synchronization.
            # ===============
            _debug_log_sync(f"Source '{source_path}' is a file. Starting file sync.")
            with open(brain_source_full_path, 'rb') as bf: brain_file_bytes = bf.read()
            _debug_log_sync(f"Read {len(brain_file_bytes)} bytes from brain source file '{brain_source_full_path}'.")

            # For single-file neurons, check for adjacent requirements file
            potential_req_path_for_file_neuron = f"{brain_source_full_path}requirements.txt"
            if os.path.isfile(potential_req_path_for_file_neuron):
                _debug_log_sync(
                    f"Found neuron-specific requirements file for single-file neuron: {potential_req_path_for_file_neuron}")
                try:
                    with open(potential_req_path_for_file_neuron, 'r', encoding='utf-8') as f_req:
                        brain_neuron_requirements_content = f_req.read()
                except IOError as e_req_read:
                    _debug_log_sync(
                        f"IOError reading neuron-specific requirements for single-file neuron at {potential_req_path_for_file_neuron}: {e_req_read}")

            if consumer_dest_exists:
                if os.path.isdir(consumer_dest_full_path): 
                    # Type mismatch: directory in consumer but file in brain
                    _debug_log_sync(f"Consumer destination '{consumer_dest_full_path}' is a directory, but brain source is file. Removing consumer dir.")
                    shutil.rmtree(consumer_dest_full_path)
                    _debug_log_sync(f"Writing brain file content to '{consumer_dest_full_path}'.")
                    with open(consumer_dest_full_path, 'wb') as cf_write: cf_write.write(brain_file_bytes)
                    action_taken = 'updated'
                else: 
                    # File exists in both places - check for conflicts
                    _debug_log_sync(f"Consumer destination '{consumer_dest_full_path}' is a file. Reading local content.")
                    with open(consumer_dest_full_path, 'rb') as cf: local_file_bytes = cf.read()
                    _debug_log_sync(f"Read {len(local_file_bytes)} bytes from local consumer file '{consumer_dest_full_path}'.")
                    
                    if detect_conflicts(local_file_bytes, brain_file_bytes):
                        _debug_log_sync(f"Conflict detected for file '{dest_path}'. Effective Policy: Strategy='{effective_conflict_strategy}'.")
                        dest_rel_path_for_display = os.path.relpath(consumer_dest_full_path, os.path.abspath(repo_path))
                        resolution = handle_conflicts(dest_rel_path_for_display, local_file_bytes, brain_file_bytes, effective_conflict_strategy)
                        _debug_log_sync(f"Conflict resolution for '{dest_rel_path_for_display}': {resolution['resolution']}. Writing content.")
                        if resolution['content'] != local_file_bytes: 
                            with open(consumer_dest_full_path, 'wb') as cf_write: cf_write.write(resolution['content'])
                            action_taken = 'updated'
                    else:
                        _debug_log_sync(f"No conflict detected for file '{dest_path}'. Content is identical.")
                        action_taken = 'unchanged' 
            else: 
                # File doesn't exist in consumer - copy it
                _debug_log_sync(f"Consumer destination file '{consumer_dest_full_path}' does not exist. Writing brain content.")
                with open(consumer_dest_full_path, 'wb') as cf_write: cf_write.write(brain_file_bytes)
                action_taken = 'added'
        
        # Update result with success status
        result_base.update({'status': 'success', 'action': action_taken})
        _debug_log_sync(f"sync_neuron for '{dest_path}' status: {result_base['status']}, action: {result_base['action']}.")

        # --------------------------------------------------------------
        # STEP 7: Merge neuron requirements into consumer's main requirements.txt if applicable.
        # --------------------------------------------------------------
        if brain_neuron_requirements_content: 
            _debug_log_sync(f"Neuron '{source_path}' has requirements. Merging into consumer's main requirements.txt.")
            consumer_main_req_path = os.path.join(os.path.abspath(repo_path), 'requirements.txt')
            consumer_main_req_content = ""
            if os.path.exists(consumer_main_req_path):
                _debug_log_sync(f"Reading existing consumer requirements from '{consumer_main_req_path}'.")
                with open(consumer_main_req_path, 'r', encoding='utf-8') as f_main_req:
                    consumer_main_req_content = f_main_req.read()
            
            merged_req_content = merge_requirements(consumer_main_req_content, brain_neuron_requirements_content)
            
            if merged_req_content.strip() != consumer_main_req_content.strip():
                 result_base['requirements_merged'] = True
                 _debug_log_sync(f"Consumer requirements.txt ('{consumer_main_req_path}') changed after merge from neuron '{source_path}'.")
            else:
                 _debug_log_sync(f"Consumer requirements.txt content unchanged after merge for neuron '{source_path}'.")
            
            _debug_log_sync(f"Writing merged requirements to '{consumer_main_req_path}'.")
            with open(consumer_main_req_path, 'w', encoding='utf-8') as f_main_req_write:
                f_main_req_write.write(merged_req_content)

    except GitError as e_git: 
        result_base['message'] = f"Git error during sync for neuron '{source_path}' (brain: {brain_id}): {str(e_git)}"
        _debug_log_sync(f"sync_neuron FAILED (GitError): {result_base['message']}")
    except SyncError as e_sync: 
        result_base['message'] = f"Sync error for neuron '{source_path}' (brain: {brain_id}): {str(e_sync)}"
        _debug_log_sync(f"sync_neuron FAILED (SyncError): {result_base['message']}")
    except Exception as e_generic: 
        result_base['message'] = f"Unexpected error during sync for neuron '{source_path}' (brain: {brain_id}): {type(e_generic).__name__} - {str(e_generic)}"
        _debug_log_sync(f"sync_neuron FAILED (Unexpected Exception): {result_base['message']}")
    finally:
        # --------------------------------------------------------------
        # STEP 8: Clean up temporary brain clone directory.
        # --------------------------------------------------------------
        if brain_temp_dir and os.path.exists(brain_temp_dir):
            _debug_log_sync(f"Cleaning up temp brain clone dir from sync_neuron: {brain_temp_dir}")
            try:
                shutil.rmtree(brain_temp_dir)
                _debug_log_sync(f"Successfully removed temp dir: {brain_temp_dir}")
            except OSError as e_rmtree: 
                _debug_log_sync(f"Warning: Could not remove temp dir {brain_temp_dir}: {e_rmtree}")
        else:
            _debug_log_sync(f"No temp brain clone dir to clean up (path was: '{brain_temp_dir}').")
    
    _debug_log_sync(f"sync_neuron for '{dest_path}' returning: {result_base}")
    return result_base


def sync_all_neurons(neurons_config: Dict[str, Any], repo_path: str = '.') -> List[Dict[str, Any]]:
    """
    Description:
        Synchronizes all neurons defined in the configuration.
    
    Parameters:
        neurons_config (Dict[str, Any]): Configuration for neurons.
        repo_path (str): Path to the consumer repository. Defaults to current directory.

    Returns:
        results (List[Dict[str, Any]]): List of dictionaries containing synchronization results for each neuron.
    """
    _debug_log_sync(f"Starting sync_all_neurons for repo: {os.path.abspath(repo_path)}")
    results: List[Dict[str, Any]] = []
    if not neurons_config or not neurons_config.get('MAP'): 
        _debug_log_sync("sync_all_neurons: No neurons_config or MAP key found, or MAP is empty. Nothing to sync.")
        return results
    
    map_list = neurons_config.get('MAP', []) 
    if not map_list:
        _debug_log_sync("sync_all_neurons: MAP section is present but empty. Nothing to sync.")
        return results

    _debug_log_sync(f"sync_all_neurons: Found {len(map_list)} mappings to process.")
    for i, mapping in enumerate(map_list):
        brain_id = mapping.get('brain_id')
        source = mapping.get('source')
        dest = mapping.get('destination')

        # Validate mapping
        if not all([brain_id, source, dest]): 
            _debug_log_sync(f"sync_all_neurons: Skipping invalid mapping {i+1}/{len(map_list)} due to missing fields: {mapping}")
            results.append({
                'mapping': mapping, 'status': 'error', 'action': 'skipped',
                'message': 'Invalid mapping entry: missing brain_id, source, or destination.'
            })
            continue
            
        _debug_log_sync(f"sync_all_neurons: Processing mapping {i+1}/{len(map_list)}: Brain='{brain_id}', Source='{source}', Dest='{dest}'")
        result = sync_neuron(neurons_config, brain_id, source, dest, repo_path)
        results.append(result)
    _debug_log_sync(f"sync_all_neurons finished. Processed {len(results)} mappings.")
    return results


def get_modified_neurons(neurons_config: Dict[str, Any], repo_path: str = '.') -> List[Dict[str, Any]]:
    """
    Description:
        Identifies neurons that have been modified in the consumer repository.
    
    Parameters:
        neurons_config (Dict[str, Any]): Configuration for neurons.
        repo_path (str): Path to the consumer repository. Defaults to current directory.

    Returns:
        modified_neurons_mappings (List[Dict[str, Any]]): List of mapping dictionaries for modified neurons.
    """
    abs_repo_path = os.path.abspath(repo_path)
    _debug_log_sync(f"get_modified_neurons: For repo_path '{abs_repo_path}'")
    modified_neurons_mappings: List[Dict[str, Any]] = []
    
    # --------------------------------------------------------------
    # STEP 1: Basic validation checks.
    # --------------------------------------------------------------
    if not neurons_config or not neurons_config.get('MAP'):
        _debug_log_sync("get_modified_neurons: No config or MAP section, or MAP is empty. Returning empty list.")
        return modified_neurons_mappings

    if not is_git_repo(abs_repo_path):
        _debug_log_sync(f"get_modified_neurons: Path '{abs_repo_path}' does not appear to be a git repository. Returning empty list.")
        return [] 
        
    # --------------------------------------------------------------
    # STEP 2: Get list of modified files from Git.
    # --------------------------------------------------------------
    try:
        changed_file_paths_from_git_root = get_changed_files(cwd=abs_repo_path) 
        _debug_log_sync(f"get_modified_neurons: Git changed files (relative to root): {changed_file_paths_from_git_root}")
    except GitError as e:
        _debug_log_sync(f"get_modified_neurons: GitError getting changed files for '{abs_repo_path}': {e}. Returning empty list.")
        return [] 

    # --------------------------------------------------------------
    # STEP 3: Check each mapping against the list of modified files.
    # --------------------------------------------------------------
    for mapping_idx, mapping in enumerate(neurons_config['MAP']):
        consumer_dest_path_rel = mapping['destination'] 
        normalized_dest_path_rel = os.path.normpath(consumer_dest_path_rel)
        _debug_log_sync(f"get_modified_neurons: Checking mapping #{mapping_idx}: Neuron Dest='{normalized_dest_path_rel}' (Original: '{consumer_dest_path_rel}')")
        
        full_consumer_dest_path_abs = os.path.join(abs_repo_path, normalized_dest_path_rel)
        
        # Determine if this is a directory mapping
        is_dir_mapping_by_syntax = consumer_dest_path_rel.endswith('/') or \
                                   consumer_dest_path_rel.endswith(os.sep)
        
        is_dir_on_fs_currently = os.path.isdir(full_consumer_dest_path_abs)
        
        consumer_dest_exists_check = os.path.exists(full_consumer_dest_path_abs) 
        is_effectively_dir_mapping = is_dir_mapping_by_syntax or \
                                   (consumer_dest_exists_check and is_dir_on_fs_currently)


        _debug_log_sync(f"get_modified_neurons: Mapping for '{normalized_dest_path_rel}': is_dir_by_syntax={is_dir_mapping_by_syntax}, is_dir_on_fs={is_dir_on_fs_currently}, effective_is_dir={is_effectively_dir_mapping}")

        # Check each changed file against this mapping
        for changed_file_rel_to_repo_root in changed_file_paths_from_git_root:
            normalized_changed_file_rel = os.path.normpath(changed_file_rel_to_repo_root)

            if is_effectively_dir_mapping:
                # For directory mappings, check if the changed file is inside the directory
                dir_prefix_to_check = normalized_dest_path_rel
                if not (dir_prefix_to_check.endswith(os.sep) or dir_prefix_to_check == "."): 
                    dir_prefix_to_check += os.sep
                
                if normalized_changed_file_rel.startswith(dir_prefix_to_check):
                    _debug_log_sync(f"get_modified_neurons: Modified file '{normalized_changed_file_rel}' IS INSIDE mapped directory '{dir_prefix_to_check}'. Adding mapping.")
                    if mapping not in modified_neurons_mappings: modified_neurons_mappings.append(mapping)
                    break 
            else: 
                # For file mappings, check for an exact match
                if normalized_changed_file_rel == normalized_dest_path_rel:
                    _debug_log_sync(f"get_modified_neurons: Modified file '{normalized_changed_file_rel}' MATCHES mapped file '{normalized_dest_path_rel}'. Adding mapping.")
                    if mapping not in modified_neurons_mappings: modified_neurons_mappings.append(mapping)
                    break 
    
    _debug_log_sync(f"get_modified_neurons: Found {len(modified_neurons_mappings)} modified neuron mappings: {[m['destination'] for m in modified_neurons_mappings]}")
    return modified_neurons_mappings


def export_neurons_to_brain(
    neurons_config: Dict[str, Any],
    modified_neurons: List[Dict[str, Any]], 
    repo_path: str = '.', 
    commit_message_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Description:
        Exports modified neurons from consumer repository back to their brain repositories.
    
    Parameters:
        neurons_config (Dict[str, Any]): Configuration for neurons.
        modified_neurons (List[Dict[str, Any]]): List of mappings for modified neurons to export.
        repo_path (str): Path to the consumer repository. Defaults to current directory.
        commit_message_override (Optional[str]): Custom commit message to use for the export.

    Returns:
        overall_results (Dict[str, Any]): Dictionary mapping brain IDs to export results.
    """
    abs_consumer_repo_path = os.path.abspath(repo_path)
    _debug_log_sync(f"Starting export_neurons_to_brain. Consumer repo path: '{abs_consumer_repo_path}'. Modified neurons count: {len(modified_neurons)}")
    overall_results: Dict[str, Any] = {} 
    
    # --------------------------------------------------------------
    # STEP 1: Check if export is allowed by policy.
    # --------------------------------------------------------------
    sync_policy = neurons_config.get('SYNC_POLICY', {})
    if not sync_policy.get('ALLOW_PUSH_TO_BRAIN', False): 
        msg = "Exporting to brain repositories is not allowed by SYNC_POLICY (ALLOW_PUSH_TO_BRAIN is false)."
        _debug_log_sync(f"Export aborted: {msg}")
        overall_results["_GLOBAL_ERROR_"] = {'status': 'error', 'message': msg, 'exported_neurons': []}
        return overall_results

    if not modified_neurons:
        msg = "No modified neurons provided to export."
        _debug_log_sync(f"Export info: {msg}")
        overall_results["_NO_MODIFICATIONS_"] = {'status': 'success', 'message': msg, 'exported_neurons': []}
        return overall_results

    # --------------------------------------------------------------
    # STEP 2: Group modified neurons by brain ID.
    # --------------------------------------------------------------
    neurons_by_brain: Dict[str, List[Dict[str, Any]]] = {}
    for neuron_mapping in modified_neurons:
        brain_id = neuron_mapping['brain_id']
        neurons_by_brain.setdefault(brain_id, []).append(neuron_mapping)
    _debug_log_sync(f"Grouped {len(modified_neurons)} modified neurons by brain IDs: {list(neurons_by_brain.keys())}")

    # --------------------------------------------------------------
    # STEP 3: Process each brain separately.
    # --------------------------------------------------------------
    for brain_id, mappings_for_this_brain in neurons_by_brain.items():
        _debug_log_sync(f"Processing export for brain_id: '{brain_id}'")
        brain_repo_config = neurons_config.get('BRAINS', {}).get(brain_id)
        if not brain_repo_config or not brain_repo_config.get('REMOTE'):
            msg = f"Brain configuration or REMOTE URL for '{brain_id}' not found in .neurons."
            _debug_log_sync(f"Export error for '{brain_id}': {msg}")
            overall_results[brain_id] = {'status': 'error', 'message': msg, 'exported_neurons': []}
            continue

        remote_url = brain_repo_config['REMOTE']
        branch = brain_repo_config.get('BRANCH') 

        brain_ops_path: Optional[str] = None 
        is_direct_brain_modification = False 
        temp_dir_for_clone: Optional[str] = None 

        try:
            # --------------------------------------------------------------
            # STEP 4: Handle local brain repositories (file://) specially.
            # --------------------------------------------------------------
            if remote_url.startswith('file://'):
                parsed_url = urlparse(remote_url)
                local_brain_filesystem_path = os.path.abspath(unquote(parsed_url.path))
                _debug_log_sync(f"Brain '{brain_id}' URL is local: '{local_brain_filesystem_path}' (from '{remote_url}')")
                if os.path.isdir(local_brain_filesystem_path) and is_git_repo(local_brain_filesystem_path):
                    if not is_bare_repo(local_brain_filesystem_path):
                        _debug_log_sync(f"Brain '{brain_id}' at '{local_brain_filesystem_path}' is a local NON-BARE repository. Will attempt direct modification.")
                        try:
                            # Verify brain repository is in a suitable state for direct modification
                            current_brain_branch = run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], cwd=local_brain_filesystem_path)
                            if branch and current_brain_branch != branch:
                                raise GitError(f"Local non-bare brain '{brain_id}' (path: {local_brain_filesystem_path}) is on branch '{current_brain_branch}', but export target branch is '{branch}'. Manual branch switch required in brain repo or ensure target branch is checked out.")
                            brain_status_output = run_git_command(['status', '--porcelain'], cwd=local_brain_filesystem_path)
                            if brain_status_output.strip():
                                raise GitError(f"Local non-bare brain '{brain_id}' at '{local_brain_filesystem_path}' has uncommitted changes. Please commit or stash them before export.")
                        except GitError as ge_local_brain_check:
                             raise SyncError(f"Pre-check failed for local non-bare brain '{brain_id}': {ge_local_brain_check}") from ge_local_brain_check
                        
                        brain_ops_path = get_repo_root(local_brain_filesystem_path) 
                        is_direct_brain_modification = True
                        _debug_log_sync(f"Operations for brain '{brain_id}' will be performed directly in: {brain_ops_path}")
                    else: 
                        _debug_log_sync(f"Brain '{brain_id}' at '{local_brain_filesystem_path}' is a local BARE repository. Cloning for export.")
                else: 
                    raise SyncError(f"Local brain path '{local_brain_filesystem_path}' (from URL '{remote_url}') for brain '{brain_id}' is not a valid Git repository.")
            
            # --------------------------------------------------------------
            # STEP 5: Clone the brain repository if not directly modifying a local one.
            # --------------------------------------------------------------
            if not is_direct_brain_modification: 
                _debug_log_sync(f"Cloning brain '{brain_id}' from '{remote_url}' (branch: {branch or 'default'}) for export.")
                temp_dir_for_clone = temp_clone_repo(remote_url, branch) 
                brain_ops_path = temp_dir_for_clone 
                _debug_log_sync(f"Brain '{brain_id}' cloned to temp dir for export: {brain_ops_path}")

            if not brain_ops_path: 
                raise SyncError(f"Internal error: brain_ops_path not set for brain '{brain_id}'.")

            exported_mappings_details_for_commit = [] 
            any_actual_file_change_in_brain = False

            # --------------------------------------------------------------
            # STEP 6: Copy modified neuron files from consumer to brain repository.
            # --------------------------------------------------------------
            for mapping in mappings_for_this_brain:
                consumer_fs_source_path = os.path.join(abs_consumer_repo_path, mapping['destination']) 
                brain_fs_target_path = os.path.join(brain_ops_path, mapping['source']) 
                _debug_log_sync(f"Exporting mapping for brain '{brain_id}': Consumer_Source='{consumer_fs_source_path}' -> Brain_Target='{brain_fs_target_path}'")

                if not os.path.exists(consumer_fs_source_path):
                    _debug_log_sync(f"Skipping export of '{mapping['destination']}' for brain '{brain_id}', path not found in consumer '{abs_consumer_repo_path}'.")
                    continue 

                # Ensure parent directory exists in brain repository
                brain_target_parent_dir = os.path.dirname(brain_fs_target_path)
                if brain_target_parent_dir: 
                    _debug_log_sync(f"Ensuring parent directory for brain target: {brain_target_parent_dir}")
                    os.makedirs(brain_target_parent_dir, exist_ok=True)
                
                file_content_changed_in_this_op = False
                if os.path.isdir(consumer_fs_source_path): 
                    # ===============
                    # Sub step 6.1: Handle directory neuron export.
                    # ===============
                    _debug_log_sync(f"Consumer path '{consumer_fs_source_path}' is a directory. Copying tree to brain target '{brain_fs_target_path}'.")
                    if os.path.exists(brain_fs_target_path):
                        if not os.path.isdir(brain_fs_target_path): 
                            # Brain target exists but is a file - remove and copy directory
                            _debug_log_sync(f"Brain target '{brain_fs_target_path}' is a file, removing to replace with directory.")
                            os.remove(brain_fs_target_path)
                            shutil.copytree(consumer_fs_source_path, brain_fs_target_path)
                            file_content_changed_in_this_op = True
                        else: 
                            # Brain target is a directory - remove and copytree to ensure clean state
                            _debug_log_sync(f"Brain target dir '{brain_fs_target_path}' exists. Removing before copytree for overwrite.")
                            shutil.rmtree(brain_fs_target_path)
                            shutil.copytree(consumer_fs_source_path, brain_fs_target_path)
                            file_content_changed_in_this_op = True 
                    else: 
                        # Brain target doesn't exist - simple copytree
                        shutil.copytree(consumer_fs_source_path, brain_fs_target_path)
                        file_content_changed_in_this_op = True
                else: 
                    # ===============
                    # Sub step 6.2: Handle file neuron export.
                    # ===============
                    _debug_log_sync(f"Consumer path '{consumer_fs_source_path}' is a file. Copying to brain target '{brain_fs_target_path}'.")
                    with open(consumer_fs_source_path, 'rb') as f_consumer: consumer_bytes = f_consumer.read()
                    
                    needs_write_to_brain = True
                    if os.path.exists(brain_fs_target_path):
                        if os.path.isdir(brain_fs_target_path): 
                             # Brain target is a directory but consumer source is a file - replace
                             _debug_log_sync(f"Brain target '{brain_fs_target_path}' is a dir, but consumer source is file. Removing brain dir.")
                             shutil.rmtree(brain_fs_target_path)
                        else: 
                            # Both are files - check if content differs
                            try:
                                with open(brain_fs_target_path, 'rb') as f_brain_read: existing_brain_bytes = f_brain_read.read()
                                if existing_brain_bytes == consumer_bytes:
                                    needs_write_to_brain = False
                                    _debug_log_sync(f"Brain target file '{brain_fs_target_path}' content matches consumer. No write needed.")
                                else:
                                    _debug_log_sync(f"Brain target file '{brain_fs_target_path}' content differs. Overwriting.")
                            except IOError as e_read_brain:
                                _debug_log_sync(f"IOError reading existing brain file '{brain_fs_target_path}': {e_read_brain}. Assuming overwrite is needed.")
                    else: 
                        _debug_log_sync(f"Brain target '{brain_fs_target_path}' does not exist. Writing new file.")

                    if needs_write_to_brain:
                        try:
                            with open(brain_fs_target_path, 'wb') as f_brain_write: f_brain_write.write(consumer_bytes)
                            file_content_changed_in_this_op = True
                        except IOError as e_write_brain:
                            raise SyncError(f"Failed to write to brain target '{brain_fs_target_path}': {e_write_brain}") from e_write_brain
                
                if file_content_changed_in_this_op:
                    any_actual_file_change_in_brain = True 
                    exported_mappings_details_for_commit.append(f"  - '{mapping['source']}' (from consumer: '{mapping['destination']}')")
            
            # --------------------------------------------------------------
            # STEP 7: Commit and push changes if any files were modified.
            # --------------------------------------------------------------
            if any_actual_file_change_in_brain:
                _debug_log_sync(f"Actual file changes potentially made in brain ops path '{brain_ops_path}' for '{brain_id}'. Checking git status.")
                status_output = run_git_command(['status', '--porcelain'], cwd=brain_ops_path, timeout_seconds=20)
                if status_output.strip(): 
                    _debug_log_sync(f"Git status in brain ops path '{brain_ops_path}' shows changes. Adding and committing for '{brain_id}'.")
                    run_git_command(['add', '.'], cwd=brain_ops_path, timeout_seconds=20) 
                    
                    # Prepare commit message with details
                    commit_msg_body = "\n\nExported items from consumer:\n" + "\n".join(exported_mappings_details_for_commit)
                    final_commit_message = (commit_message_override or f"Brain Export: Update from consumer repository") + commit_msg_body
                    
                    run_git_command(['commit', '-m', final_commit_message], cwd=brain_ops_path, timeout_seconds=30)
                    
                    if not is_direct_brain_modification: 
                        # Push changes for remote brain repositories
                        _debug_log_sync(f"Pushing committed changes from clone '{brain_ops_path}' to brain '{brain_id}' remote '{remote_url}'.")
                        run_git_command(['push'], cwd=brain_ops_path, timeout_seconds=90) 
                        msg = f"{len(exported_mappings_details_for_commit)} neuron source(s) exported and pushed to brain '{brain_id}'."
                    else: 
                        # Local brain repositories are already committed, no push needed
                        msg = f"{len(exported_mappings_details_for_commit)} neuron source(s) exported and committed directly to local brain '{brain_id}' at '{brain_ops_path}'."
                    
                    _debug_log_sync(f"Export success for '{brain_id}': {msg}")
                    successfully_exported_neurons_list = [
                        m for m in mappings_for_this_brain 
                        if f"'{m['source']}'" in "".join(exported_mappings_details_for_commit)
                    ]
                    overall_results[brain_id] = {
                        'status': 'success', 
                        'message': msg,
                        'exported_neurons': successfully_exported_neurons_list
                    }
                else: 
                    msg = f"Files for brain '{brain_id}' copied/updated in ops path '{brain_ops_path}', but no effective changes detected by git status. Nothing to commit."
                    _debug_log_sync(f"Export info for '{brain_id}': {msg}")
                    overall_results[brain_id] = {'status': 'success', 'message': msg, 'exported_neurons': [] }
            else: 
                msg = f"No effective file changes or new files to export for brain '{brain_id}' based on consumer content."
                _debug_log_sync(f"Export info for '{brain_id}': {msg}")
                overall_results[brain_id] = {'status': 'success', 'message': msg, 'exported_neurons': []}

        except GitError as e_git:
            msg = f"Git operation failed during export process for brain '{brain_id}': {str(e_git)}"
            _debug_log_sync(f"Export error for '{brain_id}' (GitError): {msg}")
            overall_results[brain_id] = {'status': 'error', 'message': msg, 'exported_neurons': []}
        except SyncError as e_sync: 
            msg = f"Sync logic error during export for brain '{brain_id}': {str(e_sync)}"
            _debug_log_sync(f"Export error for '{brain_id}' (SyncError): {msg}")
            overall_results[brain_id] = {'status': 'error', 'message': msg, 'exported_neurons': []}
        except Exception as e_generic: 
            msg = f"Unexpected generic error exporting to brain '{brain_id}': {type(e_generic).__name__} - {str(e_generic)}"
            _debug_log_sync(f"Export error for '{brain_id}' (Generic Exception): {msg}")
            overall_results[brain_id] = {'status': 'error', 'message': msg, 'exported_neurons': []}
        finally:
            # --------------------------------------------------------------
            # STEP 8: Clean up temporary clone directory if used.
            # --------------------------------------------------------------
            if temp_dir_for_clone and os.path.exists(temp_dir_for_clone):
                _debug_log_sync(f"Cleaning up temp brain clone dir from export: {temp_dir_for_clone}")
                try: shutil.rmtree(temp_dir_for_clone)
                except OSError as e_rm: _debug_log_sync(f"Warning: Failed to remove temp dir {temp_dir_for_clone} after export: {e_rm}")
            elif temp_dir_for_clone: 
                 _debug_log_sync(f"Temp clone dir {temp_dir_for_clone} was assigned but does not exist for cleanup.")
                
    _debug_log_sync(f"export_neurons_to_brain finished. Overall results: {overall_results}")
    return overall_results