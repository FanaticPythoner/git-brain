"""
Handler for the brain clone command.

Implements the 'brain clone' command which clones a repository
and sets up neurons if present.
"""

import os
import subprocess
from typing import List

from brain.config import load_neurons_config, NeuronsConfigError
from brain.sync import sync_all_neurons


def handle_clone(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain clone' command which clones a Git repository and sets up neurons if present.
    
    Parameters:
        args (List[str]): Command-line arguments passed to the clone command, including repository URL and options.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
    """
    # --------------------------------------------------------------
    # STEP 1: Execute standard git clone command.
    # --------------------------------------------------------------
    # Run the git clone command with all provided arguments.
    result = subprocess.run(['git', 'clone'] + args)
    
    if result.returncode != 0:
        # Return error code if git clone failed.
        return result.returncode
    
    # --------------------------------------------------------------
    # STEP 2: Determine the cloned repository directory path.
    # --------------------------------------------------------------
    if len(args) > 0 and not args[0].startswith('-'):
        # URL is first non-flag argument.
        if len(args) > 1 and not args[1].startswith('-'):
            # ===============
            # Sub step 2.1: Use explicitly provided directory.
            # ===============
            repo_dir = args[1]
        else:
            # ===============
            # Sub step 2.2: Derive directory name from repository URL.
            # ===============
            repo_dir = os.path.basename(args[0].rstrip('/'))
            if repo_dir.endswith('.git'):
                # Remove .git extension if present.
                repo_dir = repo_dir[:-4]
    else:
        # Cannot determine directory, exit with success.
        return 0
    
    # --------------------------------------------------------------
    # STEP 3: Check for and process .neurons configuration file.
    # --------------------------------------------------------------
    # Look for .neurons file in the cloned repository.
    neurons_path = os.path.join(repo_dir, '.neurons')
    if os.path.exists(neurons_path):
        # Notify user about neurons configuration.
        print(f"\nRepository contains neurons configuration. Setting up neurons...")
        
        # ===============
        # Sub step 3.1: Change to repository directory.
        # ===============
        # Store current directory to return to later.
        current_dir = os.getcwd()
        os.chdir(repo_dir)
        
        try:
            # ===============
            # Sub step 3.2: Load and process neurons configuration.
            # ===============
            # Load neurons config file.
            neurons_config = load_neurons_config()
            
            # Synchronize all neurons based on configuration.
            sync_results = sync_all_neurons(neurons_config)
            
            # ===============
            # Sub step 3.3: Report setup results.
            # ===============
            # Count successful and failed setups.
            success_count = sum(1 for r in sync_results if r.get('status') == 'success')
            error_count = sum(1 for r in sync_results if r.get('status') == 'error')
            
            # Display summary of results.
            print(f"Neurons setup complete: {success_count} succeeded, {error_count} failed")
        except NeuronsConfigError as e:
            # Handle configuration errors.
            print(f"Error setting up neurons: {str(e)}")
        finally:
            # ===============
            # Sub step 3.4: Return to original directory.
            # ===============
            # Always return to the original directory, even if errors occurred.
            os.chdir(current_dir)
    
    # Return success code.
    return 0