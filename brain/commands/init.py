"""
Handler for the brain init command.

Implements the 'brain init' command which initializes a Git repository
and optionally sets up neurons.
"""

import os
import subprocess
import argparse
from typing import List

from brain.config import save_brain_config, save_neurons_config


def handle_init(args: List[str]) -> int:
    """
    Description:
        Handle the brain init command. This function processes command-line arguments,
        initializes a Git repository, and optionally configures it as a brain repository
        with neurons.
    
    Parameters:
        args (List[str]): Command line arguments passed to the brain init command.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
    """
    # --------------------------------------------------------------
    # STEP 1: Set up argument parser and define command options.
    # --------------------------------------------------------------
    # Create argument parser with description.
    parser = argparse.ArgumentParser(
        description="Initialize a Git repository with Brain",
        prog="brain init"
    )
    
    # Add standard git init arguments.
    parser.add_argument(
        'directory',
        nargs='?',
        help="Directory to initialize"
    )
    
    parser.add_argument(
        '--as-brain',
        action='store_true',
        help="Initialize as a brain repository"
    )
    
    parser.add_argument(
        '--brain-id',
        help="Brain identifier (for --as-brain)"
    )
    
    parser.add_argument(
        '--brain-description',
        help="Brain description (for --as-brain)"
    )
    
    parser.add_argument(
        '--with-neurons',
        action='store_true',
        help="Initialize with neurons configuration"
    )
    
    # --------------------------------------------------------------
    # STEP 2: Parse arguments and prepare for git init.
    # --------------------------------------------------------------
    # Parse known arguments, keeping unknown ones for git init.
    parsed_args, unknown_args = parser.parse_known_args(args)
    
    # Prepare arguments for git init command.
    git_args = unknown_args
    if parsed_args.directory:
        git_args.append(parsed_args.directory)
    
    # --------------------------------------------------------------
    # STEP 3: Execute git init command.
    # --------------------------------------------------------------
    # Run git init with prepared arguments.
    result = subprocess.run(['git', 'init'] + git_args)
    
    # Return early if git init failed.
    if result.returncode != 0:
        return result.returncode
    
    # --------------------------------------------------------------
    # STEP 4: Handle brain and neurons configuration.
    # --------------------------------------------------------------
    # Determine the repository directory.
    repo_dir = parsed_args.directory or '.'
    
    # Store current directory to return later.
    current_dir = os.getcwd()
    if repo_dir != '.':
        os.chdir(repo_dir)
    
    try:
        # ===============
        # Sub step 4.1: Initialize as brain repository if requested.
        # ===============
        if parsed_args.as_brain:
            # Use provided brain ID or derive from directory name.
            brain_id = parsed_args.brain_id or os.path.basename(os.path.abspath(repo_dir))
            # Use provided description or generate default one.
            brain_description = parsed_args.brain_description or f"Brain repository: {brain_id}"
            
            # Create brain configuration with default settings.
            brain_config = {
                'ID': brain_id,
                'DESCRIPTION': brain_description,
                'EXPORT': {
                    '*': 'readonly'  # Default export all as readonly
                }
            }
            
            # Save the brain configuration to disk.
            save_brain_config(brain_config)
            print(f"Initialized brain repository with ID: {brain_id}")
            print("Edit .brain file to configure exported neurons.")
        
        # ===============
        # Sub step 4.2: Initialize with neurons if requested.
        # ===============
        if parsed_args.with_neurons:
            # Create neurons configuration with default settings.
            neurons_config = {
                'BRAINS': {},
                'SYNC_POLICY': {
                    'AUTO_SYNC_ON_PULL': True,
                    'CONFLICT_STRATEGY': 'prompt',
                    'ALLOW_LOCAL_MODIFICATIONS': False,
                    'ALLOW_PUSH_TO_BRAIN': False
                },
                'MAP': []
            }
            
            # Save the neurons configuration to disk.
            save_neurons_config(neurons_config)
            print("Initialized repository with neurons configuration.")
            print("Use 'brain add-brain' to add a brain and 'brain add-neuron' to add neurons.")
    
    finally:
        # --------------------------------------------------------------
        # STEP 5: Clean up and return.
        # --------------------------------------------------------------
        # Return to original directory if we changed it.
        if repo_dir != '.':
            os.chdir(current_dir)
    
    return 0