"""
Handler for the brain remove-neuron command.

Implements the 'brain remove-neuron' command which removes a neuron mapping.
"""

import os
import argparse
from typing import List

from brain.config import (
    get_current_repo_neurons_config,
    save_neurons_config,
    NeuronsConfigError
)
from brain.utils import find_mapping_for_neuron


def handle_remove_neuron(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain remove-neuron' command which removes a neuron mapping from the configuration.
        Optionally deletes the neuron file if requested.
    
    Parameters:
        args (List[str]): Command line arguments passed to the remove-neuron command.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (1).
    """
    # --------------------------------------------------------------
    # STEP 1: Set up and parse command line arguments.
    # --------------------------------------------------------------
    # Create argument parser with description.
    parser = argparse.ArgumentParser(
        description="Remove a neuron mapping",
        prog="brain remove-neuron"
    )
    
    # Add required argument for neuron path.
    parser.add_argument(
        'neuron_path',
        help="Path to the neuron file to remove"
    )
    
    # Add optional flag to delete the file.
    parser.add_argument(
        '--delete',
        action='store_true',
        help="Delete the neuron file after removing the mapping"
    )
    
    # ===============
    # Sub step 1.1: Parse the provided arguments.
    # ===============
    # Attempt to parse arguments and handle parser errors.
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # Return failure if argument parsing fails.
        return 1
    
    # Extract argument values for easier access.
    neuron_path = parsed_args.neuron_path
    delete_file = parsed_args.delete
    
    # --------------------------------------------------------------
    # STEP 2: Load neuron configuration from the repository.
    # --------------------------------------------------------------
    # Attempt to load the neurons configuration file.
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            print("ERROR: No .neurons file found.")
            return 1
    except NeuronsConfigError as e:
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Find and remove the neuron mapping.
    # --------------------------------------------------------------
    # Find the mapping entry for the specified neuron path.
    mapping = find_mapping_for_neuron(neurons_config, neuron_path)
    if not mapping:
        print(f"ERROR: No mapping found for neuron: {neuron_path}")
        return 1
    
    # ===============
    # Sub step 3.1: Extract mapping details for logging.
    # ===============
    # Get important fields from the mapping for confirmation message.
    brain_id = mapping.get('brain_id')
    source = mapping.get('source')
    dest = mapping.get('destination')
    
    # ===============
    # Sub step 3.2: Remove the mapping from configuration.
    # ===============
    # Filter out the mapping to be removed from the MAP list.
    neurons_config['MAP'] = [m for m in neurons_config.get('MAP', []) if m != mapping]
    
    # --------------------------------------------------------------
    # STEP 4: Save updated configuration and cleanup.
    # --------------------------------------------------------------
    # Save the modified neurons configuration.
    try:
        save_neurons_config(neurons_config)
        print(f"Removed neuron mapping: {brain_id}::{source} → {dest}")
    except NeuronsConfigError as e:
        print(f"Error saving neurons configuration: {str(e)}")
        return 1
    
    # ===============
    # Sub step 4.1: Delete the neuron file if requested.
    # ===============
    # Check if file deletion was requested and file exists.
    if delete_file and os.path.exists(neuron_path):
        try:
            # Delete the file from the filesystem.
            os.unlink(neuron_path)
            print(f"Deleted neuron file: {neuron_path}")
        except Exception as e:
            print(f"Error deleting neuron file: {str(e)}")
            return 1
    
    # Return success code.
    return 0