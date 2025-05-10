"""
Handler for the brain brain-init command.

Implements the 'brain brain-init' command which initializes a repository as a brain.
"""

import os
import argparse
from typing import List, Dict, Any

from brain.config import save_brain_config, BrainConfigError


def handle_brain_init(args: List[str]) -> int:
    """
    Description:
        Handle the brain brain-init command which initializes a repository as a brain.
    
    Parameters:
        args (List[str]): Command line arguments passed to the brain-init command.

    Returns:
        exit_code (int): Exit code (0 for success, 1 for failure).
    """
    # --------------------------------------------------------------
    # STEP 1: Set up argument parser for command line arguments.
    # --------------------------------------------------------------
    # Create argument parser with description and program name.
    parser = argparse.ArgumentParser(
        description="Initialize a repository as a brain",
        prog="brain brain-init"
    )
    
    parser.add_argument(
        '--id',
        required=True,
        help="Unique identifier for this brain"
    )
    
    parser.add_argument(
        '--description',
        default="Shared code repository",
        help="Description of this brain"
    )
    
    parser.add_argument(
        '--export',
        action='append',
        default=[],
        help="Path patterns to export (format: path=permission)"
    )
    
    # --------------------------------------------------------------
    # STEP 2: Parse the command line arguments.
    # --------------------------------------------------------------
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit as e: # Raised by argparse on error (e.g. missing required arg) or for --help
        # Let SystemExit propagate for test runners or higher-level handlers like cli.py
        # to catch it correctly. Tests using assertRaises(SystemExit) rely on this.
        raise e

    # --------------------------------------------------------------
    # STEP 3: Check if a brain configuration already exists.
    # --------------------------------------------------------------
    if os.path.exists('.brain'):
        # Notify user that configuration already exists and provide guidance.
        print("Brain configuration file '.brain' already exists. Use --force to overwrite (not yet implemented).")
        return 1
    
    # --------------------------------------------------------------
    # STEP 4: Create brain configuration dictionary with provided parameters.
    # --------------------------------------------------------------
    brain_config: Dict[str, Any] = {
        'ID': parsed_args.id,
        'DESCRIPTION': parsed_args.description,
        'EXPORT': {}
    }
    
    # --------------------------------------------------------------
    # STEP 5: Process export parameters if provided.
    # --------------------------------------------------------------
    if parsed_args.export:
        # ===============
        # Sub step 5.1: Iterate through each export entry and parse it.
        # ===============
        for export_entry in parsed_args.export:
            if '=' in export_entry:
                # Split the entry into path and permission if separator exists.
                path, permission = export_entry.split('=', 1)
                path = path.strip()
                permission = permission.strip()
            else:
                # Use default permission if only path is provided.
                path = export_entry.strip()
                permission = 'readonly' # Default permission if not specified
            
            # ===============
            # Sub step 5.2: Validate the permission value.
            # ===============
            if permission not in ['readonly', 'readwrite']:
                # Report invalid permission and exit with error code.
                print(f"Invalid permission: {permission} for path '{path}'")
                print("Valid permissions: readonly, readwrite")
                return 1
            
            # ===============
            # Sub step 5.3: Add the validated path and permission to configuration.
            # ===============
            brain_config['EXPORT'][path] = permission
    
    # --------------------------------------------------------------
    # STEP 6: Save the brain configuration and provide feedback.
    # --------------------------------------------------------------
    try:
        # Save configuration to the .brain file.
        save_brain_config(brain_config)
        # Provide success message to the user.
        print(f"Brain repository initialized with ID: {parsed_args.id}")
        print(f"Edit .brain file to configure exported neurons.")
        return 0
    except BrainConfigError as e:
        # Handle configuration save errors by displaying message.
        print(f"Error saving brain configuration: {str(e)}")
        return 1