"""
Git operations for Brain.

This module provides a comprehensive set of functions for interacting with Git repositories,
including repository identification, file tracking, repository cloning, and other common Git operations.
All functions are designed to be robust, with appropriate error handling and debugging capabilities.
"""

import os
import shutil
import subprocess
import tempfile
import re
from urllib.parse import urlparse
import sys 
from typing import List, Optional


# --- DEBUGGING ---
ENABLE_GIT_DEBUG_LOGGING = True 

def _debug_log_git(message: str):
    """
    Description:
        Logs debug messages related to Git operations when debugging is enabled.
    
    Parameters:
        message (str): The debug message to log.

    Returns:
        None
    """
    if ENABLE_GIT_DEBUG_LOGGING:
        print(f"[GIT_DEBUG] {message}", file=sys.stderr, flush=True)
# --- END DEBUGGING ---

class GitError(Exception):
    """
    Description:
        Custom exception class for Git-related errors.
        Used to encapsulate and propagate Git command failures with descriptive messages.
    """
    pass


def run_git_command(args: List[str], cwd: Optional[str] = None, timeout_seconds: Optional[int] = 60) -> str:
    """
    Description:
        Executes a Git command with the provided arguments and returns the command output.
        Uses subprocess directly instead of GitPython.
    
    Parameters:
        args (List[str]): Command arguments (without the 'git' prefix)
        cwd (Optional[str]): Working directory where the command will execute (default: current directory)
        timeout_seconds (Optional[int]): Timeout for the Git command execution in seconds (default: 60)
    
    Returns:
        stdout_content (str): Command output (stdout) as a string with trailing whitespace removed
    
    Raises:
        GitError: If the command fails or times out
    """
    # --------------------------------------------------------------
    # STEP 1: Prepare for subprocess execution.
    # --------------------------------------------------------------
    # Forcing subprocess as GitPython is not used per original setup.
    _debug_log_git(f"GitPython not available, falling back to subprocess")
    effective_cwd = cwd or os.getcwd()
    _debug_log_git(f"Running command with subprocess: git {' '.join(args)} in CWD: {effective_cwd}")
    
    # --------------------------------------------------------------
    # STEP 2: Execute the Git command and handle potential errors.
    # --------------------------------------------------------------
    try:
        # Execute Git command with appropriate parameters.
        result = subprocess.run(
            ['git'] + args,
            cwd=effective_cwd,
            check=False, # Manual check of returncode to include stderr in GitError
            capture_output=True,
            text=True, # Ensure text mode for stdout/stderr
            encoding='utf-8', # Be explicit about encoding
            env=os.environ.copy(), # Pass environment
            timeout=timeout_seconds 
        )
        _debug_log_git(f"Command finished. Return code: {result.returncode}")
        if result.stdout:
            _debug_log_git(f"Stdout:\n{result.stdout.strip()}")
        if result.stderr:
            _debug_log_git(f"Stderr:\n{result.stderr.strip()}")

        # Check for command failure.
        if result.returncode != 0:
            error_message = result.stderr.strip() if result.stderr else f"Git command failed with no stderr. Args: {args}"
            raise GitError(f"Git command failed with code {result.returncode}: {error_message}")
        
        return result.stdout.strip()

    # --------------------------------------------------------------
    # STEP 3: Handle specific exceptions that might occur.
    # --------------------------------------------------------------
    except subprocess.TimeoutExpired:
        _debug_log_git(f"Command timed out after {timeout_seconds} seconds: git {' '.join(args)}")
        raise GitError(f"Git command timed out: git {' '.join(args)}")
    # CalledProcessError should not happen due to check=False, but as a safeguard:
    except subprocess.CalledProcessError as e: 
        _debug_log_git(f"CalledProcessError: {e.stderr.strip() if e.stderr else str(e)}")
        raise GitError(f"Git command failed (CalledProcessError): {e.stderr.strip() if e.stderr else str(e)}")
    except FileNotFoundError:
        _debug_log_git(f"Git command not found. Ensure 'git' is in PATH.")
        raise GitError("Git command not found. Please ensure Git is installed and in your PATH.")
    except Exception as e_gen: 
        _debug_log_git(f"Unexpected error running git command 'git {' '.join(args)}': {type(e_gen).__name__}: {e_gen}")
        raise GitError(f"Unexpected error running git command 'git {' '.join(args)}': {e_gen}")


def is_git_repo(path: str = '.') -> bool:
    """
    Description:
        Determines if a directory is part of a Git repository or is a Git repository itself.
        Checks both regular repositories and bare repositories.
    
    Parameters:
        path (str): Directory path to check (default: current directory '.')
    
    Returns:
        is_repo (bool): True if the directory is a Git repository or within a repository, False otherwise
    """
    _debug_log_git(f"is_git_repo: Checking path '{path}'")
    # A more robust check for a git repo is to see if `git rev-parse --git-dir` succeeds
    # and points to a valid .git directory (or the directory itself if bare).
    # For simplicity matching current usage:
    try:
        # Using --is-inside-work-tree is robust for checking if 'path' is part of a work tree.
        # For checking if 'path' IS a repo root, rev-parse specific to that path is better.
        run_git_command(['rev-parse', '--is-inside-work-tree'], cwd=path, timeout_seconds=5)
        _debug_log_git(f"is_git_repo: Path '{path}' IS part of a Git working tree.")
        return True
    except GitError: # If not inside a work tree or not a repo at all.
        # Could be a bare repo. Check for that.
        try:
            is_bare_output = run_git_command(['rev-parse', '--is-bare-repository'], cwd=path, timeout_seconds=5)
            if is_bare_output == 'true':
                _debug_log_git(f"is_git_repo: Path '{path}' IS a bare Git repository.")
                return True
        except GitError:
            pass # Not bare either
        _debug_log_git(f"is_git_repo: Path '{path}' is NOT a Git repository (or command failed).")
        return False


def is_bare_repo(repo_path: str) -> bool:
    """
    Description:
        Determines if the given path is a bare Git repository.
        A bare repository contains only the Git data with no working files.
    
    Parameters:
        repo_path (str): The path to the Git repository to check
    
    Returns:
        is_bare (bool): True if it's a bare repository, False otherwise
    
    Raises:
        GitError: If the git rev-parse command fails for reasons other than not being a repo
                  (e.g., git executable not found, insufficient permissions)
    """
    _debug_log_git(f"is_bare_repo: Checking if '{repo_path}' is bare.")
    try:
        output = run_git_command(['rev-parse', '--is-bare-repository'], cwd=repo_path, timeout_seconds=5)
        is_bare = output.strip().lower() == 'true'
        _debug_log_git(f"is_bare_repo: Output for '{repo_path}': '{output}', is_bare: {is_bare}")
        return is_bare
    except GitError as e:
        # If the error indicates it's not a git repository at all, then it's not bare.
        # This depends on the specific error message from run_git_command for "not a git repo".
        # For now, assume any GitError means it cannot be determined as bare or isn't one.
        _debug_log_git(f"is_bare_repo: GitError for '{repo_path}', assuming not bare or not a repo. Error: {e}")
        # A more specific check would be needed if we want to distinguish "not a repo" from other git errors.
        # If run_git_command raises GitError for "not a git repo", then False is correct.
        if "not a git repository" in str(e).lower(): # Heuristic check
            return False
        raise # Re-raise other GitErrors (permissions, git not found etc.)


def get_repo_root(path: str = '.') -> str:
    """
    Description:
        Retrieves the absolute path to the root directory of a Git repository.
        The root is the top-level directory of the working tree.
    
    Parameters:
        path (str): Path within the repository to start from (default: current directory '.')
    
    Returns:
        root_path (str): Absolute path to the repository root directory
    
    Raises:
        GitError: If the path is not in a Git repository's working tree
    """
    _debug_log_git(f"get_repo_root: For path '{path}'")
    try:
        root = run_git_command(['rev-parse', '--show-toplevel'], cwd=path, timeout_seconds=10)
        _debug_log_git(f"get_repo_root: Root for '{path}' is '{root}'")
        return os.path.abspath(root) # Ensure absolute path
    except GitError as e:
        _debug_log_git(f"get_repo_root: Failed for '{path}'. Error: {e}")
        raise


def get_repo_name(path: str = '.') -> str:
    """
    Description:
        Retrieves the name of a Git repository from its remote origin URL or directory name.
        First attempts to get the name from the 'origin' remote URL, then falls back to using
        the directory name of the repository root if remote URL extraction fails.
    
    Parameters:
        path (str): Path within the repository (default: current directory '.')
    
    Returns:
        repo_name (str): Repository name derived from URL or directory name
    
    Raises:
        GitError: If the path is not in a Git repository
    """
    _debug_log_git(f"get_repo_name: For path '{path}'")
    
    # --------------------------------------------------------------
    # STEP 1: First try to get the name from remote origin URL.
    # --------------------------------------------------------------
    try:
        # Ensure we are in a git repo first by getting its root
        repo_root_path = get_repo_root(path) # This will raise GitError if not a repo

        # Get the URL of the 'origin' remote.
        remote_url = run_git_command(['remote', 'get-url', 'origin'], cwd=repo_root_path, timeout_seconds=10)
        _debug_log_git(f"get_repo_name: Remote URL for origin: '{remote_url}'")
        
        # Parse the URL to extract repository name.
        parsed_url = urlparse(remote_url)
        url_path = parsed_url.path
        
        # Handle SCP-like syntax for SSH URLs (git@github.com:user/repo.git).
        if not parsed_url.scheme and ':' in url_path and '@' in url_path.split(':')[0]:
            url_path = url_path.split(':', 1)[-1]

        # Extract basename and remove '.git' extension if present.
        base_name = os.path.basename(url_path)
        if base_name.endswith('.git'):
            repo_name = base_name[:-4]
        else:
            repo_name = base_name
        
        # Verify we have a valid repository name.
        if repo_name: # Check if repo_name derived is non-empty
            _debug_log_git(f"get_repo_name: Deduced name '{repo_name}' from URL.")
            return repo_name
        else: # Fallback if parsing URL somehow yielded empty name
             _debug_log_git(f"get_repo_name: Deduced empty name from URL, falling back to directory name.")
             name = os.path.basename(repo_root_path)
             _debug_log_git(f"get_repo_name: Deduced name '{name}' from directory root.")
             return name

    # --------------------------------------------------------------
    # STEP 2: Fallback to using directory name if remote origin approach fails.
    # --------------------------------------------------------------
    except GitError: # Catches error from get_repo_root or remote get-url
        _debug_log_git(f"get_repo_name: Error getting remote 'origin' or not a repo. Falling back to directory name.")
        # If get_repo_root failed, path isn't a repo. If remote failed, use root dir name.
        # This needs get_repo_root to succeed if we are to use its output.
        try:
            root_dir = get_repo_root(path) # Try again, if original error was remote-related
            name = os.path.basename(root_dir)
            _debug_log_git(f"get_repo_name: Deduced name '{name}' from directory root (fallback).")
            return name
        except GitError as e_final_fallback: # If path is truly not a repo
            _debug_log_git(f"get_repo_name: Path '{path}' is not a git repository. Cannot determine name. Error: {e_final_fallback}")
            raise # Re-raise the error that path is not a git repo


def is_file_tracked(file_path: str, cwd: Optional[str] = None) -> bool:
    """
    Description:
        Determines if a file is currently tracked by Git (part of the repository).
        A tracked file is one that was previously added to the Git repository.
    
    Parameters:
        file_path (str): Path to the file, relative to cwd if provided
        cwd (Optional[str]): Working directory (default: current directory)
    
    Returns:
        is_tracked (bool): True if the file is tracked by Git, False otherwise
    """
    effective_cwd = cwd or os.getcwd()
    _debug_log_git(f"is_file_tracked: Checking file '{file_path}' in CWD: {effective_cwd}")
    try:
        # `git ls-files --error-unmatch <file_path>` returns 0 if tracked, 1 if not.
        run_git_command(['ls-files', '--error-unmatch', file_path], cwd=effective_cwd, timeout_seconds=10)
        _debug_log_git(f"is_file_tracked: File '{file_path}' IS tracked.")
        return True
    except GitError as e:
        # Check if error message indicates "did not match any files"
        if "did not match any file(s)" in str(e) or "fatal: pathspec" in str(e).lower() and "did not match any files" in str(e).lower() : # Example patterns
            _debug_log_git(f"is_file_tracked: File '{file_path}' is NOT tracked (ls-files error).")
        else: # Other GitError (e.g. not a repo, git not found)
            _debug_log_git(f"is_file_tracked: GitError checking if '{file_path}' is tracked: {e}. Assuming not tracked for safety.")
        return False


def is_file_modified(file_path: str, cwd: Optional[str] = None) -> bool:
    """
    Description:
        Checks if a tracked file has been modified in the working tree or index.
        This includes added, modified, deleted, or renamed files.
    
    Parameters:
        file_path (str): Path to the file, relative to cwd if provided
        cwd (Optional[str]): Working directory (default: current directory)
    
    Returns:
        is_modified (bool): True if the file has been modified, False otherwise
    """
    effective_cwd = cwd or os.getcwd()
    _debug_log_git(f"is_file_modified: Checking file '{file_path}' in CWD: {effective_cwd}")
    
    # A file can't be "modified" in git terms if it's not tracked or doesn't exist.
    # However, this function is usually called for files presumed to be part of the repo.
    # If is_file_tracked is strict, use it. For now, rely on `git status --porcelain`.
    # if not is_file_tracked(file_path, effective_cwd): # This already logs
    #     _debug_log_git(f"is_file_modified: File '{file_path}' not tracked, so not modified by Git's definition.")
    #     return False
    
    try:
        # `git status --porcelain <file_path>` will output if changed, staged, or untracked (if new).
        # We are interested in changes to *tracked* files.
        status = run_git_command(['status', '--porcelain', file_path], cwd=effective_cwd, timeout_seconds=10)
        is_mod = bool(status.strip()) # Any output means some kind of status change.
                                      # For a tracked file, this implies modification or staging.
        _debug_log_git(f"is_file_modified: File '{file_path}' porcelain status: '{status.strip()}'. Modified: {is_mod}")
        return is_mod
    except GitError:
        _debug_log_git(f"is_file_modified: Error getting status for '{file_path}'. Assuming not modified for safety.")
        return False


def get_file_hash(file_path: str, cwd: Optional[str] = None) -> str:
    """
    Description:
        Retrieves the Git hash (blob SHA-1) of a file as it exists in the HEAD commit.
        This is NOT the hash of the current file system content if the file has been modified.
    
    Parameters:
        file_path (str): Path to the file, relative to cwd if provided
        cwd (Optional[str]): Working directory (default: current directory)
    
    Returns:
        blob_hash (str): Git object hash (SHA-1) of the file from HEAD
    
    Raises:
        GitError: If the file is not tracked in HEAD or another Git error occurs
    """
    effective_cwd = cwd or os.getcwd()
    _debug_log_git(f"get_file_hash (from HEAD): For file '{file_path}' in CWD: {effective_cwd}")
    
    try:
        # `git ls-files -s <file_path>` shows <mode> <hash> <stage>\t<file>
        # `git rev-parse HEAD:<file_path>` gives blob hash of file in HEAD
        obj_hash = run_git_command(['rev-parse', f'HEAD:{file_path}'], cwd=effective_cwd, timeout_seconds=10)
        _debug_log_git(f"get_file_hash: Hash for '{file_path}' in HEAD is '{obj_hash}'")
        return obj_hash
    except GitError as e:
        _debug_log_git(f"get_file_hash: Error getting hash for '{file_path}' from HEAD: {e}")
        # This can happen if file is new (not in HEAD), or path is wrong.
        raise GitError(f"Could not get Git hash for '{file_path}' from HEAD. It might not be committed or path is incorrect. Error: {e}")


def get_changed_files(cwd: Optional[str] = None) -> List[str]:
    """
    Description:
        Retrieves a list of all files that have been changed (modified, added, deleted, renamed, copied)
        in the repository's working tree and staging area compared to HEAD.
    
    Parameters:
        cwd (Optional[str]): Working directory (default: current directory)
    
    Returns:
        changed_files (List[str]): List of changed file paths relative to the repository root
    """
    effective_cwd = cwd or os.getcwd()
    _debug_log_git(f"get_changed_files: In CWD: {effective_cwd}")
    
    # --------------------------------------------------------------
    # STEP 1: Get porcelain status of all files.
    # --------------------------------------------------------------
    try:
        status = run_git_command(['status', '--porcelain'], cwd=effective_cwd, timeout_seconds=10)
        _debug_log_git(f"get_changed_files: Porcelain status output:\n{status}")
        
        # --------------------------------------------------------------
        # STEP 2: Parse status output to extract changed file paths.
        # --------------------------------------------------------------
        changed_files = []
        for line in status.splitlines():
            if not line.strip():
                continue
            
            # Porcelain format: XY PATH or XY ORIG_PATH -> PATH for renames/copies
            parts = line.strip().split(maxsplit=1) # Split only on the first whitespace
            # status_codes = parts[0] # e.g., " M", "A ", " D", "R ", "C "
            file_info = parts[1]

            # ===============
            # Sub step 2.1: Handle renames and copies specially.
            # ===============
            # For renames (R) and copies (C), path is after "->". Example: "R  old_name -> new_name"
            if parts[0].startswith('R') or parts[0].startswith('C'): 
                file_path = file_info.split('->')[-1].strip()
            else:
                file_path = file_info.strip()

            # ===============
            # Sub step 2.2: Handle quoted paths.
            # ===============
            # Handle paths quoted by Git (e.g., if they contain spaces or special chars)
            if file_path.startswith('"') and file_path.endswith('"'):
                # Attempt to unquote. Git's quoting can be complex (e.g., octal escapes).
                # A simple [1:-1] might be insufficient for all cases but common.
                # For robust unquoting, one might need a more sophisticated parser.
                # Python's `shlex.split` might be too heavy. For now, simple unquote.
                # Or, use `git status --porcelain=v2 --unquote` if available and parse that.
                # Current simple approach:
                try:
                    # This is a basic attempt, may not cover all Git's quoting/escaping.
                    unquoted_path = file_path[1:-1].encode('latin-1', 'backslashreplace').decode('unicode_escape')
                    file_path = unquoted_path
                except UnicodeDecodeError:
                    _debug_log_git(f"get_changed_files: Failed to robustly unquote path '{file_path[1:-1]}', using simple slice.")
                    file_path = file_path[1:-1] # Fallback to simple slicing if complex unquoting fails

            changed_files.append(file_path)
        _debug_log_git(f"get_changed_files: Parsed changed files: {changed_files}")
        return changed_files
    except GitError as e:
        _debug_log_git(f"get_changed_files: Error getting status: {e}. Returning empty list.")
        return []


def clone_repo(url: str, target_dir: str, args: Optional[List[str]] = None) -> bool:
    """
    Description:
        Clones a Git repository from the specified URL to the target directory.
        Supports additional Git arguments for customizing the clone operation.
    
    Parameters:
        url (str): Repository URL or local path to clone from
        target_dir (str): Target directory where the repository will be cloned
        args (Optional[List[str]]): Additional Git arguments for clone (e.g., ['--branch', 'main'])
    
    Returns:
        success (bool): True if cloning was successful (always true because exception is raised on failure)
    
    Raises:
        GitError: If cloning fails for any reason
    """
    final_args = args if args is not None else []
    _debug_log_git(f"clone_repo: Attempting to clone '{url}' into '{target_dir}' with args: {final_args}")
    
    # Forcing subprocess as per original project structure
    _debug_log_git(f"clone_repo: Using subprocess for 'git clone'")
    try:
        # The run_git_command will handle cwd if it's part of its own logic,
        # but clone typically doesn't need a specific CWD other than where the command is run from.
        # The target_dir is an argument to clone itself.
        run_git_command(['clone'] + final_args + [url, target_dir], timeout_seconds=180) # Increased timeout for clone
        _debug_log_git(f"clone_repo: Successfully cloned '{url}' into '{target_dir}'")
        return True
    except GitError as e: # run_git_command raises GitError on failure
        _debug_log_git(f"clone_repo: Failed to clone repository from '{url}' into '{target_dir}'. Error: {str(e)}")
        # Re-raise the specific GitError from run_git_command
        raise GitError(f"Failed to clone repository from '{url}' into '{target_dir}': {str(e)}") from e


def is_github_url(url: str) -> bool:
    """
    Description:
        Determines if a URL is likely a GitHub repository URL.
        Checks for both HTTPS and SSH URL formats for GitHub.
    
    Parameters:
        url (str): The URL to check
    
    Returns:
        is_github (bool): True if the URL is likely a GitHub URL, False otherwise
    """
    _debug_log_git(f"is_github_url: Checking URL: {url}")
    try:
        # --------------------------------------------------------------
        # STEP 1: Handle standard URL formats (HTTPS, SSH with hostname).
        # --------------------------------------------------------------
        parsed_url = urlparse(url)
        if parsed_url.hostname: # HTTPS or SSH with identifiable hostname
            is_gh = parsed_url.hostname.lower() == 'github.com' or parsed_url.hostname.lower().endswith('.github.com')
            _debug_log_git(f"is_github_url: Parsed hostname '{parsed_url.hostname}', is GitHub: {is_gh}")
            return is_gh
        
        # --------------------------------------------------------------
        # STEP 2: Handle SCP-like SSH syntax (git@github.com:user/repo.git).
        # --------------------------------------------------------------
        if not parsed_url.scheme and '@' in parsed_url.path and ':' in parsed_url.path:
            # Path for SCP-like is "git@github.com:user/repo.git"
            host_part = parsed_url.path.split('@')[-1].split(':')[0]
            is_gh_scp = host_part.lower() == 'github.com'
            _debug_log_git(f"is_github_url: SCP-like syntax, potential host '{host_part}', is GitHub: {is_gh_scp}")
            return is_gh_scp
    except ValueError: # Raised by urlparse on very malformed URLs
        _debug_log_git(f"is_github_url: ValueError parsing URL '{url}'")
        pass 
    _debug_log_git(f"is_github_url: URL '{url}' is not recognized as GitHub.")
    return False

def is_auth_error(error_message: str) -> bool:
    """
    Description:
        Determines if a Git error message likely indicates an authentication or authorization issue.
        Used to provide better error messages for GitHub authentication failures.
    
    Parameters:
        error_message (str): The Git error message to analyze
    
    Returns:
        is_auth_error (bool): True if the error appears to be an authentication issue, False otherwise
    """
    error_message_lower = error_message.lower()
    # Patterns are regex, ensure they are treated as such if complex.
    # Simple string checking for keywords is often sufficient.
    auth_keywords = [
        "authentication failed", "permission denied", "access denied",
        "could not read from remote repository", 
        "please make sure you have the correct access rights",
        "repository not found", # Can be auth, or genuinely not found
        "fatal: could not read username", 
        "remote end hung up unexpectedly", # Can be network, but often auth for private repos
        "fatal: unable to access", # Often followed by details like "The requested URL returned error: 403"
        r"fatal: '.*' does not appear to be a git repository" # Can be wrong URL or private repo without access
    ]
    for keyword_pattern in auth_keywords:
        if re.search(keyword_pattern, error_message_lower):
            _debug_log_git(f"is_auth_error: Auth error keyword/pattern '{keyword_pattern}' found in: {error_message_lower[:200]}...")
            return True
    _debug_log_git(f"is_auth_error: No auth error keywords found in: {error_message_lower[:200]}...")
    return False


def temp_clone_repo(url: str, branch: Optional[str] = None) -> str:
    """
    Description:
        Clones a repository to a temporary directory and handles potential errors.
        Optimizes cloning based on whether the source is local or remote.
    
    Parameters:
        url (str): Repository URL or local path (absolute path recommended for local, or file:// prefix)
        branch (Optional[str]): Branch to clone (default: None for the default branch of the remote)
    
    Returns:
        temp_dir_path (str): Path to the temporary directory containing the cloned repository
    
    Raises:
        GitError: If cloning fails, with enhanced error messages for GitHub authentication issues
    """
    # --------------------------------------------------------------
    # STEP 1: Create temporary directory for the clone.
    # --------------------------------------------------------------
    temp_dir = tempfile.mkdtemp(prefix='brain-clone-')
    _debug_log_git(f"temp_clone_repo: Created temp dir for clone: {temp_dir}")
    
    # --------------------------------------------------------------
    # STEP 2: Determine if URL is local and set clone strategy.
    # --------------------------------------------------------------
    # Determine if URL is local path for optimized cloning
    # file:// indicates a local filesystem path.
    # os.path.isabs() helps for direct paths, but ensure it's a dir for repo check.
    is_local_url_scheme = url.startswith('file://')
    # A simple heuristic for local paths not using file://
    # This could be refined, e.g. by checking if os.path.isdir(url) and then is_git_repo(url)
    # For now, rely on file:// for explicit local, otherwise assume remote for shallow clone.
    is_likely_local_path_direct = os.path.isabs(url) and os.path.isdir(url) # Basic check
    
    # Prefer shallow clone for remotes to save time/bandwidth
    # For local clones, shallow clone might not be beneficial or even problematic.
    use_shallow_clone = not (is_local_url_scheme or is_likely_local_path_direct)
    
    if use_shallow_clone:
        _debug_log_git(f"temp_clone_repo: '{url}' treated as remote. Will use shallow clone.")
    else:
        _debug_log_git(f"temp_clone_repo: '{url}' treated as local. Will NOT use shallow clone.")
    
    # --------------------------------------------------------------
    # STEP 3: Set up clone arguments and perform clone.
    # --------------------------------------------------------------
    # Using subprocess directly as per project structure
    _debug_log_git(f"temp_clone_repo: Using subprocess for clone operation.")
    
    clone_args: List[str] = []
    if use_shallow_clone:
        clone_args.extend(['--depth=1'])
    
    # --quiet is useful for both local and remote to reduce log noise from git itself
    clone_args.append('--quiet')
    
    if branch:
        clone_args.extend(['--branch', branch])
        
    _debug_log_git(f"temp_clone_repo: Final clone args: {clone_args} for URL: '{url}', Branch: '{branch}'")
    try:
        clone_repo(url, temp_dir, clone_args) # This function logs and raises GitError on failure
        _debug_log_git(f"temp_clone_repo: Temp clone successful into {temp_dir} for URL '{url}'.")
        return temp_dir
    except GitError as e: # Raised by clone_repo
        _debug_log_git(f"temp_clone_repo: FAILED for URL '{url}' during clone_repo call. Error: {e}")
        
        # --------------------------------------------------------------
        # STEP 4: Clean up on failure and provide enhanced error messages.
        # --------------------------------------------------------------
        # Ensure cleanup of temp_dir on any failure from clone_repo
        try:
            if os.path.exists(temp_dir): # Should exist unless mkdtemp failed (unlikely here)
                _debug_log_git(f"temp_clone_repo: Cleaning up failed clone temp dir: {temp_dir}")
                shutil.rmtree(temp_dir)
        except Exception as cleanup_exc:
            # Log cleanup error but prioritize re-raising the original clone error
            _debug_log_git(f"temp_clone_repo: Warning! Failed to cleanup temp dir {temp_dir} after clone error: {cleanup_exc}")

        # Enhance error for common GitHub authentication issues
        original_git_error_message = ""
        if e.__cause__ and type(e.__cause__) is GitError and e.__cause__.args:
            original_git_error_message = str(e.__cause__.args[0])
        elif e.args:
            original_git_error_message = str(e.args[0])
            
        if is_github_url(url) and is_auth_error(original_git_error_message):
            enhanced_message = (
                f"Failed to clone from GitHub URL: {url}. "
                "This might be a private repository. Please ensure your Git credentials "
                "(e.g., Personal Access Token for HTTPS, or SSH key for SSH protocol) are correctly configured and grant access. "
                f"Original Git Details: {original_git_error_message}" # This can be very long
            )
            _debug_log_git(f"temp_clone_repo: Raising enhanced GitHub auth error (first 500 chars): {enhanced_message[:500]}")
            raise GitError(enhanced_message) from e # Chain the original exception
        
        raise # Re-raise the original GitError from clone_repo if not a handled GitHub auth case