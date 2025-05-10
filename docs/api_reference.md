API Reference (Internal Modules)
--------------------------------

While "Brain" is primarily a command-line tool, its internal modules provide foundational functionalities. This section briefly touches upon key functions and classes within those modules, mainly for developers looking to understand or extend Brain. Note that some functions, especially in `brain.config`, might raise specific exceptions like `BrainConfigError` or `NeuronsConfigError` on issues like file not found or parsing problems, rather than returning `None` as might be implied by `Optional` in some older signature comments. The descriptions below reflect observed behavior.

### `brain.config`

Handles loading and saving of `.brain` (brain repository configuration) and `.neurons` (consumer repository configuration) files. These files are INI-style and parsed with case-sensitive keys.

*   `load_brain_config(file_path: str = '.brain') -> Dict[str, Any]`
    *   Loads and parses a `.brain` file.
    *   **Sections & Keys Processed:**
        *   `[BRAIN]`: `ID` (required, string), `DESCRIPTION` (optional, string).
        *   `[EXPORT]`: Required. Maps path patterns (strings) to permissions (`readonly` or `readwrite`). If permission is not specified (e.g., `path =`), it defaults to `readonly`.
        *   `[ACCESS]`: Optional. Maps entity identifiers (strings) to comma-separated lists of export path patterns. `*` is treated as a literal string.
        *   `[UPDATE_POLICY]`: Optional. Parses known boolean-like values (`true`, `false`, `yes`, `no`, `1`, `0`) to Python booleans. `PROTECTED_PATHS` is parsed as a list of strings. Other keys are stored as strings.
    *   Raises `BrainConfigError` if the file is not found, required sections/keys are missing, or parsing fails.

*   `save_brain_config(config: Dict[str, Any], file_path: str = '.brain') -> None`
    *   Saves a brain configuration dictionary to a `.brain` file.
    *   Writes boolean values as 'true' or 'false'. Lists are saved as comma-separated strings.

*   `load_neurons_config(file_path: str = '.neurons') -> Dict[str, Any]`
    *   Loads and parses a `.neurons` file. Reads with UTF-8 encoding.
    *   **Sections & Keys Processed:**
        *   `[BRAIN:<brain_id>]`: Defines connections. `<brain_id>` is extracted from the section name.
            *   `REMOTE`: Required, non-empty string (URL of the brain repository).
            *   `BRANCH`: Optional, string (branch to track). If absent in the file, it's not defaulted by `load_neurons_config` itself; consuming code (e.g., `add_neuron.py`) often defaults to 'main' if the key is missing from the loaded config dict.
            *   `ARGS`: Optional, string (additional Git arguments, parsed but not actively used by current core sync logic for `temp_clone_repo`).
        *   `[SYNC_POLICY]`: Optional. If present, updates default policy values. Keys are uppercased internally.
            *   Known boolean keys (`AUTO_SYNC_ON_PULL`, `ALLOW_LOCAL_MODIFICATIONS`, `ALLOW_PUSH_TO_BRAIN`, `AUTO_SYNC_ON_CHECKOUT`) are parsed to Python booleans.
            *   Other keys (e.g., `CONFLICT_STRATEGY`) are stored as strings.
            *   Default policies if section or key is missing: `AUTO_SYNC_ON_PULL=True`, `CONFLICT_STRATEGY='prompt'`, `ALLOW_LOCAL_MODIFICATIONS=False`, `ALLOW_PUSH_TO_BRAIN=False`, `AUTO_SYNC_ON_CHECKOUT=False`.
        *   `[MAP]`: Section is required. Defines neuron mappings.
            *   Format: `key_name = brain_id::source_path::destination_path`
            *   Alternate format (if only one brain is defined): `key_name = source_path::destination_path` (uses the single defined brain_id).
            *   Parses into a list of dictionaries, each containing `brain_id`, `source`, `destination`, and `_map_key` (the original key from the INI file). Validates that parts are non-empty and `brain_id` is known.
    *   Raises `NeuronsConfigError` if the file is not found, required sections/keys are missing (e.g., `[MAP]` section, `REMOTE` in brain definition), or parsing fails.

*   `save_neurons_config(config: Dict[str, Any], file_path: str = '.neurons') -> None`
    *   Saves a neurons configuration dictionary to a `.neurons` file with UTF-8 encoding.
    *   Boolean values in `SYNC_POLICY` are saved as 'true' or 'false'.
    *   `MAP` entries are written using `_map_key` if available, otherwise `map{i}` is generated as the key.

*   `get_current_repo_neurons_config() -> Optional[Dict[str, Any]]`
    *   Loads `.neurons` from the current working directory using `load_neurons_config()`.
    *   Re-raises `NeuronsConfigError` if `load_neurons_config` fails (e.g., file not found or parsing error).
    *   *Correction: Based on `load_neurons_config` raising `NeuronsConfigError` for file not found, this function will not return `None` if the file is absent but will raise instead.*

*   `get_current_repo_brain_config() -> Optional[Dict[str, Any]]`
    *   Loads `.brain` from the current working directory using `load_brain_config()`.
    *   Re-raises `BrainConfigError` if `load_brain_config` fails.
    *   *Correction: Similar to above, this will raise on file not found.*

*   `is_brain_repo() -> bool`
    *   Checks if a `.brain` file exists in the current working directory.

*   `is_neuron_repo() -> bool`
    *   Checks if a `.neurons` file exists in the current working directory.

*   Exceptions: `BrainConfigError`, `NeuronsConfigError`

### `brain.git`

Provides Git command execution and utility functions using `subprocess`.

*   `run_git_command(args: List[str], cwd: Optional[str] = None, timeout_seconds: Optional[int] = 60) -> str`
    *   Executes a Git command (e.g., `args=['status', '--porcelain']`).
    *   Returns `stdout` as a string (stripped of trailing whitespace).
    *   Raises `GitError` on non-zero exit code, timeout, or if `git` executable is not found.

*   `is_git_repo(path: str = '.') -> bool`
    *   Checks if the given path is within a Git working tree or is a bare repository. Uses `git rev-parse --is-inside-work-tree` and `git rev-parse --is-bare-repository`.

*   `is_bare_repo(repo_path: str) -> bool`
    *   Checks if the `repo_path` is a bare Git repository using `git rev-parse --is-bare-repository`.
    *   Returns `False` if `repo_path` is not a Git repository (based on "not a git repository" in error message). Raises `GitError` for other Git command issues.

*   `get_repo_root(path: str = '.') -> str`
    *   Returns the absolute path to the root of the Git repository containing `path`. Uses `git rev-parse --show-toplevel`.

*   `is_file_tracked(file_path: str, cwd: Optional[str] = None) -> bool`
    *   Checks if `file_path` is tracked by Git. Uses `git ls-files --error-unmatch <file_path>`. Returns `False` if command fails (e.g. file not tracked, or other git error).

*   `is_file_modified(file_path: str, cwd: Optional[str] = None) -> bool`
    *   Checks if `file_path` has modifications in the working tree or staging area. Uses `git status --porcelain <file_path>`. Any output from `git status --porcelain` for the file means some kind of status change. Returns `False` on `GitError`.

*   `get_file_hash(file_path: str, cwd: Optional[str] = None) -> str`
    *   Returns the Git blob hash of `file_path` as it exists in the `HEAD` commit. Uses `git rev-parse HEAD:<file_path>`. Raises `GitError` if file not in HEAD or other Git error.

*   `get_changed_files(cwd: Optional[str] = None) -> List[str]`
    *   Returns a list of file paths (relative to repository root) that are changed (modified, added, deleted, renamed, copied) in the working tree or staging area. Parses `git status --porcelain`. Returns empty list on `GitError`.

*   `clone_repo(url: str, target_dir: str, args: Optional[List[str]] = None) -> bool`
    *   Clones `url` into `target_dir` with optional `args`. Raises `GitError` on failure. Returns `True` on success (as failure raises exception).

*   `temp_clone_repo(url: str, branch: Optional[str] = None) -> str`
    *   Clones a repository into a temporary directory. Returns the path to this directory.
    *   Uses shallow clone (`--depth=1 --quiet`) for remote URLs (URLs not starting with `file://` and not identified as local absolute directory paths). Uses full, quiet clone for local URLs.
    *   Cleans up the temporary directory on failure. Provides enhanced error messages for GitHub authentication issues.

*   `is_github_url(url: str) -> bool`
    *   Heuristically checks if a URL is a GitHub URL (HTTPS or SSH, including SCP-like syntax).

*   `is_auth_error(error_message: str) -> bool`
    *   Heuristically checks if a Git error message indicates an authentication/authorization problem by looking for common keywords/patterns.

*   Exception: `GitError`

### `brain.sync`

Contains the logic for neuron synchronization, conflict resolution,and exporting.

*   `sync_neuron(neurons_config: Dict[str, Any], brain_id: str, source_path: str, dest_path: str, repo_path: str = '.') -> Dict[str, Any]`
    *   Synchronizes a single neuron.
    *   Temporarily clones the brain repository using `temp_clone_repo`.
    *   Copies files/directories from brain source to consumer destination.
    *   Handles conflicts based on `effective_conflict_strategy`. This strategy is `prefer_brain` if `ALLOW_LOCAL_MODIFICATIONS` is `false` and `CONFLICT_STRATEGY` is `prompt`; otherwise, it's the `CONFLICT_STRATEGY` from `SYNC_POLICY`.
    *   Merges neuron-specific requirements into the consumer's root `requirements.txt`. For directory neurons, it looks for `requirements.txt` or `<dirname>requirements.txt` inside the neuron's source directory in the brain. For file neurons (`neuron_file.py`), it looks for an adjacent `neuron_file.pyrequirements.txt` in the brain.
    *   Returns a result dictionary with `status` ('success'/'error'), `action` ('added'/'updated'/'unchanged'/'skipped'), `message`, etc.

*   `sync_all_neurons(neurons_config: Dict[str, Any], repo_path: str = '.') -> List[Dict[str, Any]]`
    *   Iterates through all mappings in `neurons_config['MAP']` and calls `sync_neuron` for each valid mapping.
    *   Returns a list of result dictionaries from `sync_neuron`.

*   `get_modified_neurons(neurons_config: Dict[str, Any], repo_path: str = '.') -> List[Dict[str, Any]]`
    *   Identifies consumer neurons whose local paths (as specified in `MAP`'s `destination`) correspond to files reported as changed by `brain.git.get_changed_files()`.
    *   A destination path is considered a directory if its mapping ends with `/` or `os.sep`, or if it exists on the filesystem as a directory.
    *   Returns a list of mapping dictionaries for these modified neurons.

*   `export_neurons_to_brain(neurons_config: Dict[str, Any], modified_neurons: List[Dict[str, Any]], repo_path: str = '.', commit_message_override: Optional[str] = None) -> Dict[str, Any]`
    *   Exports changes from consumer neurons back to their brain repositories.
    *   Requires `ALLOW_PUSH_TO_BRAIN=true` in the consumer's `SYNC_POLICY`.
    *   Groups neurons by `brain_id`.
    *   For local non-bare brains (`file://` URL, not bare, correct branch, clean working tree): copies changes directly, adds, and commits.
    *   For remote/bare brains: temporarily clones the brain, copies changes, adds, commits, and pushes.
    *   **Important:** This function does *not* re-verify if the neuron has `readwrite` permission in the *brain's `.brain` file* during the export; it relies on the `modified_neurons` list and the consumer's `ALLOW_PUSH_TO_BRAIN` policy.
    *   Returns a dictionary mapping brain IDs to export results (which include `status`, `message`, and `exported_neurons` list).

*   `detect_conflicts(local_content_orig: Union[str, bytes], brain_content_orig: Union[str, bytes]) -> bool`
    *   Compares byte content. If different, and both are decodable as UTF-8, compares string content. Returns `True` if different.

*   `handle_conflicts(file_path: str, local_content_bytes: bytes, brain_content_bytes: bytes, strategy: str = 'prompt') -> Dict[str, Any]`
    *   Resolves content conflicts based on strategy:
        *   `prefer_brain`: Returns brain content.
        *   `prefer_local`: Returns local content.
        *   `prompt`: If non-interactive (`not sys.stdin.isatty()`), defaults to `prefer_brain`. Interactively, shows diff (for text files) and prompts user to choose: `(b)rain`, `(l)ocal`, or `(m)erge`. Merge uses `git merge-file`.
    *   Returns a dictionary with `resolution` ('brain', 'local', 'merged', 'merged_with_conflicts') and `content` (bytes).

*   `parse_requirements(content: str) -> Dict[str, str]`
    *   Parses `requirements.txt`-style content. Returns a dictionary mapping package names to version strings. Only captures version string if `==` is used (e.g., `pkg==1.0` -> `{'pkg': '1.0'}`). For other specifiers (e.g., `pkg>=1.0`, `pkg`), the version string is stored as empty.

*   `merge_requirements(repo_requirements_content: str, neuron_requirements_content: str) -> str`
    *   Merges two sets of requirements parsed by `parse_requirements`.
    *   If `packaging.version.parse` is available and versions are PEP 440 compliant `==` specifications, it attempts to take the higher version.
    *   If versions are not parseable or one is non-specific (`""`), it generally prefers the neuron's specific version if available, or the repo's if the neuron's is non-specific. If both are non-specific, it remains non-specific. If both are specific but unparseable, it prefers the neuron's if they differ.
    *   Returns the merged content as a string, reconstructing `name==version` lines or just `name` lines.

*   Exception: `SyncError`

### `brain.utils`

General utility functions.

*   `ensure_directory_exists(path: str) -> None`
    *   Creates a directory if it doesn't exist, including parent directories (`os.makedirs(path, exist_ok=True)`).

*   `copy_file_or_directory(source: str, destination: str, overwrite: bool = True) -> bool`
    *   Copies a file or directory. Uses `shutil.copytree` for directories (removing destination directory first if it exists and `overwrite` is true) and `shutil.copy2` for files. Parent directory of `destination` is created if it doesn't exist.
    *   Returns `True` on success. Returns `False` if `source` doesn't exist, or if `destination` exists and `overwrite` is `False`.

*   `read_file_content(file_path: str, binary: bool = False) -> Union[str, bytes]`
    *   Reads file content as text (UTF-8 by default for text mode) or bytes.

*   `write_file_content(file_path: str, content: Union[str, bytes], binary: bool = False) -> None`
    *   Writes content to a file as text (UTF-8 by default for text mode) or bytes. Ensures parent directory exists.

*   `parse_mapping(mapping_str: str) -> Tuple[str, str, str]`
    *   Parses a neuron mapping string "brain_id::source::destination" into a 3-tuple. Raises `ValueError` if format is not three parts separated by `::`.

*   `find_mapping_for_neuron(neurons_config: Dict[str, Any], neuron_path: str) -> Optional[Dict[str, str]]`
    *   Finds the neuron mapping from `neurons_config['MAP']` whose `destination` matches `neuron_path` (after path normalization).
    *   For directory mappings (destination in config ends with `/`), it checks if the normalized `neuron_path` starts with the normalized directory path.

*   `format_size(size_bytes: int) -> str`
    *   Formats a byte size into a human-readable string (B, KB, MB, GB) with one decimal place for KB, MB, GB.

### `brain.commands.*`

Each module in `brain.commands` (e.g., `add_brain.py`, `sync.py`) contains a `handle_<command_name>(args: List[str]) -> int` function that implements the logic for that specific CLI command. These are orchestrated by `brain.cli.main`. The exit code is typically `0` for success and non-zero for errors. `argparse` within handlers may raise `SystemExit` on argument errors or for `--help`.