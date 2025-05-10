"""
Handler for the brain checkout command.

Implements the 'brain checkout' command which checks out a branch
and optionally syncs neurons.
"""

import os
import sys
import subprocess
from typing import List, Dict, Any, Optional

from brain.config import get_current_repo_neurons_config, NeuronsConfigError
from brain.sync import sync_all_neurons


def handle_checkout(args: List[str]) -> int:
    """
    Description:
        Handles the brain checkout command, which wraps git checkout with additional
        neuron synchronization capabilities.
    
    Parameters:
        args (List[str]): Command line arguments passed to the brain checkout command.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
    """
    # --------------------------------------------------------------
    # STEP 1: Extract special flags.
    # --------------------------------------------------------------
    sync_flag = '--sync-neurons'
    no_sync_flag = '--no-sync-neurons'
    
    sync_neurons = sync_flag in args
    no_sync = no_sync_flag in args
    
    # Remove our custom flags before passing to git.
    filtered_args = [arg for arg in args if arg not in [sync_flag, no_sync_flag]]
    
    # --------------------------------------------------------------
    # STEP 2: Execute standard git checkout.
    # --------------------------------------------------------------
    try:
        result = subprocess.run(['git', 'checkout'] + filtered_args, check=True, capture_output=True, text=True)
        if result.stdout: print(result.stdout.strip())
        if result.stderr: print(result.stderr.strip(), file=sys.stderr)
    except subprocess.CalledProcessError as e:
        # Output any messages from git before returning the error code.
        if e.stdout: print(e.stdout.strip())
        if e.stderr: print(e.stderr.strip(), file=sys.stderr)
        return e.returncode # Propagate Git's error code.
    except FileNotFoundError:
        print("ERROR: git command not found. Please ensure Git is installed.", file=sys.stderr)
        return 127  # Standard error code for command not found.


    # --------------------------------------------------------------
    # STEP 3: Check for and load neurons configuration.
    # --------------------------------------------------------------
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            # No neurons config, checkout was successful, so return 0.
            # No message needed unless verbose.
            return 0 
    except NeuronsConfigError as e:
        print(f"Error loading neurons configuration after checkout: {str(e)}", file=sys.stderr)
        print("Git checkout was successful, but neuron configuration is problematic.", file=sys.stderr)
        return 1 # Indicate an error related to brain, even if git checkout succeeded.
    
    # --------------------------------------------------------------
    # STEP 4: Determine if neurons should be synchronized.
    # --------------------------------------------------------------
    sync_policy = neurons_config.get('SYNC_POLICY', {})
    # Default for AUTO_SYNC_ON_CHECKOUT should be documented or consistently applied.
    # Assuming True if not specified for now, or could be False. Let's assume False by default to be safer.
    auto_sync = sync_policy.get('AUTO_SYNC_ON_CHECKOUT', False) 
    
    # --------------------------------------------------------------
    # STEP 5: Synchronize neurons if required.
    # --------------------------------------------------------------
    if (auto_sync and not no_sync) or sync_neurons:
        print("\nSynchronizing neurons after checkout...")
        
        try:
            # ===============
            # Sub step 5.1: Perform the neuron synchronization.
            # ===============
            results = sync_all_neurons(neurons_config)
            
            # ===============
            # Sub step 5.2: Collect and report synchronization results.
            # ===============
            status_counts: Dict[str, int] = {'success': 0, 'error': 0} # Initialize correctly.
            
            for result_item in results: # Use a different variable name.
                status = result_item.get('status')
                if status: # Status can be None if not set in result_item.
                    status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"Neuron synchronization complete: {status_counts.get('success', 0)} succeeded, {status_counts.get('error', 0)} failed")
            if status_counts.get('error', 0) > 0:
                return 1 # Indicate error if sync had issues.
        except Exception as e:
            print(f"Error synchronizing neurons: {str(e)}", file=sys.stderr)
            return 1 # Indicate error.
    
    return 0