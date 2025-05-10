"""
Handler for the brain list command.

Implements the 'brain list' command which lists neurons in the current repository.
"""

import os
import argparse
from typing import List

from brain.config import (
    get_current_repo_neurons_config, 
    NeuronsConfigError
)
from brain.git import is_file_modified
from brain.utils import format_size


def handle_list(args: List[str]) -> int:
    """
    Description:
        Handles the 'brain list' command which displays all neurons in the current repository.
        Supports filtering by brain and verbose output options.
    
    Parameters:
        args (List[str]): Command line arguments passed to the command.

    Returns:
        exit_code (int): 0 for success, 1 for errors.
    """
    # --------------------------------------------------------------
    # STEP 1: Set up and parse command line arguments.
    # --------------------------------------------------------------
    # Create argument parser with description and program name.
    parser = argparse.ArgumentParser(
        description="List neurons in the current repository",
        prog="brain list"
    )
    
    # Add verbose flag for detailed output.
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Show detailed information"
    )
    
    # Add brain filter option.
    parser.add_argument(
        '--brain',
        help="Filter by brain"
    )
    
    # Parse the provided arguments.
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # Return error code if argument parsing fails.
        return 1
    
    # Extract argument values for later use.
    verbose = parsed_args.verbose
    filter_brain = parsed_args.brain
    
    # --------------------------------------------------------------
    # STEP 2: Load and validate neuron configuration.
    # --------------------------------------------------------------
    # Attempt to load the neurons config from the current repository.
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            print("ERROR: No .neurons file found.")
            return 1
    except NeuronsConfigError as e:
        # Handle configuration errors with descriptive message.
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Extract brain and mapping information.
    # --------------------------------------------------------------
    # Get brain definitions from the config.
    brains = neurons_config.get('BRAINS', {})
    
    # Get neuron mappings from the config.
    mappings = neurons_config.get('MAP', [])
    
    # --------------------------------------------------------------
    # STEP 4: Apply filtering if requested.
    # --------------------------------------------------------------
    # Filter mappings by brain if specified.
    if filter_brain:
        # Keep only mappings that match the specified brain.
        mappings = [m for m in mappings if m.get('brain_id') == filter_brain]
        
        # Early return if no neurons match the filter.
        if not mappings:
            print(f"No neurons found for brain: {filter_brain}")
            return 0
    
    # --------------------------------------------------------------
    # STEP 5: Display header information.
    # --------------------------------------------------------------
    # Display header with total count and optionally brain details.
    if verbose:
        # Verbose mode includes brain definitions.
        print(f"Neurons in repository: {len(mappings)}")
        print("\nBrains:")
        for brain_id, brain_config in brains.items():
            print(f"  {brain_id}:")
            print(f"    Remote: {brain_config.get('REMOTE')}")
            print(f"    Branch: {brain_config.get('BRANCH', 'main')}")
        print("\nNeurons:")
    else:
        # Simple mode just shows the count.
        print(f"Neurons in repository: {len(mappings)}")
        print()
    
    # --------------------------------------------------------------
    # STEP 6: Display neuron details.
    # --------------------------------------------------------------
    # Iterate through each neuron mapping.
    for mapping in mappings:
        brain_id = mapping.get('brain_id')
        source = mapping.get('source')
        dest = mapping.get('destination')
        
        # ===============
        # Sub step 6.1: Check neuron status.
        # ===============
        # Determine if the neuron file exists and has modifications.
        exists = os.path.exists(dest)
        modified = exists and is_file_modified(dest)
        
        # ===============
        # Sub step 6.2: Calculate neuron size.
        # ===============
        # Initialize size counter.
        size = 0
        if exists:
            try:
                # Handle both file and directory neurons.
                if os.path.isdir(dest):
                    # For directories, sum up the size of all contained files.
                    for root, dirs, files in os.walk(dest):
                        for file in files:
                            size += os.path.getsize(os.path.join(root, file))
                else:
                    # For single files, get the direct size.
                    size = os.path.getsize(dest)
            except:
                # Silently handle any errors in size calculation.
                pass
        
        # ===============
        # Sub step 6.3: Display neuron information.
        # ===============
        # Format and print information based on verbosity.
        if verbose:
            # Detailed output for verbose mode.
            print(f"  {dest}:")
            print(f"    Brain: {brain_id}")
            print(f"    Source: {source}")
            print(f"    Status: {'Modified' if modified else ('Missing' if not exists else 'OK')}")
            print(f"    Size: {format_size(size)}")
            print()
        else:
            # Simple output with status indicators.
            status = "* " if modified else ("! " if not exists else "  ")
            print(f"{status}{dest} ({brain_id})")
    
    # Return success code.
    return 0