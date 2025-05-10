"""
Description:
    Handler for the brain add-brain command.
    
    Implements the 'brain add-brain' command which adds a brain to a repository.
    This allows for tracking and managing external brain repositories within the current project.
"""

import os
import shutil
import sys
from typing import List, Dict, Any, Optional

from brain.config import (
    get_current_repo_neurons_config, 
    # load_neurons_config, # Not directly used, get_current_repo_neurons_config is preferred
    save_neurons_config,
    NeuronsConfigError
)
from brain.git import temp_clone_repo, GitError


def handle_add_brain(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain add-brain' command which adds an external brain repository
        to the current repository's neurons configuration.
    
    Parameters:
        args (List[str]): Command line arguments where:
                          args[0] = brain_id - Identifier for the brain
                          args[1] = remote_url - URL of the remote brain repository
                          args[2] = branch (optional) - Branch to use (defaults to 'main')

    Returns:
        exit_code (int): 0 for success, 1 for failure
    """
    # --------------------------------------------------------------
    # STEP 1: Validate and extract command arguments.
    # --------------------------------------------------------------
    if len(args) < 2:
        print("ERROR: Missing required arguments for add-brain.", file=sys.stderr)
        print("Usage: brain add-brain <id> <remote_url> [branch]", file=sys.stderr)
        return 1
    
    brain_id = args[0]
    remote_url = args[1]
    branch = args[2] if len(args) > 2 else 'main' # Default to 'main'
    
    # --------------------------------------------------------------
    # STEP 2: Load or initialize neurons configuration.
    # --------------------------------------------------------------
    neurons_config: Optional[Dict[str, Any]] = None
    # Handle NeuronsConfigError if .neurons file doesn't exist or is invalid.
    try:
        neurons_config = get_current_repo_neurons_config() # This will raise if file not found or parse error
        if not neurons_config: # Should not happen if get_current_repo_neurons_config raises on error
            # This path implies get_current_repo_neurons_config returned None without raising,
            # which is contrary to its updated design (it re-raises).
            # However, to be safe, or if it could return None for other reasons (e.g. empty but valid file):
            print("Warning: Neurons configuration loaded as empty. Initializing a new structure if needed.", file=sys.stderr)
            neurons_config = {} # Initialize to empty dict to build upon
    except NeuronsConfigError as e: # Covers file not found, parse errors
        print(f"Info: Neurons configuration issue ({str(e)}). Assuming new configuration.", file=sys.stdout) # Changed to stdout for info
        # This is an expected case if .neurons doesn't exist yet.
        pass # Fall through to create new_config structure if neurons_config is None

    # ===============
    # Sub step 2.1: Initialize default configuration structure when missing.
    # ===============
    if neurons_config is None: # If try-except passed due to error, neurons_config is None
        neurons_config = {
            'BRAINS': {},
            'SYNC_POLICY': {
                'AUTO_SYNC_ON_PULL': True,
                'CONFLICT_STRATEGY': 'prompt',
                'ALLOW_LOCAL_MODIFICATIONS': False,
                'ALLOW_PUSH_TO_BRAIN': False,
                'AUTO_SYNC_ON_CHECKOUT': False # Ensure all defaults are here
            },
            'MAP': []
        }
    # ===============
    # Sub step 2.2: Ensure all required configuration keys exist.
    # ===============
    # Ensure essential keys exist if an empty or partial config was loaded (e.g. from an empty .neurons file)
    if 'BRAINS' not in neurons_config: neurons_config['BRAINS'] = {}
    if 'SYNC_POLICY' not in neurons_config:
        neurons_config['SYNC_POLICY'] = {
            'AUTO_SYNC_ON_PULL': True, 'CONFLICT_STRATEGY': 'prompt',
            'ALLOW_LOCAL_MODIFICATIONS': False, 'ALLOW_PUSH_TO_BRAIN': False,
            'AUTO_SYNC_ON_CHECKOUT': False
        }
    if 'MAP' not in neurons_config: neurons_config['MAP'] = []
    
    # --------------------------------------------------------------
    # STEP 3: Check if brain already exists in configuration.
    # --------------------------------------------------------------
    if brain_id in neurons_config.get('BRAINS', {}):
        print(f"ERROR: Brain '{brain_id}' already exists in .neurons configuration.", file=sys.stderr)
        current_brain_details = neurons_config['BRAINS'][brain_id]
        print(f"Current URL: {current_brain_details.get('REMOTE')}, Branch: {current_brain_details.get('BRANCH', 'N/A')}", file=sys.stderr)
        return 1
    
    # --------------------------------------------------------------
    # STEP 4: Verify brain repository by temporary cloning.
    # --------------------------------------------------------------
    print(f"Verifying brain repository: {remote_url} (branch: {branch})")
    temp_dir_clone: Optional[str] = None
    try:
        temp_dir_clone = temp_clone_repo(remote_url, branch) # This logs verbosely
        
        # ===============
        # Sub step 4.1: Check for .brain file in repository root.
        # ===============
        brain_file_path = os.path.join(temp_dir_clone, '.brain')
        if not os.path.exists(brain_file_path):
            print("WARNING: The specified repository does not contain a '.brain' file at its root.", file=sys.stderr)
            print("It may not be a properly configured brain repository.", file=sys.stderr)
            
            # ===============
            # Sub step 4.2: Handle user confirmation based on session type.
            # ===============
            # Interactive confirmation (skip if not tty, e.g., in scripts)
            if sys.stdin.isatty():
                response = input("Continue adding this brain anyway? (y/N): ").strip().lower()
                if response != 'y':
                    print("Brain addition cancelled by user.")
                    return 1 # User cancelled
            else: # Non-interactive, proceed with caution or make it an error
                print("Non-interactive session: Continuing to add brain despite missing .brain file.", file=sys.stderr)

    except GitError as e:
        print(f"ERROR: Could not access or verify the brain repository at '{remote_url}'.", file=sys.stderr)
        print(f"Git Details: {str(e)}", file=sys.stderr)
        return 1
    except Exception as e_generic: # Catch other unexpected errors during verification
        print(f"ERROR: An unexpected error occurred during brain verification: {str(e_generic)}", file=sys.stderr)
        return 1
    finally:
        # ===============
        # Sub step 4.3: Clean up temporary clone directory.
        # ===============
        if temp_dir_clone and os.path.exists(temp_dir_clone):
            try:
                shutil.rmtree(temp_dir_clone)
            except OSError as e_rm:
                print(f"Warning: Could not remove temporary clone directory '{temp_dir_clone}': {e_rm}", file=sys.stderr)

    # --------------------------------------------------------------
    # STEP 5: Add brain entry to neurons configuration.
    # --------------------------------------------------------------
    # Add brain to configuration (guaranteed neurons_config is a dict here)
    neurons_config['BRAINS'][brain_id] = {
        'REMOTE': remote_url,
        'BRANCH': branch
    }
    
    # --------------------------------------------------------------
    # STEP 6: Save updated configuration and provide user feedback.
    # --------------------------------------------------------------
    try:
        save_neurons_config(neurons_config) # This will create .neurons if it doesn't exist
        print(f"Added brain '{brain_id}' from {remote_url} (branch: {branch}) to .neurons configuration.")
        print("Use 'brain add-neuron' to add neuron mappings from this brain.")
        return 0
    except NeuronsConfigError as e: # Error during saving .neurons
        print(f"Error saving neurons configuration: {str(e)}", file=sys.stderr)
        return 1