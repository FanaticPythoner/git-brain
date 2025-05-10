"""
Handler for the brain add-neuron command.

Implements the 'brain add-neuron' command which adds a neuron mapping from a brain.
"""

import os
from typing import List

from brain.config import (
    get_current_repo_neurons_config,
    save_neurons_config,
    NeuronsConfigError
)
from brain.utils import parse_mapping
from brain.git import temp_clone_repo, GitError
from brain.sync import sync_neuron


def handle_add_neuron(args: List[str]) -> int:
    """
    Description:
        Handle the brain add-neuron command, which adds a mapping from a source path 
        in a brain repository to a destination path in the current repository.
    
    Parameters:
        args (List[str]): Command line arguments containing the mapping string in the format
                         <brain_id>::<source_path>::<destination_path>.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1).
    """
    # --------------------------------------------------------------
    # STEP 1: Validate and parse input arguments.
    # --------------------------------------------------------------
    # Check if the required mapping argument is provided.
    if len(args) < 1:
        print("ERROR: Missing required argument")
        print("Usage: brain add-neuron <mapping>")
        print("Format: <brain_id>::<source_path>::<destination_path>")
        return 1
    
    # Parse the mapping string into components.
    mapping_str = args[0]
    
    try:
        brain_id, source_path, dest_path = parse_mapping(mapping_str)
    except ValueError:
        print("ERROR: Invalid mapping format")
        print("Format: <brain_id>::<source_path>::<destination_path>")
        return 1
    
    # --------------------------------------------------------------
    # STEP 2: Load neurons configuration from current repository.
    # --------------------------------------------------------------
    # Retrieve the neurons configuration file or display error if not found.
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            print("ERROR: No .neurons file found. Use 'brain add-brain' first.")
            return 1
    except NeuronsConfigError as e:
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Verify brain exists and retrieve its configuration.
    # --------------------------------------------------------------
    # Check if the specified brain ID exists in the configuration.
    brains = neurons_config.get('BRAINS', {})
    if brain_id not in brains:
        print(f"ERROR: Brain '{brain_id}' not found in configuration")
        print("Available brains:")
        for brain in brains:
            print(f"  - {brain}")
        return 1
    
    # Extract repository details for the specified brain.
    brain_config = brains[brain_id]
    remote_url = brain_config.get('REMOTE')
    branch = brain_config.get('BRANCH', 'main')
    
    # --------------------------------------------------------------
    # STEP 4: Verify source path exists in the brain repository.
    # --------------------------------------------------------------
    print(f"Verifying source path in brain: {source_path}")
    
    try:
        # ===============
        # Sub step 4.1: Clone brain repository to temporary directory.
        # ===============
        # Create a temporary clone to verify the source path.
        temp_dir = temp_clone_repo(remote_url, branch)
        
        try:
            # ===============
            # Sub step 4.2: Check if source path exists in cloned repository.
            # ===============
            # Construct the full path and verify it exists.
            source_full_path = os.path.join(temp_dir, source_path)
            if not os.path.exists(source_full_path):
                print(f"ERROR: Source path '{source_path}' not found in brain repository")
                return 1
            
            # ===============
            # Sub step 4.3: Add mapping to configuration if not duplicate.
            # ===============
            # Initialize the MAP list if it doesn't exist yet.
            if 'MAP' not in neurons_config:
                neurons_config['MAP'] = []
            
            # Check for existing identical mapping to prevent duplicates.
            for mapping in neurons_config['MAP']:
                if (
                    mapping.get('brain_id') == brain_id and
                    mapping.get('source') == source_path and
                    mapping.get('destination') == dest_path
                ):
                    print(f"Mapping already exists: {brain_id}::{source_path}::{dest_path}")
                    return 0
            
            # Add the new mapping to the configuration.
            neurons_config['MAP'].append({
                'brain_id': brain_id,
                'source': source_path,
                'destination': dest_path
            })
            
            # Persist the updated configuration to disk.
            save_neurons_config(neurons_config)
            
            print(f"Added neuron mapping: {brain_id}::{source_path} → {dest_path}")
        finally:
            # ===============
            # Sub step 4.4: Clean up temporary repository.
            # ===============
            # Remove the temporary directory regardless of outcome.
            import shutil
            shutil.rmtree(temp_dir)
    except GitError as e:
        print(f"ERROR: Failed to access brain repository: {str(e)}")
        return 1
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 5: Synchronize the newly added neuron from the brain.
    # --------------------------------------------------------------
    print("Syncing neuron from brain...")
    
    try:
        # Perform the actual synchronization of the neuron.
        result = sync_neuron(neurons_config, brain_id, source_path, dest_path)
        
        # Process the synchronization result and report status.
        if result['status'] == 'success':
            action = result.get('action', 'synced')
            print(f"Neuron successfully {action}")
            return 0
        else:
            print(f"Error syncing neuron: {result.get('message', 'Unknown error')}")
            return 1
    except Exception as e:
        print(f"Error syncing neuron: {str(e)}")
        return 1