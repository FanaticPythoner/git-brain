Developer Guide
---------------

This section provides insights into the internal workings of Brain, primarily derived from `sync.py`, `git.py`, and `config.py`.

### Synchronization Logic (`brain.sync`)

The core of Brain's functionality lies in its synchronization mechanism.

1.  **`sync_all_neurons`**:
    *   Iterates through all valid mappings in the `[MAP]` section of the `neurons_config`.
    *   For each mapping, calls `sync_neuron`. Returns a list of results.

2.  **`sync_neuron`**:
    *   **Configuration**: Retrieves brain details (URL, branch from `BRAINS` section) and sync policies (`SYNC_POLICY`) from the passed `neurons_config`. Determines the `effective_conflict_strategy`.
    *   **Cloning Brain**: Performs a temporary clone of the brain repository using `brain.git.temp_clone_repo`. This is a shallow clone (`--depth=1 --quiet`) for remote URLs by default.
    *   **Path Resolution**: Determines the full path to the neuron source in the cloned brain and the neuron destination in the consumer repository. Ensures destination parent directory exists.
    *   **Directory vs. File Sync**:
        *   **Directory Neuron**:
            *   If the consumer destination doesn't exist or is not a directory, it's created/replaced by copying the entire directory tree from the brain source using `shutil.copytree` (after removing the destination if it's a file, or removing and re-copying if it's an existing directory to ensure a clean state).
            *   If the destination directory exists, it walks through the brain's neuron directory. For each file/sub-directory:
                *   Creates corresponding sub-directories in the consumer if they don't exist.
                *   For files (excluding the neuron's own `requirements.txt` if present directly in the neuron source dir), it reads the brain version and the local consumer version (if it exists).
                *   `detect_conflicts` is called. If conflicts exist, `handle_conflicts` is invoked.
                *   The consumer's file is updated with the resolved content if it differs from the original local content.
        *   **File Neuron**:
            *   The brain's file content is read.
            *   If the consumer's destination exists and is a file, `detect_conflicts` and `handle_conflicts` are used.
            *   The consumer's file is updated if the resolved content differs.
            *   If the destination doesn't exist or is a directory (type mismatch), it's created/replaced.
    *   **Requirements Merging**:
        *   After syncing the neuron's content, it checks for associated requirements files:
            *   For a directory neuron (e.g., `brain_src/my_dir/`), it looks for `brain_src/my_dir/requirements.txt` or `brain_src/my_dir/my_dirrequirements.txt`.
            *   For a file neuron (e.g., `brain_src/my_util.py`), it looks for `brain_src/my_util.pyrequirements.txt` adjacent to the neuron file.
        *   If found, `parse_requirements` reads both the neuron's requirements and the consumer's root `requirements.txt`.
        *   `merge_requirements` combines them (preferring higher `==` versions if `packaging.version` can parse, or neuron's version string otherwise if different). The consumer's root `requirements.txt` is updated.
    *   **Cleanup**: The temporary brain clone is removed.
    *   **Result**: Returns a dictionary indicating `status` (`success`/`error`), `action` (`added`/`updated`/`unchanged`/`skipped`), `message`, and `requirements_merged` (boolean).

3.  **Conflict Handling (`handle_conflicts`)**:
    *   If strategy is `prefer_brain` or `prefer_local`, returns the respective content immediately.
    *   If `prompt`:
        *   In non-interactive environments (`not sys.stdin.isatty()`), defaults to `prefer_brain`.
        *   Interactively:
            *   Shows a diff for text files using `difflib.unified_diff`.
            *   Asks user to choose: `(b)rain`, `(l)ocal`, `(m)erge` (merge only available for text files).
            *   Merge option (`m`): Uses `git merge-file` with temporary files. The merged output (potentially with conflict markers) becomes the new content.
    *   Returns a dictionary with `resolution` and `content`.

### Git Operations (`brain.git`)

Brain uses a custom `run_git_command` function that executes Git commands via `subprocess.run`.

*   **`temp_clone_repo(url, branch)`**:
    *   Creates a temporary directory.
    *   Determines if the URL is local (`file://` or an absolute path to an existing directory).
    *   Uses shallow clone (`--depth=1 --quiet`) for remote URLs. For local URLs, it's a full, quiet clone.
    *   Handles `GitError`, providing enhanced messages for GitHub authentication issues by checking `is_github_url` and `is_auth_error`.
    *   Cleans up the temporary directory on failure.
*   **File Status Checks**:
    *   `is_file_tracked()`: Uses `git ls-files --error-unmatch <file_path>`.
    *   `is_file_modified()`: Uses `git status --porcelain <file_path>`. Any output indicates a change status.
    *   `get_file_hash()`: Uses `git rev-parse HEAD:<file_path>` to get the blob hash from `HEAD`.
*   **`get_changed_files()`**: Parses `git status --porcelain` output to list all files that are modified, added, deleted, renamed, or copied in the working tree or staging area relative to `HEAD`. Attempts basic unquoting for paths with spaces.

### Export Logic (`brain.sync.export_neurons_to_brain`)

*   **Policy Check**: Verifies `ALLOW_PUSH_TO_BRAIN` is `true` in the consumer's `SYNC_POLICY`.
*   **Grouping**: Groups `modified_neurons` by their `brain_id`.
*   **Processing Each Brain**:
    *   **Local Non-Bare Brains**: If the brain's remote URL is `file://` and points to a local non-bare Git repository:
        *   Checks if the brain repo is clean (no uncommitted changes) and on the target branch (if a branch is specified in `.neurons`).
        *   If checks pass, modifications are copied directly into this local brain's working tree.
        *   `git add .` and `git commit` are run directly in the local brain repository. No `git push` is needed.
    *   **Remote or Bare Local Brains**:
        *   The brain repository is temporarily cloned (using `temp_clone_repo`).
        *   Modified neuron files/directories are copied from the consumer to the corresponding `source_path` in the temporary clone.
        *   `git add .` and `git commit` are run in the clone.
        *   `git push` is run from the clone to the brain's actual remote.
    *   **Commit Message**: A detailed commit message is generated listing the exported items (source path from brain, destination path from consumer), unless `commit_message_override` is provided.
*   **Cleanup**: The temporary clone (if used) is deleted.
*   **Important**: The current implementation of `export_neurons_to_brain` does **not** re-validate if the neuron is `readwrite` based on the target *Brain's `.brain` configuration* during the export. It relies on the provided `modified_neurons` list and the consumer's `ALLOW_PUSH_TO_BRAIN` policy.

### Debugging

Both `brain.sync` and `brain.git` include debug logging flags (`ENABLE_SYNC_DEBUG_LOGGING`, `ENABLE_GIT_DEBUG_LOGGING`). When `True`, they print messages to `sys.stderr` via `_debug_log_sync` and `_debug_log_git` respectively. These are enabled by default in the provided code.