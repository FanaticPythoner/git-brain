"""
Handler for the brain pull command.

Implements the 'brain pull' command which pulls from the origin repository 
and synchronizes neurons from brain repositories.
"""

import os
import sys
import subprocess
from typing import List, Dict, Any, Optional

from brain.config import get_current_repo_neurons_config, NeuronsConfigError
from brain.sync import sync_all_neurons


def handle_pull(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain pull' command by performing a standard git pull operation
        followed by synchronization of neurons according to the repository's
        configuration. The function manages error handling, reporting, and user
        notifications throughout the process.
    
    Parameters:
        args (List[str]): Command line arguments to be passed to the git pull command,
                         such as remote names, branch names, or git pull options.

    Returns:
        exit_code (int): Exit code where 0 indicates successful completion and
                        non-zero values indicate various error conditions.
    """
    # --------------------------------------------------------------
    # STEP 1: Execute standard git pull command.
    # --------------------------------------------------------------
    # Run git pull with any provided arguments and capture the result.
    result = subprocess.run(['git', 'pull'] + args)
    
    # Exit early if git pull failed.
    if result.returncode != 0:
        return result.returncode
    
    # --------------------------------------------------------------
    # STEP 2: Check for neurons configuration.
    # --------------------------------------------------------------
    # Attempt to load the neurons configuration file.
    try:
        neurons_config = get_current_repo_neurons_config()
        # Return successfully if no neurons configuration exists.
        if not neurons_config:
            return 0  # No neurons to sync
    except NeuronsConfigError as e:
        # Display error message if neurons configuration cannot be loaded.
        print(f"Error loading neurons configuration: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Determine if neurons synchronization should be performed.
    # --------------------------------------------------------------
    # Extract synchronization policy from configuration.
    sync_policy = neurons_config.get('SYNC_POLICY', {})
    auto_sync = sync_policy.get('AUTO_SYNC_ON_PULL', True)
    
    # Honor the auto-sync setting.
    if not auto_sync:
        print("\nNeuron auto-sync is disabled. Use 'brain sync' to update neurons.")
        return 0
    
    # --------------------------------------------------------------
    # STEP 4: Synchronize neurons and report results.
    # --------------------------------------------------------------
    print("\nSynchronizing neurons from brain repositories...")
    
    try:
        # ===============
        # Sub step 4.1: Perform the synchronization.
        # ===============
        # Synchronize all neurons according to the configuration.
        results = sync_all_neurons(neurons_config)
        
        # ===============
        # Sub step 4.2: Aggregate statistics about the sync operation.
        # ===============
        # Initialize counters for different result types.
        status_counts = {'success': 0, 'error': 0, 'unchanged': 0, 'updated': 0, 'added': 0}
        
        # Iterate through results and count by status and action.
        for result in results:
            status = result.get('status')
            action = result.get('action')
            
            # Update status counts.
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Update action counts.
            if action:
                status_counts[action] = status_counts.get(action, 0) + 1
        
        # ===============
        # Sub step 4.3: Display summary of synchronization results.
        # ===============
        # Print overview of sync operation.
        print("\nNeuron synchronization complete:")
        print(f"  {status_counts.get('success', 0)} neurons processed successfully")
        print(f"  {status_counts.get('added', 0)} neurons added")
        print(f"  {status_counts.get('updated', 0)} neurons updated")
        print(f"  {status_counts.get('unchanged', 0)} neurons unchanged")
        
        # ===============
        # Sub step 4.4: Report any errors that occurred.
        # ===============
        # Filter results to find errors.
        errors = [r for r in results if r.get('status') == 'error']
        if errors:
            # Print error summary and details.
            print(f"\n{len(errors)} errors occurred:")
            for error in errors:
                mapping = error.get('mapping', {})
                message = error.get('message', 'Unknown error')
                brain_id = mapping.get('brain_id', 'unknown')
                dest = mapping.get('destination', 'unknown')
                print(f"  Error in {brain_id}::{dest}: {message}")
        
        # Return success code if no errors, otherwise error code.
        return 0 if not errors else 1
    
    except Exception as e:
        # Handle unexpected exceptions during synchronization.
        print(f"Error synchronizing neurons: {str(e)}")
        return 1