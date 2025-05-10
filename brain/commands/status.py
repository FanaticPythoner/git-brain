"""
Handler for the brain status command.

Implements the 'brain status' command which shows the status of the repository
and neuron files.
"""

import os
import sys
import subprocess
from typing import List, Dict, Any, Optional

from brain.config import get_current_repo_neurons_config, NeuronsConfigError
from brain.sync import get_modified_neurons


def handle_status(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain status' command by executing git status and displaying
        information about modified neurons in the repository. This function combines
        standard git status output with brain-specific neuron status information.
    
    Parameters:
        args (List[str]): Command line arguments passed to the status command,
                         which will be forwarded to 'git status'.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
                         Returns git's exit code if git fails, 127 if git is not found,
                         1 if neurons configuration has errors, or 0 for success.
    """
    # --------------------------------------------------------------
    # STEP 1: Execute standard git status command.
    # --------------------------------------------------------------
    try:
        # Run git status with any provided arguments
        result = subprocess.run(['git', 'status'] + args, check=True, capture_output=True, text=True)
        # Print git status output directly
        if result.stdout: print(result.stdout.strip())
        if result.stderr: print(result.stderr.strip(), file=sys.stderr) # Should be empty on success
    except subprocess.CalledProcessError as e:
        # Handle git command errors
        if e.stdout: print(e.stdout.strip()) # Print stdout even on error
        if e.stderr: print(e.stderr.strip(), file=sys.stderr)
        return e.returncode # Propagate Git's error code
    except FileNotFoundError:
        # Handle case where git is not installed
        print("ERROR: git command not found. Please ensure Git is installed.", file=sys.stderr)
        return 127
    
    # --------------------------------------------------------------
    # STEP 2: Check for and load neurons configuration.
    # --------------------------------------------------------------
    # Check for .neurons file
    neurons_config: Optional[Dict[str, Any]] = None
    try:
        # Attempt to load the neurons configuration
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            # No neurons config, git status was successful, so return 0.
            # No message needed unless verbose.
            return 0 
    except NeuronsConfigError as e:
        print(f"\nError loading neurons configuration: {str(e)}", file=sys.stderr)
        print("Git status was successful, but neuron configuration is problematic.", file=sys.stderr)
        return 1 # Indicate an error related to brain, even if git status succeeded
    
    # --------------------------------------------------------------
    # STEP 3: Display modified neurons information.
    # --------------------------------------------------------------
    # Get modified neurons
    modified_neurons = get_modified_neurons(neurons_config)
    
    if modified_neurons:
        # ===============
        # Sub step 3.1: Display list of modified neurons.
        # ===============
        print("\nNeuron status:")
        print("  Modified neurons:")
        for neuron in modified_neurons:
            brain_id = neuron.get('brain_id', 'unknown')
            dest = neuron.get('destination', 'unknown')
            print(f"    {dest} (from brain: {brain_id})")
        
        # ===============
        # Sub step 3.2: Display sync policy information and warnings.
        # ===============
        # Get sync policy configuration
        sync_policy = neurons_config.get('SYNC_POLICY', {})
        allow_local_mods = sync_policy.get('ALLOW_LOCAL_MODIFICATIONS', False)
        allow_push_to_brain = sync_policy.get('ALLOW_PUSH_TO_BRAIN', False)
        
        # Display appropriate warnings based on sync policy configuration
        if not allow_local_mods:
            # Warn if local modifications are not allowed
            print("\n  Warning: Local neuron modifications are not allowed by configuration")
            print("  To allow, set ALLOW_LOCAL_MODIFICATIONS=true in .neurons")
        
        if allow_local_mods and not allow_push_to_brain: # Only relevant if local mods are allowed
            # Note that pushing to brain is not allowed
            print("\n  Note: Pushing neuron changes to brain repositories is not allowed by current SYNC_POLICY")
            print("  To allow, set ALLOW_PUSH_TO_BRAIN=true in .neurons and use 'brain export' or 'brain push --push-to-brain'")
        
        if allow_local_mods and allow_push_to_brain:
            # Provide information about pushing changes to brain repositories
            print("\n  Note: Use 'brain export <neuron_paths>' or 'brain push --push-to-brain' to push these changes to brain repositories")
    
    # --------------------------------------------------------------
    # STEP 4: Display neuron mappings if verbose output is requested.
    # --------------------------------------------------------------
    if '--neuron-mappings' in args or '-v' in args or '--verbose' in args: # Show mappings if verbose requested for status
        mappings = neurons_config.get('MAP', [])
        if mappings:
            # Display all configured neuron mappings
            print("\nNeuron mappings:")
            for mapping_item in mappings: # Renamed to avoid conflict
                brain_id = mapping_item.get('brain_id', 'unknown')
                source = mapping_item.get('source', 'unknown')
                dest = mapping_item.get('destination', 'unknown')
                print(f"  {dest} ← {brain_id}::{source}")
        else:
            # Inform user if no mappings are defined
            print("\nNo neuron mappings defined.")
            
    # Return success
    return 0