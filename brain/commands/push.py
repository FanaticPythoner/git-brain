"""
Handler for the brain push command.

Implements the 'brain push' command which pushes to the origin repository
with special handling for neuron files.
"""

import os
import sys
import subprocess
from typing import List, Dict, Any, Optional

from brain.config import get_current_repo_neurons_config, NeuronsConfigError
from brain.sync import get_modified_neurons, export_neurons_to_brain


def handle_push(args: List[str]) -> int:
    """
    Description:
        Handles the brain push command, which pushes to the origin repository
        with special handling for neuron files. It checks for modified neurons,
        applies neuron push policies, and optionally pushes modified neurons
        to brain repositories.
    
    Parameters:
        args (List[str]): Command line arguments including standard git push arguments
                          and special flags like --force, -f, and --push-to-brain.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
    """
    # --------------------------------------------------------------
    # STEP 1: Extract special flags and filter arguments.
    # --------------------------------------------------------------
    # Extract special flags from the command arguments.
    force = '--force' in args or '-f' in args
    push_to_brain = '--push-to-brain' in args
    
    # Remove our custom flags before passing to git.
    filtered_args = [arg for arg in args if arg != '--push-to-brain']
    
    # --------------------------------------------------------------
    # STEP 2: Check for .neurons file and handle configurations.
    # --------------------------------------------------------------
    # Check for .neurons file and load configuration.
    try:
        neurons_config = get_current_repo_neurons_config()
        if neurons_config:
            # ===============
            # Sub step 2.1: Check for modified neurons.
            # ===============
            # Get a list of neurons that have been modified locally.
            modified_neurons = get_modified_neurons(neurons_config)
            
            # ===============
            # Sub step 2.2: Apply neuron push policy.
            # ===============
            # Get the synchronization policy settings from configuration.
            sync_policy = neurons_config.get('SYNC_POLICY', {})
            allow_local_modifications = sync_policy.get('ALLOW_LOCAL_MODIFICATIONS', False)
            allow_push_to_brain = sync_policy.get('ALLOW_PUSH_TO_BRAIN', False)
            
            # ===============
            # Sub step 2.3: Check if local modifications are allowed.
            # ===============
            if modified_neurons and not allow_local_modifications and not force:
                # Display error message for locally modified neurons.
                print("ERROR: You have modified neurons that should not be changed locally:")
                for neuron in modified_neurons:
                    brain_id = neuron.get('brain_id', 'unknown')
                    dest = neuron.get('destination', 'unknown')
                    print(f"  - {dest} (from brain: {brain_id})")
                
                # Display options for the user to proceed.
                print("\nOptions:")
                print("  1. Use --force to push anyway (not recommended)")
                print("  2. Reset neurons: brain sync --reset")
                print("  3. Enable local modifications: Set ALLOW_LOCAL_MODIFICATIONS=true in .neurons")
                
                return 1
            
            # ===============
            # Sub step 2.4: Check if pushing to brain is allowed.
            # ===============
            if push_to_brain:
                # Verify that pushing to brain repositories is allowed by configuration.
                if not allow_push_to_brain:
                    print("ERROR: Pushing to brain repositories is not allowed by configuration")
                    print("Set ALLOW_PUSH_TO_BRAIN=true in .neurons or use --force")
                    return 1
    except NeuronsConfigError as e:
        # Handle errors in loading neurons configuration.
        print(f"Error loading neurons configuration: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Execute standard git push.
    # --------------------------------------------------------------
    # Run the standard git push command with filtered arguments.
    result = subprocess.run(['git', 'push'] + filtered_args)
    
    # Check if the git push was successful.
    if result.returncode != 0:
        return result.returncode
    
    # --------------------------------------------------------------
    # STEP 4: Push neurons to brain repositories if requested.
    # --------------------------------------------------------------
    # If push successful and push-to-brain requested, push neurons to brains.
    if push_to_brain and neurons_config and modified_neurons:
        print("\nPushing modified neurons to brain repositories...")
        
        try:
            # ===============
            # Sub step 4.1: Export modified neurons to brain repositories.
            # ===============
            # Export the modified neurons to their brain repositories.
            export_results = export_neurons_to_brain(neurons_config, modified_neurons)
            
            # ===============
            # Sub step 4.2: Process and display export results.
            # ===============
            # Initialize success flag to track overall operation success.
            success = True
            for brain_id, result in export_results.items():
                status = result.get('status')
                message = result.get('message', '')
                
                # Display different messages based on export success or failure.
                if status == 'success':
                    exported = result.get('exported_neurons', [])
                    if exported:
                        print(f"  {brain_id}: {len(exported)} neurons exported successfully")
                    else:
                        print(f"  {brain_id}: {message}")
                else:
                    print(f"  {brain_id}: ERROR - {message}")
                    success = False
            
            # Return success (0) or failure (1) exit code.
            return 0 if success else 1
        
        except Exception as e:
            # Handle any exceptions during the export process.
            print(f"Error exporting neurons to brain: {str(e)}")
            return 1
    
    # Return success exit code when no further actions are needed.
    return 0