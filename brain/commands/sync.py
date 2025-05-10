"""
Handler for the brain sync command.

Implements the 'brain sync' command which synchronizes neurons from brain repositories.
"""

import os
import sys
import argparse
from typing import List, Dict, Any, Optional

from brain.config import (
    get_current_repo_neurons_config, 
    NeuronsConfigError
)
from brain.sync import sync_all_neurons, sync_neuron
from brain.utils import find_mapping_for_neuron


def handle_sync(args: List[str]) -> int:
    """
    Description:
        Handle the 'brain sync' command which synchronizes neurons from repositories.
        This function parses arguments, loads configuration, and manages the 
        synchronization process for either specific neurons or all neurons.
    
    Parameters:
        args (List[str]): Command line arguments passed to the 'brain sync' command.

    Returns:
        exit_code (int): Exit code where 0 indicates success and 1 indicates failure.
    """
    # --------------------------------------------------------------
    # STEP 1: Set up argument parser and parse command arguments.
    # --------------------------------------------------------------
    # Create argument parser with description
    parser = argparse.ArgumentParser(
        description="Synchronize neurons from brain repositories",
        prog="brain sync"
    )
    
    # Add argument for specific neurons
    parser.add_argument(
        'neurons',
        nargs='*',
        help="Specific neurons to sync (default: all)"
    )
    
    # Add reset flag argument
    parser.add_argument(
        '--reset',
        action='store_true',
        help="Force reset local modifications"
    )
    
    # Add strategy selection argument
    parser.add_argument(
        '--strategy',
        choices=['prompt', 'prefer_brain', 'prefer_local'],
        help="Conflict resolution strategy (overrides .neurons setting)"
    )
    
    # Parse the provided arguments
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # Return error code if argument parsing fails
        return 1
    
    # Extract arguments into variables
    specific_neurons = parsed_args.neurons
    force_reset = parsed_args.reset
    strategy = parsed_args.strategy
    
    # --------------------------------------------------------------
    # STEP 2: Load neurons configuration from the current repository.
    # --------------------------------------------------------------
    # Attempt to load the neurons config file
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            print("ERROR: No .neurons file found.")
            return 1
    except NeuronsConfigError as e:
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Apply command-line options to the configuration.
    # --------------------------------------------------------------
    # ===============
    # Sub step 3.1: Apply custom conflict resolution strategy if specified.
    # ===============
    if strategy:
        # Ensure SYNC_POLICY exists in the config
        if 'SYNC_POLICY' not in neurons_config:
            neurons_config['SYNC_POLICY'] = {}
        # Set the conflict strategy based on command line argument
        neurons_config['SYNC_POLICY']['CONFLICT_STRATEGY'] = strategy
    
    # ===============
    # Sub step 3.2: Apply force reset option if specified.
    # ===============
    if force_reset:
        # Ensure SYNC_POLICY exists in the config
        if 'SYNC_POLICY' not in neurons_config:
            neurons_config['SYNC_POLICY'] = {}
        # Enable local modifications flag in the config
        neurons_config['SYNC_POLICY']['ALLOW_LOCAL_MODIFICATIONS'] = True
    
    # --------------------------------------------------------------
    # STEP 4: Synchronize neurons based on command arguments.
    # --------------------------------------------------------------
    # ===============
    # Sub step 4.1: Handle specific neurons if provided.
    # ===============
    if specific_neurons:
        print(f"Synchronizing {len(specific_neurons)} specific neurons...")
        
        results = []
        for neuron_path in specific_neurons:
            # Find the mapping configuration for this neuron
            mapping = find_mapping_for_neuron(neurons_config, neuron_path)
            if not mapping:
                print(f"ERROR: No mapping found for neuron: {neuron_path}")
                continue
            
            # Extract mapping details
            brain_id = mapping.get('brain_id')
            source = mapping.get('source')
            dest = mapping.get('destination')
            
            # Perform the actual synchronization
            result = sync_neuron(neurons_config, brain_id, source, dest)
            results.append(result)
            
            # Display the result of this neuron's synchronization
            if result['status'] == 'success':
                action = result.get('action', 'synced')
                print(f"  {dest}: {action}")
            else:
                message = result.get('message', 'Unknown error')
                print(f"  {dest}: ERROR - {message}")
    # ===============
    # Sub step 4.2: Handle synchronization of all neurons.
    # ===============
    else:
        print("Synchronizing all neurons from brain repositories...")
        
        # Sync all neurons using the loaded configuration
        results = sync_all_neurons(neurons_config)
    
    # --------------------------------------------------------------
    # STEP 5: Process and display results summary.
    # --------------------------------------------------------------
    # Initialize counters for different result categories
    status_counts = {'success': 0, 'error': 0, 'unchanged': 0, 'updated': 0, 'added': 0}
    
    # Count results by status and action
    for result in results:
        status = result.get('status')
        action = result.get('action')
        
        # Increment status count if status exists
        if status:
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Increment action count if action exists
        if action:
            status_counts[action] = status_counts.get(action, 0) + 1
    
    # Display summary of synchronization results
    print("\nNeuron synchronization complete:")
    print(f"  {status_counts.get('success', 0)} neurons processed successfully")
    print(f"  {status_counts.get('added', 0)} neurons added")
    print(f"  {status_counts.get('updated', 0)} neurons updated")
    print(f"  {status_counts.get('unchanged', 0)} neurons unchanged")
    
    # --------------------------------------------------------------
    # STEP 6: Handle and display any errors that occurred.
    # --------------------------------------------------------------
    # Filter results to find any errors
    errors = [r for r in results if r.get('status') == 'error']
    if errors:
        print(f"\n{len(errors)} errors occurred:")
        for error in errors:
            # Extract error details
            mapping = error.get('mapping', {})
            message = error.get('message', 'Unknown error')
            brain_id = mapping.get('brain_id', 'unknown')
            dest = mapping.get('destination', 'unknown')
            # Display detailed error information
            print(f"  Error in {brain_id}::{dest}: {message}")
    
    # Return appropriate exit code based on whether errors occurred
    return 0 if not errors else 1