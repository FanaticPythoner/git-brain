"""
Command-line interface for the Brain Git extension.

This module provides the main entry point for the 'brain' command,
parsing the arguments and dispatching to the appropriate handler.
"""

import sys
import subprocess

# Import command handlers
from brain.commands.brain_init import handle_brain_init
from brain.commands.add_brain import handle_add_brain
from brain.commands.add_neuron import handle_add_neuron
from brain.commands.remove_neuron import handle_remove_neuron
from brain.commands.sync import handle_sync
from brain.commands.export import handle_export
from brain.commands.list import handle_list
from brain.commands.pull import handle_pull
from brain.commands.push import handle_push
from brain.commands.status import handle_status
from brain.commands.clone import handle_clone
from brain.commands.checkout import handle_checkout
from brain.commands.init import handle_init


def print_usage_and_exit() -> None:
    """
    Description:
        Print usage information for the Brain Git extension and exit the program.
        Displays available commands including both standard Git commands and
        Brain-specific commands.
    
    Parameters:
        None
        
    Returns:
        None: This function exits the program with status code 1
    """
    print("Usage: brain <command> [args]")
    print("\nStandard Git commands:")
    print("  All standard Git commands are supported (pull, push, commit, etc.)")
    print("\nBrain-specific commands:")
    print("  brain-init         Initialize a brain repository")
    print("  add-brain          Add a brain to the current repository")
    print("  add-neuron         Add a neuron mapping from a brain")
    print("  remove-neuron      Remove a neuron mapping")
    print("  sync               Synchronize neurons from brain repositories")
    print("  export             Export neuron changes back to brain repositories")
    print("  list               List neurons in the current repository")
    print("\nFor more information, see the documentation or run 'brain <command> --help'")
    sys.exit(1)


def main() -> int:
    """
    Description:
        Main entry point for the brain command. Parses command-line arguments 
        and dispatches to the appropriate handler based on the provided command.
        Supports both brain-specific commands and standard Git commands with
        special handling, and passes through other commands directly to Git.
    
    Parameters:
        None: Arguments are read directly from sys.argv
        
    Returns:
        exit_code (int): Exit code indicating success (0) or failure (non-zero)
    """
    # --------------------------------------------------------------
    # STEP 1: Parse command-line arguments.
    # --------------------------------------------------------------
    if len(sys.argv) < 2:
        # Display usage information if no command is provided.
        print_usage_and_exit()
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    # --------------------------------------------------------------
    # STEP 2: Define command mappings.
    # --------------------------------------------------------------
    # ===============
    # Sub step 2.1: Define brain-specific commands.
    # ===============
    # Map brain-specific command names to their handler functions.
    brain_commands = {
        'brain-init': handle_brain_init,
        'add-brain': handle_add_brain,
        'add-neuron': handle_add_neuron,
        'remove-neuron': handle_remove_neuron,
        'sync': handle_sync,
        'export': handle_export,
        'list': handle_list
    }
    
    # ===============
    # Sub step 2.2: Define Git commands that need special handling.
    # ===============
    # Map Git commands that require brain-specific processing to their handler functions.
    special_commands = {
        'pull': handle_pull,
        'push': handle_push,
        'status': handle_status,
        'clone': handle_clone,
        'checkout': handle_checkout,
        'init': handle_init
    }
    
    # --------------------------------------------------------------
    # STEP 3: Execute the appropriate command.
    # --------------------------------------------------------------
    try:
        if command in brain_commands:
            # Execute brain-specific command by calling its handler function.
            return brain_commands[command](args)
        elif command in special_commands:
            # Execute Git command with special brain-specific handling.
            return special_commands[command](args)
        else:
            # Pass through to Git for all other commands.
            # This allows all standard Git commands to work within the brain tool.
            result = subprocess.run(['git', command] + args)
            return result.returncode
    except KeyboardInterrupt:
        # Handle user interruption (Ctrl+C).
        print("\nOperation cancelled by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        # Handle any other exceptions that occur during command execution.
        print(f"Error: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())