#!/usr/bin/env python3
"""
Brain Git Extension - Local Brain and Neurons Simulation Demo (Direct Handler Calls)

This script demonstrates the 'brain' Git extension by directly calling
the Python handler functions for 'brain' commands, creating a "virtual shell".
Git operations for setup are still done via subprocess.
"""

import os
import shutil
import subprocess
import pathlib
import sys
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Any, Callable, Dict, Optional

# --- Add project root to sys.path ---
PROJECT_ROOT = pathlib.Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# --- Import Brain Command Handlers and Core Components ---
try:
    from brain import __version__ as brain_version
    # Import all command handlers
    from brain.commands.brain_init import handle_brain_init
    from brain.commands.add_brain import handle_add_brain
    from brain.commands.add_neuron import handle_add_neuron
    from brain.commands.remove_neuron import handle_remove_neuron
    from brain.commands.sync import handle_sync
    from brain.commands.export import handle_export
    from brain.commands.list import handle_list
    from brain.commands.pull import handle_pull # Will still use subprocess for underlying git pull
    from brain.commands.push import handle_push # Will still use subprocess for underlying git push
    from brain.commands.status import handle_status # Will still use subprocess for underlying git status
    from brain.commands.clone import handle_clone # Will still use subprocess for underlying git clone
    from brain.commands.checkout import handle_checkout # Will still use subprocess for underlying git checkout
    from brain.commands.init import handle_init # Will still use subprocess for underlying git init

except ImportError as e:
    print(f"❌ ERROR: Could not import 'brain' modules from '{PROJECT_ROOT}'. Trace: {e}")
    sys.exit(1)

# --- Configuration ---
DEMO_DIR_NAME = "brain_demo_direct_calls"
BRAIN_REPO_NAME = "local_brain_repo_direct"
CONSUMER_ALPHA_NAME = "project_alpha_direct"
CONSUMER_BETA_NAME = "project_beta_direct"
INITIAL_BRANCH_NAME = "main"

# --- Command Handler Mapping for "Virtual Shell" ---
# Maps command string to the handler function
BRAIN_COMMAND_HANDLERS: Dict[str, Callable[[List[str]], int]] = {
    'brain-init': handle_brain_init,
    'add-brain': handle_add_brain,
    'add-neuron': handle_add_neuron,
    'remove-neuron': handle_remove_neuron,
    'sync': handle_sync,
    'export': handle_export,
    'list': handle_list,
    # Commands that primarily wrap git operations will still use subprocess
    # but their 'brain' specific logic (if any) is part of these handlers.
    'pull': handle_pull,
    'push': handle_push,
    'status': handle_status,
    'clone': handle_clone,
    'checkout': handle_checkout,
    'init': handle_init,
}

# --- Helper Functions ---
def print_header(message: str):
    """
    Description:
        Prints a formatted header message with equal signs above and below.
    
    Parameters:
        message (str): The message to display in the header.

    Returns:
        None
    """
    print(f"\n{'='*80}\n🚀 {message}\n{'='*80}")


def print_subheader(message: str):
    """
    Description:
        Prints a formatted subheader message with dashes above and below.
    
    Parameters:
        message (str): The message to display in the subheader.

    Returns:
        None
    """
    print(f"\n{'-'*60}\n🔧 {message}\n{'-'*60}")


def print_captured_output(stdout_val: str, stderr_val: str, context: str = "direct call"):
    """
    Description:
        Prints captured stdout and stderr values with appropriate headers.
    
    Parameters:
        stdout_val (str): The captured standard output.
        stderr_val (str): The captured standard error.
        context (str): A description of the context for the captured output. Default is "direct call".

    Returns:
        None
    """
    if stdout_val: print(f"\n--- STDOUT ({context}) ---\n{stdout_val.strip()}\n-------------------------")
    if stderr_val: print(f"\n--- STDERR ({context}) ---\n{stderr_val.strip()}\n-------------------------")


def execute_brain_command_directly(command_name: str, args_list: List[str], cwd: pathlib.Path) -> Any:
    """
    Description:
        Executes a brain command by directly calling its handler function.
        Captures stdout/stderr and return code.
    
    Parameters:
        command_name (str): The name of the brain command to execute.
        args_list (List[str]): List of arguments to pass to the command handler.
        cwd (pathlib.Path): The current working directory to execute the command in.

    Returns:
        result (Any): The return value from the command handler function or error code.
    """
    full_command_str_for_log = f"brain {command_name} {' '.join(args_list)}"
    print(f"\n👉 Executing (direct) in '{cwd.name}': $ {full_command_str_for_log}")

    original_cwd = os.getcwd()
    os.chdir(str(cwd))

    # --------------------------------------------------------------
    # STEP 1: Get the handler function for the specified command.
    # --------------------------------------------------------------
    handler_func = BRAIN_COMMAND_HANDLERS.get(command_name)
    if not handler_func:
        stderr_val = f"❌ Demo Script Error: No direct handler found for brain command '{command_name}'."
        print(stderr_val)
        os.chdir(original_cwd)
        return None # Or raise an error specific to the demo script

    # --------------------------------------------------------------
    # STEP 2: Execute the handler function and capture its output.
    # --------------------------------------------------------------
    stdout_capture = StringIO()
    stderr_capture = StringIO()
    result = None

    try:
        # Capture stdout/stderr from direct handler calls for better inspection
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            result = handler_func(args_list)
    except SystemExit as e:  # Argparse often raises SystemExit
        # ===============
        # Sub step 2.1: Handle SystemExit exceptions raised by argparse.
        # ===============
        # The handler's internal argparse might print to stderr_capture already
        if type(e.code) is int:
            result = e.code
        elif e.code is None: # SystemExit() or SystemExit(None) typically means success (0) or error (1) depending on context
            result = 0 # Assuming SystemExit() without code is often success or handled by argparse's output
        else: # Non-integer, non-None code (e.g. a string message printed by argparse)
            result = 1 # Default to error
    except Exception as e_handler:
        # ===============
        # Sub step 2.2: Handle any other exceptions.
        # ===============
        # Ensure full traceback for unexpected exceptions in handlers is captured and reported
        stderr_capture.write(f"❌ EXCEPTION in handler for '{command_name}': {type(e_handler).__name__}: {e_handler}\n")
        import traceback
        traceback.print_exc(file=stderr_capture)
        result = 1 # Indicate error
    finally:
        os.chdir(original_cwd)

    # --------------------------------------------------------------
    # STEP 3: Print the captured output.
    # --------------------------------------------------------------
    stdout_val = stdout_capture.getvalue()
    stderr_val = stderr_capture.getvalue()
    print_captured_output(stdout_val, stderr_val, f"brain {command_name}")

    return result


def run_git_command_subprocess(cmd_list: List[str], cwd: pathlib.Path, check_return_code: bool = True) -> Any:
    """
    Description:
        Runs git commands using subprocess, with proper output capturing and error handling.
    
    Parameters:
        cmd_list (List[str]): The git command and its arguments as a list.
        cwd (pathlib.Path): The current working directory to execute the command in.
        check_return_code (bool): Whether to check the return code and raise an exception on non-zero exit. Default is True.

    Returns:
        process (subprocess.CompletedProcess): The completed process object from subprocess.run.
    """
    cmd_str = " ".join(str(c) for c in cmd_list)
    print(f"\n👉 Running (git) in '{cwd.name}': $ {cmd_str}")
    if True: # Forcing subprocess as per original script logic for git
        # Fall back to subprocess if GitPython is not available
        print("Note: Using subprocess for git operations (GitPython not available)")
        try:
            # --------------------------------------------------------------
            # STEP 1: Execute the git command using subprocess.
            # --------------------------------------------------------------
            process = subprocess.run(
                cmd_list, # Should start with "git"
                cwd=str(cwd),
                check=check_return_code, # Let it raise CalledProcessError if check is True
                capture_output=True,
                text=True,
                env=os.environ.copy()
            )
            print_captured_output(process.stdout, process.stderr, "git subprocess")
            return process
        except FileNotFoundError:
            # --------------------------------------------------------------
            # STEP 2: Handle the case where the git command is not found.
            # --------------------------------------------------------------
            print(f"❌ ERROR: Command '{cmd_list[0]}' (expected 'git') not found.")
            raise
        except subprocess.CalledProcessError as e:
            # --------------------------------------------------------------
            # STEP 3: Handle the case where the git command fails.
            # --------------------------------------------------------------
            # Output already printed by this point if it failed and check_return_code was True,
            # but good to have a clear error message from the demo script itself.
            print(f"❌ GIT command '{cmd_str}' failed in '{cwd.name}' with exit code {e.returncode}.")
            # Output was already printed if this was reached due to check=True.
            # If check=False, the caller needs to handle it.
            raise


def create_file_with_content(file_path: pathlib.Path, content: str):
    """
    Description:
        Creates a file at the specified path with the given content.
        Creates parent directories if they don't exist.
    
    Parameters:
        file_path (pathlib.Path): The path where the file should be created.
        content (str): The content to write to the file.

    Returns:
        None
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    try: rel_path = str(file_path.relative_to(file_path.parent.parent))
    except ValueError: rel_path = str(file_path)
    print(f"📄 Created file: {rel_path}")


def append_to_file(file_path: pathlib.Path, content_to_append: str):
    """
    Description:
        Appends the given content to an existing file.
    
    Parameters:
        file_path (pathlib.Path): The path to the file to append to.
        content_to_append (str): The content to append to the file.

    Returns:
        None
    """
    with open(file_path, "a", encoding="utf-8") as f: f.write(content_to_append)
    try: rel_path = str(file_path.relative_to(file_path.parent.parent))
    except ValueError: rel_path = str(file_path)
    print(f"📝 Appended to file: {rel_path}")


# --- Demo Steps ---
def setup_demo_environment(base_dir: pathlib.Path) -> pathlib.Path:
    """
    Description:
        Sets up the demo environment by creating a clean demo directory.
    
    Parameters:
        base_dir (pathlib.Path): The base directory where the demo directory will be created.

    Returns:
        demo_dir (pathlib.Path): The path to the created demo directory.
    """
    print_header("Setting up Demo Environment")
    demo_dir = base_dir / DEMO_DIR_NAME
    if demo_dir.exists(): shutil.rmtree(demo_dir)
    demo_dir.mkdir(parents=True)
    print(f"✅ Demo directory created: {demo_dir}")
    return demo_dir


def create_local_brain_repository(demo_dir: pathlib.Path) -> pathlib.Path:
    """
    Description:
        Creates and initializes a local "brain" repository with sample files and configurations.
    
    Parameters:
        demo_dir (pathlib.Path): The demo directory where the brain repository will be created.

    Returns:
        brain_repo_path (pathlib.Path): The path to the created brain repository.
    """
    print_header("Creating Local Brain Repository")
    
    # --------------------------------------------------------------
    # STEP 1: Create the brain repository directory.
    # --------------------------------------------------------------
    brain_repo_path = demo_dir / BRAIN_REPO_NAME
    brain_repo_path.mkdir()
    print(f"🧠 Brain repo dir: {brain_repo_path}")

    # --------------------------------------------------------------
    # STEP 2: Initialize git repository.
    # --------------------------------------------------------------
    run_git_command_subprocess(["git", "init", "-b", INITIAL_BRANCH_NAME], cwd=brain_repo_path)

    # --------------------------------------------------------------
    # STEP 3: Create sample files.
    # --------------------------------------------------------------
    create_file_with_content(brain_repo_path / "core_logic/utils.py", "# Brain utils v1\ndef greet(): pass\n")
    create_file_with_content(brain_repo_path / "core_logic/constants.py", "# Brain constants v1\nVERSION='1.0b'\n")
    (brain_repo_path / "shared_assets/styles").mkdir(parents=True, exist_ok=True)
    create_file_with_content(brain_repo_path / "shared_assets/logo.txt", "BRAIN_LOGO_V1_DIRECT\n")
    create_file_with_content(brain_repo_path / "shared_assets/styles/main.css", "/* Brain CSS v1 */\n")

    # --------------------------------------------------------------
    # STEP 4: Initialize brain configuration.
    # --------------------------------------------------------------
    # Use direct call for "brain brain-init"
    execute_brain_command_directly("brain-init", ["--id", "my_local_brain", "--description", "Demo local brain (direct)"], cwd=brain_repo_path)

    # Overwrite .brain with specific export configuration for the demo
    # This ensures the demo tests specific export functionalities that might not be fully configurable via CLI args of brain-init
    brain_config_content = ("[BRAIN]\nID = my_local_brain\nDESCRIPTION = Demo local brain (direct)\n\n"
                            "[EXPORT]\ncore_logic/utils.py = readonly\ncore_logic/constants.py = readwrite\n"
                            "shared_assets/* = readonly\n")
    (brain_repo_path / ".brain").write_text(brain_config_content.strip(), encoding="utf-8")
    print(f"⚙️  Manually configured .brain file in {brain_repo_path.name}")

    # --------------------------------------------------------------
    # STEP 5: Commit the initial setup.
    # --------------------------------------------------------------
    run_git_command_subprocess(["git", "add", "."], cwd=brain_repo_path)
    run_git_command_subprocess(["git", "commit", "-m", f"Initial brain setup (direct calls) on {INITIAL_BRANCH_NAME}"], cwd=brain_repo_path)
    print("✅ Local brain repository initialized and configured.")
    return brain_repo_path


def create_consumer_repository(
    demo_dir: pathlib.Path, consumer_name: str, brain_repo_abs_path: pathlib.Path,
    neurons_to_add: List[tuple[str, str]], sync_policy_overrides: Optional[Dict[str, Any]] = None
) -> pathlib.Path:
    """
    Description:
        Creates and initializes a consumer repository that connects to the brain repository.
    
    Parameters:
        demo_dir (pathlib.Path): The demo directory where the consumer repository will be created.
        consumer_name (str): The name of the consumer repository.
        brain_repo_abs_path (pathlib.Path): The absolute path to the brain repository.
        neurons_to_add (List[tuple[str, str]]): List of neurons to add, each as a tuple of (mapping_string, description).
        sync_policy_overrides (Optional[Dict[str, Any]]): Optional dictionary of sync policy overrides to apply.

    Returns:
        consumer_repo_path (pathlib.Path): The path to the created consumer repository.
    """
    print_header(f"Creating Consumer Repository: {consumer_name}")
    
    # --------------------------------------------------------------
    # STEP 1: Create and initialize the consumer repository.
    # --------------------------------------------------------------
    consumer_repo_path = demo_dir / consumer_name
    consumer_repo_path.mkdir()
    print(f"🛍️ Consumer repo dir: {consumer_repo_path}")

    run_git_command_subprocess(["git", "init", "-b", INITIAL_BRANCH_NAME], cwd=consumer_repo_path)

    # --------------------------------------------------------------
    # STEP 2: Add the brain to the consumer repository.
    # --------------------------------------------------------------
    brain_url = f"file://{brain_repo_abs_path.as_posix()}"
    execute_brain_command_directly("add-brain", ["my_local_brain", brain_url, INITIAL_BRANCH_NAME], cwd=consumer_repo_path)

    # --------------------------------------------------------------
    # STEP 3: Add neurons from the brain to the consumer.
    # --------------------------------------------------------------
    for neuron_map_str, desc in neurons_to_add:
        print_subheader(f"Adding neuron: {desc} ({neuron_map_str})")
        execute_brain_command_directly("add-neuron", [neuron_map_str], cwd=consumer_repo_path)

    # --------------------------------------------------------------
    # STEP 4: Override sync policies if specified.
    # --------------------------------------------------------------
    if sync_policy_overrides:
        print_subheader(f"Overriding sync policy in .neurons for {consumer_name}")
        neurons_file_path = consumer_repo_path / ".neurons"
        if neurons_file_path.exists():
            from configparser import ConfigParser # Local import is fine for a demo script helper
            parser = ConfigParser(); parser.optionxform = str
            parser.read(str(neurons_file_path))
            if not parser.has_section('SYNC_POLICY'): parser.add_section('SYNC_POLICY')
            for key, value in sync_policy_overrides.items():
                parser.set('SYNC_POLICY', key.upper(), str(value).lower())
            with open(neurons_file_path, "w", encoding="utf-8") as f: parser.write(f)
            print(f"📝 Updated .neurons for {consumer_name} with: {sync_policy_overrides}")

    # --------------------------------------------------------------
    # STEP 5: Commit the initial setup.
    # --------------------------------------------------------------
    run_git_command_subprocess(["git", "add", "."], cwd=consumer_repo_path)
    run_git_command_subprocess(["git", "commit", "-m", f"Initial commit: Setup {consumer_name}"], cwd=consumer_repo_path)
    print(f"✅ Consumer repository {consumer_name} initialized.")
    return consumer_repo_path


def demonstrate_workflow(
    brain_repo_path: pathlib.Path, consumer_alpha_path: pathlib.Path, consumer_beta_path: pathlib.Path
):
    """
    Description:
        Demonstrates a complete workflow of the brain extension, including modifying neurons,
        syncing consumers, exporting changes, and removing neurons.
    
    Parameters:
        brain_repo_path (pathlib.Path): The path to the brain repository.
        consumer_alpha_path (pathlib.Path): The path to the alpha consumer repository.
        consumer_beta_path (pathlib.Path): The path to the beta consumer repository.

    Returns:
        None
    """
    print_header(f"Demonstrating Brain Workflow (Brain CLI v{brain_version}) (Direct Handler Calls)")

    # --------------------------------------------------------------
    # STEP 1: Get initial status of repositories.
    # --------------------------------------------------------------
    alpha_utils_path = consumer_alpha_path / "app_code" / "brain_utils.py"
    beta_css_path = consumer_beta_path / "assets_from_brain" / "styles" / "main.css"
    beta_constants_path = consumer_beta_path / "config" / "brain_constants.py"

    print_subheader(f"Initial Status in {CONSUMER_ALPHA_NAME}")
    execute_brain_command_directly("status", [], cwd=consumer_alpha_path)
    execute_brain_command_directly("list", [], cwd=consumer_alpha_path)
    if alpha_utils_path.exists(): print(f"📄 Initial Alpha utils:\n{alpha_utils_path.read_text(encoding='utf-8')[:100]}...")

    print_subheader(f"Initial Status in {CONSUMER_BETA_NAME}")
    execute_brain_command_directly("status", [], cwd=consumer_beta_path)
    execute_brain_command_directly("list", ["--verbose"], cwd=consumer_beta_path)
    if beta_constants_path.exists(): print(f"ℹ️ Initial Beta constants:\n{beta_constants_path.read_text(encoding='utf-8')}")

    # --------------------------------------------------------------
    # STEP 2: Modify neurons in the brain repository.
    # --------------------------------------------------------------
    print_header("Modifying Neurons in Brain Repository")
    append_to_file(brain_repo_path / "core_logic/utils.py", "\n# Brain utils v2\ndef farewell(): pass\n")
    run_git_command_subprocess(["git", "commit", "-am", "Update utils.py in brain (v2)"], cwd=brain_repo_path)
    append_to_file(brain_repo_path / "shared_assets/styles/main.css", "\n.new { color: blue; } /* v2 */\n")
    run_git_command_subprocess(["git", "commit", "-am", "Update main.css in brain (v2)"], cwd=brain_repo_path)

    # --------------------------------------------------------------
    # STEP 3: Sync changes from brain to consumer repositories.
    # --------------------------------------------------------------
    print_header(f"Syncing Neurons in {CONSUMER_ALPHA_NAME}")
    execute_brain_command_directly("sync", [], cwd=consumer_alpha_path) # Should use prefer_brain due to policy
    if alpha_utils_path.exists(): print(f"📄 Alpha utils after sync:\n{alpha_utils_path.read_text(encoding='utf-8')}")

    print_header(f"Syncing Neurons in {CONSUMER_BETA_NAME}")
    execute_brain_command_directly("sync", [], cwd=consumer_beta_path) # Might prompt if conflicts, but shouldn't be any here
    if beta_css_path.exists(): print(f"🎨 Beta CSS after sync:\n{beta_css_path.read_text(encoding='utf-8')}")

    # --------------------------------------------------------------
    # STEP 4: Modify a file in consumer and export changes back to brain.
    # --------------------------------------------------------------
    print_header(f"Modifying and Exporting from {CONSUMER_BETA_NAME}")
    append_to_file(beta_constants_path, "\n# Beta local change\nBETA_VER='1.1'\n")
    run_git_command_subprocess(["git", "add", str(beta_constants_path.relative_to(consumer_beta_path))], cwd=consumer_beta_path)
    run_git_command_subprocess(["git", "commit", "-m", "Local mod to constants in Beta"], cwd=consumer_beta_path)
    execute_brain_command_directly("export", [str(beta_constants_path.relative_to(consumer_beta_path)), '--force'], cwd=consumer_beta_path)

    # --------------------------------------------------------------
    # STEP 5: Verify exported changes in brain repository.
    # --------------------------------------------------------------
    print_header("Verifying Exported Change in Brain Repository")
    # No longer need arbitrary sleep if export to local non-bare repo is direct.
    # For a remote/bare repo, a `git pull` or re-clone would be needed here to see changes.
    # The current test uses a local non-bare repo, so direct modification should be visible.
    if (brain_repo_path / "core_logic/constants.py").exists():
        print(f"ℹ️ Brain constants after Beta export:\n{(brain_repo_path / 'core_logic/constants.py').read_text(encoding='utf-8')}")
    run_git_command_subprocess(["git", "log", "-n", "1", "--pretty=oneline"], cwd=brain_repo_path)

    # --------------------------------------------------------------
    # STEP 6: Remove a neuron from a consumer.
    # --------------------------------------------------------------
    print_header(f"Removing neuron from {CONSUMER_ALPHA_NAME}")
    alpha_utils_rel_path = str(alpha_utils_path.relative_to(consumer_alpha_path))
    execute_brain_command_directly("remove-neuron", [alpha_utils_rel_path, "--delete"], cwd=consumer_alpha_path)
    if not alpha_utils_path.exists(): print(f"✅ Neuron file {alpha_utils_rel_path} deleted from FS.")
    run_git_command_subprocess(["git", "add", ".neurons"], cwd=consumer_alpha_path)
    if not alpha_utils_path.exists(): # If --delete worked
         run_git_command_subprocess(["git", "rm", alpha_utils_rel_path], cwd=consumer_alpha_path, check_return_code=False) # `git rm` will fail if file not there, so `check_return_code=False`
    run_git_command_subprocess(["git", "commit", "-m", f"Removed {alpha_utils_rel_path} neuron"], cwd=consumer_alpha_path)

    print_header("🎉 Demo Complete! 🎉")


# --- Main Execution ---
def main():
    """
    Description:
        Main entry point for the script that runs the complete demonstration workflow.

    Parameters:
        None

    Returns:
        None
    """
    base_dir = pathlib.Path(__file__).parent.resolve()
    try:
        # --------------------------------------------------------------
        # STEP 1: Initialize and set up the demo environment.
        # --------------------------------------------------------------
        print(f"🧬 Running Brain Git Extension Demo Script (Brain CLI v{brain_version}) (Direct Handler Calls)")
        demo_dir = setup_demo_environment(base_dir)
        brain_repo = create_local_brain_repository(demo_dir).resolve()

        # --------------------------------------------------------------
        # STEP 2: Create consumer repositories.
        # --------------------------------------------------------------
        alpha_repo = create_consumer_repository(
            demo_dir, CONSUMER_ALPHA_NAME, brain_repo,
            neurons_to_add=[("my_local_brain::core_logic/utils.py::app_code/brain_utils.py", "Core utils")],
            sync_policy_overrides={"allow_local_modifications": False, "conflict_strategy": "prefer_brain"}
        ).resolve()

        beta_repo = create_consumer_repository(
            demo_dir, CONSUMER_BETA_NAME, brain_repo,
            neurons_to_add=[
                ("my_local_brain::shared_assets/::assets_from_brain/", "Shared assets dir"),
                ("my_local_brain::core_logic/constants.py::config/brain_constants.py", "Core constants")
            ],
            sync_policy_overrides={"allow_local_modifications": True, "allow_push_to_brain": True, "conflict_strategy": "prefer_brain"}
        ).resolve()

        # --------------------------------------------------------------
        # STEP 3: Demonstrate the complete workflow.
        # --------------------------------------------------------------
        demonstrate_workflow(brain_repo, alpha_repo, beta_repo)

    except subprocess.CalledProcessError as e:
        # --------------------------------------------------------------
        # STEP 4: Handle Git command failures.
        # --------------------------------------------------------------
        print(f"\n❌ A GIT command failed: {' '.join(e.cmd)}. Exit: {e.returncode}. Demo stopped. ❌")
        if e.stdout: print(f"Stdout:\n{e.stdout}")
        if e.stderr: print(f"Stderr:\n{e.stderr}")
    except FileNotFoundError: # Should only be for 'git' now
        # --------------------------------------------------------------
        # STEP 5: Handle missing Git executable.
        # --------------------------------------------------------------
        print("\n❌ 'git' command not found. Demo stopped. Ensure Git is installed and in PATH. ❌")
    except Exception as e:
        # --------------------------------------------------------------
        # STEP 6: Handle unexpected errors.
        # --------------------------------------------------------------
        import traceback
        print(f"\n❌ An unexpected error occurred: {type(e).__name__} - {e} ❌"); traceback.print_exc()
    finally:
        # --------------------------------------------------------------
        # STEP 7: Clean up the demo environment.
        # --------------------------------------------------------------
        print_header("Demo Teardown")
        cleanup = ""
        # Default to "no" for cleanup in non-interactive environments to preserve logs/state for CI or automated runs.
        if not sys.stdin.isatty(): print("Non-interactive, defaulting to NO cleanup."); cleanup = "no"
        else:
            try: cleanup = input(f"Remove demo directory '{DEMO_DIR_NAME}'? (yes/no) [yes]: ").lower()
            except EOFError: cleanup = "yes"; print("EOF, defaulting to cleanup.") # Keep 'yes' for EOF if interactive started
        
        if cleanup in ["", "y", "yes"]: # Only cleanup if explicitly 'yes' or empty prompt (which defaults to yes)
            shutil.rmtree(base_dir / DEMO_DIR_NAME, ignore_errors=True)
            print(f"🗑️ Demo directory '{base_dir / DEMO_DIR_NAME}' removed (or attempt made).")
        else: print(f"ℹ️ Demo directory '{base_dir / DEMO_DIR_NAME}' was not removed.")


if __name__ == "__main__":
    main()