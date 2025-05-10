"""
Handler for the brain export command.

Implements the 'brain export' command which exports neurons to brain repositories.
This module provides functionality to export neurons based on user specifications,
with validation against repository configuration policies.
"""

import os
import sys
import argparse
from typing import List, Dict, Any, Optional

from brain.config import (
    get_current_repo_neurons_config, 
    NeuronsConfigError
)
from brain.sync import get_modified_neurons, export_neurons_to_brain
from brain.utils import find_mapping_for_neuron


def handle_export(args: List[str]) -> int:
    """
    Description:
        Handle the brain export command by parsing arguments, validating configuration,
        identifying neurons to export, and performing the export operation.
    
    Parameters:
        args (List[str]): Command-line arguments passed to the export command.

    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero).
    """
    # --------------------------------------------------------------
    # STEP 1: Set up and parse command-line arguments.
    # --------------------------------------------------------------
    # Create argument parser for the export command.
    parser = argparse.ArgumentParser(
        description="Export neurons to brain repositories",
        prog="brain export"
    )
    
    # Add arguments for neuron selection.
    parser.add_argument(
        'neurons',
        nargs='*',
        help="Specific neurons to export (default: all modified)"
    )
    
    # Add option to force export regardless of configuration settings.
    parser.add_argument(
        '--force',
        action='store_true',
        help="Force export even if not allowed by configuration"
    )
    
    # Parse the command-line arguments.
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        # Return error code if argument parsing fails.
        return 1
    
    # Extract parsed arguments for later use.
    specific_neurons = parsed_args.neurons
    force = parsed_args.force
    
    # --------------------------------------------------------------
    # STEP 2: Load neurons configuration.
    # --------------------------------------------------------------
    # Attempt to load the neurons configuration from the current repository.
    try:
        neurons_config = get_current_repo_neurons_config()
        if not neurons_config:
            print("ERROR: No .neurons file found.")
            return 1
    except NeuronsConfigError as e:
        # Handle configuration loading errors.
        print(f"ERROR: {str(e)}")
        return 1
    
    # --------------------------------------------------------------
    # STEP 3: Validate export permissions.
    # --------------------------------------------------------------
    # Check if exporting to brain repositories is allowed by configuration.
    sync_policy = neurons_config.get('SYNC_POLICY', {})
    allow_push_to_brain = sync_policy.get('ALLOW_PUSH_TO_BRAIN', False)
    
    if not allow_push_to_brain and not force:
        # Prevent export if not allowed and force flag is not set.
        print("ERROR: Exporting to brain repositories is not allowed by configuration")
        print("Set ALLOW_PUSH_TO_BRAIN=true in .neurons or use --force")
        return 1
    
    # --------------------------------------------------------------
    # STEP 4: Determine which neurons to export.
    # --------------------------------------------------------------
    if specific_neurons:
        # ===============
        # Sub step 4.1: Handle specifically requested neurons.
        # ===============
        neurons_to_export = []
        
        for neuron_path in specific_neurons:
            # Find mapping configuration for the specified neuron.
            mapping = find_mapping_for_neuron(neurons_config, neuron_path)
            if not mapping:
                print(f"ERROR: No mapping found for neuron: {neuron_path}")
                continue
            
            # Add valid neuron mapping to export list.
            neurons_to_export.append(mapping)
    else:
        # ===============
        # Sub step 4.2: Export all modified neurons if none specifically requested.
        # ===============
        # Get all neurons that have been modified since last sync.
        neurons_to_export = get_modified_neurons(neurons_config)
    
    # Exit early if no neurons to export.
    if not neurons_to_export:
        print("No neurons to export")
        return 0
    
    # --------------------------------------------------------------
    # STEP 5: Display export information and confirm with user.
    # --------------------------------------------------------------
    # Show summary of neurons that will be exported.
    print(f"Exporting {len(neurons_to_export)} neurons to brain repositories:")
    for neuron in neurons_to_export:
        brain_id = neuron.get('brain_id')
        dest = neuron.get('destination')
        print(f"  {dest} → {brain_id}")
    
    # Request user confirmation unless force flag is set.
    if not force:
        confirm = input("\nContinue with export? (y/N): ")
        if confirm.lower() != 'y':
            print("Export cancelled")
            return 0
    
    # --------------------------------------------------------------
    # STEP 6: Perform export operation.
    # --------------------------------------------------------------
    try:
        # ===============
        # Sub step 6.1: Prepare export configuration.
        # ===============
        # Override configuration to allow export for this operation.
        export_config = neurons_config.copy()
        export_config['SYNC_POLICY'] = export_config.get('SYNC_POLICY', {}).copy()
        export_config['SYNC_POLICY']['ALLOW_PUSH_TO_BRAIN'] = True
        
        # ===============
        # Sub step 6.2: Export neurons and collect results.
        # ===============
        export_results = export_neurons_to_brain(export_config, neurons_to_export)
        
        # ===============
        # Sub step 6.3: Process and display export results.
        # ===============
        # Track overall success status.
        success = True
        for brain_id, result in export_results.items():
            status = result.get('status')
            message = result.get('message', '')
            
            if status == 'success':
                # Handle successful export to a brain repository.
                exported = result.get('exported_neurons', [])
                if exported:
                    print(f"  {brain_id}: {len(exported)} neurons exported successfully")
                else:
                    print(f"  {brain_id}: {message}")
            else:
                # Handle failed export to a brain repository.
                print(f"  {brain_id}: ERROR - {message}")
                success = False
        
        # Return appropriate exit code based on overall success.
        return 0 if success else 1
    
    except Exception as e:
        # Handle unexpected errors during export.
        print(f"Error exporting neurons: {str(e)}")
        return 1