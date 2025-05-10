Troubleshooting
---------------

*   **Command `brain` not found**:
    *   Ensure Brain is installed (`pip install git-brain`).
    *   Verify that the directory containing Python scripts (e.g., `~/.local/bin` on Linux, Python's `Scripts` folder on Windows, or your virtual environment's `bin` directory) is in your system's `PATH` environment variable.

*   **"ERROR: No .neurons file found."** (or similar `NeuronsConfigError`):
    *   This message appears when running commands like `brain add-neuron`, `brain sync`, `brain list`, etc., in a directory that hasn't been configured as a consumer or where the `.neurons` file is missing/misnamed.
    *   Solution: Ensure you are in the correct consumer repository directory. Run `brain add-brain` first if no brains have been added yet. For `brain init` in a new consumer repo, use `brain init --with-neurons` to create a skeleton `.neurons` file.

*   **"ERROR: Brain '<brain_id>' not found in configuration"**:
    *   When using `brain add-neuron`, the specified `<brain_id>` must match an existing `[BRAIN:<brain_id>]` section in your `.neurons` file.
    *   Solution: Verify the `brain_id` in your command and in `.neurons`. Use `brain add-brain` if the brain hasn't been added.

*   **"ERROR: Source path '<path>' not found in brain repository"**:
    *   When using `brain add-neuron` or `brain sync`, Brain temporarily clones the brain repository to check/get the `<source_path>`. This error means it doesn't exist there.
    *   Solution: Double-check the `<source_path>` in your command or `.neurons` mapping. Ensure it's correct and the file/directory exists on the specified `BRANCH` of the brain repository.

*   **Git Clone/Fetch Failures (e.g., during `add-brain`, `add-neuron`, `sync`, `export`)**:
    *   These often manifest as `GitError` messages from `brain.git` module functions.
    *   **Authentication Issues**: If the brain URL is private (e.g., private GitHub repo):
        *   For HTTPS URLs: Ensure your Git credential manager is configured, or use a Personal Access Token (PAT) with appropriate permissions.
        *   For SSH URLs: Ensure your SSH key is correctly set up and added to your Git provider.
        *   The error message from `brain.git.temp_clone_repo` attempts to provide more specific hints for GitHub authentication errors.
    *   **Network Issues**: Check your internet connection and firewall settings.
    *   **Incorrect URL/Branch**: Verify the `REMOTE` URL and `BRANCH` in your `.neurons` file for the relevant brain.

*   **Conflicts During Sync**:
    *   If `CONFLICT_STRATEGY=prompt` and you see conflict markers (```<<<<<<<```, ```=======```, ```>>>>>>>```) after choosing `(m)erge`, you need to manually edit the file to resolve these conflicts, then `git add` the resolved file.
    *   If `CONFLICT_STRATEGY=prefer_brain`, your local changes to neurons will be overwritten without prompt.
    *   If `CONFLICT_STRATEGY=prefer_local`, the neuron will not be updated from the brain if local changes exist.

*   **Export Failures (`brain export` or `brain push --push-to-brain`)**:
    *   **Policy**: Ensure `ALLOW_PUSH_TO_BRAIN=true` in `[SYNC_POLICY]` of `.neurons`. The `brain export` command will error out if this is `false` (the `--force` flag for `brain export` only bypasses the confirmation prompt, not this policy check).
    *   **Permissions (Conceptual)**: While `export_neurons_to_brain` doesn't currently re-check, the *intention* is that the neuron should be `readwrite` in the brain's `.brain` file's `[EXPORT]` section.
    *   **Brain Repo State (for local non-bare brains)**: If exporting to a local non-bare brain, ensure it has no uncommitted changes and is on the correct branch (as specified in `.neurons`).
    *   **Push Failures to Brain Remote**: Similar to clone/fetch failures, check authentication and permissions for pushing to the brain's remote repository.

*   **Python `packaging` module not found**:
    *   The `sync.py` module attempts to use `from packaging.version import parse`. If this fails (due to `ImportError`), version comparison for requirements merging becomes less precise (simple string comparison).
    *   Solution: Ensure `packaging` is installed. It's a dependency in `setup.py` (`install_requires=["packaging>=20.0"]`), so it should be installed with `git-brain`. If not, `pip install packaging`.

*   **"File is effectively binary for diffing" during sync conflict prompt**:
    *   This means `handle_conflicts` could not decode either the local or brain version of the file as UTF-8. The `(m)erge` option will not be available. You can only choose `(b)rain` or `(l)ocal`.

*   **Debug Logs**:
    *   Brain's `git.py` and `sync.py` modules have `ENABLE_GIT_DEBUG_LOGGING` and `ENABLE_SYNC_DEBUG_LOGGING` flags, respectively. These are `True` by default in the provided code. Debug messages are printed to `sys.stderr` and can be very helpful for diagnosing issues.