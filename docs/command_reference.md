Command Reference
-----------------

Brain extends Git with several specific commands and augments some standard Git commands.

### Brain-Specific Commands

These commands are unique to the Brain extension.

#### `brain brain-init`

Initializes the current Git repository as a brain repository.

*   **Usage**: `brain brain-init --id <unique_id> [--description <text>] [--export <path=permission>...]`
*   **Arguments**:
    *   `--id <unique_id>`: (Required) A unique identifier for this brain.
    *   `--description <text>`: (Optional) A human-readable description for this brain. Defaults to "Shared code repository".
    *   `--export <path=permission>`: (Optional, can be repeated) Defines a path pattern within the brain that can be exported as a neuron.
        *   `<path>`: The file or directory pattern (e.g., `src/*.py`, `assets/`).
        *   `<permission>`: Access permission, either `readonly` or `readwrite`. If only `<path>` is provided (e.g., `--export path/to/file`), it defaults to `readonly`.
*   **Behavior**:
    *   Creates a `.brain` file in the current directory.
    *   Populates the `[BRAIN]` section with the `ID` and `DESCRIPTION`.
    *   Populates the `[EXPORT]` section based on `--export` arguments. Each path is stored with its specified permission.
    *   Exits with an error (code 1, printed message) if `.brain` already exists. No `--force` option is currently implemented.
*   **Example**: `brain brain-init --id common-libs --export "utils/*.py=readonly" --export "config/defaults.ini=readwrite"`

#### `brain add-brain`

Adds a remote brain repository to the current consumer repository's configuration.

*   **Usage**: `brain add-brain <brain_id> <remote_url> [branch]`
*   **Arguments**:
    *   `<brain_id>`: A unique alias for this brain within the consumer project.
    *   `<remote_url>`: The Git URL of the brain repository (e.g., `https://...`, `git@...`, `file://...`).
    *   `[branch]`: (Optional) The branch in the brain repository to track. Defaults to `main`.
*   **Behavior**:
    *   Modifies or creates the `.neurons` file in the current directory. If `.neurons` doesn't exist or is invalid, it initializes a new structure with default `SYNC_POLICY` and empty `BRAINS` and `MAP`.
    *   Adds a new section `[BRAIN:<brain_id>]` with `REMOTE` and `BRANCH` keys.
    *   Verifies the brain repository by attempting a temporary clone using `brain.git.temp_clone_repo`. If the remote repository does not contain a `.brain` file at its root, it issues a warning.
        *   If in an interactive session (`sys.stdin.isatty()`), it prompts the user ("Continue adding this brain anyway? (y/N):") before proceeding if `.brain` is missing.
        *   If non-interactive, it proceeds with the warning.
    *   Exits with code 1 if the specified `brain_id` already exists in the configuration or if the brain repository is inaccessible.
*   **Example**: `brain add-brain central-assets file:///mnt/shared/git/central-assets-repo feature-branch`

#### `brain add-neuron`

Adds a neuron mapping from an already-added brain to the consumer repository.

*   **Usage**: `brain add-neuron <brain_id>::<source_path>::<destination_path>`
*   **Arguments**:
    *   `<mapping_str>`: A single string defining the mapping, with parts separated by `::`.
        *   `<brain_id>`: The alias of the brain (must exist in a `[BRAIN:<brain_id>]` section in `.neurons`).
        *   `<source_path>`: Path to the file or directory in the brain repository.
        *   `<destination_path>`: Path where the neuron will be placed in the consumer repository.
*   **Behavior**:
    *   Loads `.neurons`. Exits if it's not found or the specified `brain_id` is not configured.
    *   Verifies that `<source_path>` exists in the specified brain by temporarily cloning the brain. Exits if not found.
    *   Updates the `[MAP]` section in the `.neurons` file with the new mapping (as `brain_id`, `source`, `destination` dictionary). Avoids adding duplicate identical mappings.
    *   Immediately attempts to synchronize the newly added neuron using `brain.sync.sync_neuron`.
*   **Example**: `brain add-neuron central-assets::logos/company_logo.svg::static/images/logo.svg`

#### `brain remove-neuron`

Removes a neuron mapping from the consumer repository's configuration.

*   **Usage**: `brain remove-neuron <neuron_path_in_consumer> [--delete]`
*   **Arguments**:
    *   `<neuron_path_in_consumer>`: The destination path of the neuron in the consumer repository as specified in the mapping.
    *   `--delete`: (Optional flag) If present, the actual neuron file at `<neuron_path_in_consumer>` will also be deleted from the filesystem using `os.unlink()`. This only works for files, not directories.
*   **Behavior**:
    *   Removes the corresponding entry from the `[MAP]` list in the `.neurons` file (matches based on the `destination` field of mappings).
    *   If `--delete` is used and the path exists as a file, it's unlinked. Errors if it's a directory or `os.unlink` fails.
*   **Example**: `brain remove-neuron static/images/logo.svg --delete`

#### `brain sync`

Synchronizes neurons in the consumer repository with their versions in the brain repositories.

*   **Usage**: `brain sync [neuron_path_in_consumer...] [--reset] [--strategy <strategy_name>]`
*   **Arguments**:
    *   `[neuron_path_in_consumer...]`: (Optional) Space-separated list of neuron destination paths to sync. If omitted, all mapped neurons are synced using `brain.sync.sync_all_neurons`.
    *   `--reset`: (Optional flag) If present, temporarily sets `ALLOW_LOCAL_MODIFICATIONS=true` in the in-memory `neurons_config` for this sync operation. This effectively makes the conflict strategy behave like `prefer_brain` if it was `prompt` and local modifications were disallowed. *It does not directly set `CONFLICT_STRATEGY` to `prefer_brain` but influences its behavior when `ALLOW_LOCAL_MODIFICATIONS` is false.*
    *   `--strategy <strategy_name>`: (Optional) Overrides the `CONFLICT_STRATEGY` from `.neurons` for this sync operation. Valid strategies: `prompt`, `prefer_brain`, `prefer_local`.
*   **Behavior**:
    *   For each neuron to be synced (either specified or all):
        *   Uses `brain.sync.sync_neuron` which fetches the latest version from its brain repository.
        *   Compares it with the local version.
        *   Handles conflicts based on the effective conflict strategy (see `brain.sync.sync_neuron` and `brain.sync.handle_conflicts` for details).
        *   Updates the local neuron file(s)/directory.
        *   Merges any neuron-specific `requirements.txt` into the consumer's main `requirements.txt`.
    *   Reports a summary of actions (added, updated, unchanged, errors).
*   **Example**: `brain sync src/shared_utils.py --strategy prefer_brain`

#### `brain export`

Exports local changes made to neurons in the consumer repository back to their respective brain repositories.

*   **Usage**: `brain export [neuron_path_in_consumer...] [--force]`
*   **Arguments**:
    *   `[neuron_path_in_consumer...]`: (Optional) Space-separated list of neuron destination paths to export. If omitted, Brain uses `brain.sync.get_modified_neurons` to find all neurons with local Git changes and attempts to export them.
    *   `--force`: (Optional flag) If present, bypasses the interactive confirmation prompt ("Continue with export? (y/N):"). It does **not** bypass the `ALLOW_PUSH_TO_BRAIN=false` policy check.
*   **Behavior**:
    *   Requires `ALLOW_PUSH_TO_BRAIN=true` in the `[SYNC_POLICY]` of `.neurons`. Exits with an error if this is false and `--force` is not used to bypass confirmation (but still fails if policy is false).
    *   For each specified (or detected modified) neuron:
        *   Uses `brain.sync.export_neurons_to_brain`.
        *   If the brain is a local, non-bare repository (and clean, on correct branch), changes are committed directly.
        *   Otherwise, temporarily clones the brain, copies neuron content, commits, and pushes to the brain's remote.
    *   **Note**: The export command itself relies on `get_modified_neurons` if no paths are provided. The `export_neurons_to_brain` function does not currently re-validate against the brain's `.brain` file if a neuron is `readwrite`; it assumes the `modified_neurons` list is correct and proceeds if `ALLOW_PUSH_TO_BRAIN` is true.
*   **Example**: `brain export config/custom_settings.json`

#### `brain list`

Lists the neurons configured in the current consumer repository.

*   **Usage**: `brain list [-v | --verbose] [--brain <brain_id>]`
*   **Arguments**:
    *   `-v`, `--verbose`: (Optional flag) Show detailed information, including brain remotes/branches, source paths, neuron status (Modified, Missing, OK based on `os.path.exists` and `brain.git.is_file_modified`), and file/directory sizes.
    *   `--brain <brain_id>`: (Optional) Filter the list to show only neurons from the specified brain ID.
*   **Behavior**: Reads the `.neurons` file and displays formatted information.
*   **Example**: `brain list --verbose --brain common-utils`

### Standard Git Commands with Brain Integration

Brain augments the behavior of several standard Git commands. They are invoked as `brain <git_command>`.

#### `brain pull`

Pulls changes from the consumer repository's remote and then synchronizes neurons.

*   **Usage**: `brain pull [git_pull_options...]`
*   **Behavior**:
    1.  Executes `git pull` with any specified options for the consumer repository.
    2.  If the pull is successful and `AUTO_SYNC_ON_PULL=true` in `[SYNC_POLICY]` of `.neurons` (default is `true`), it then performs a full neuron synchronization (equivalent to `brain sync` for all neurons).
*   **Exit Codes**: Returns Git's exit code if `git pull` fails. Returns 0 on overall success, or 1 if neuron syncing encounters errors or neuron config loading fails.

#### `brain push`

Pushes the consumer repository's changes to its remote, with neuron protection and optional export.

*   **Usage**: `brain push [--push-to-brain] [git_push_options...]`
*   **Arguments**:
    *   `--push-to-brain`: (Optional flag) If present, after a successful `git push` of the consumer repository, Brain will also export any modified neurons (identified by `brain.sync.get_modified_neurons`) to their respective brain repositories.
    *   Other arguments are standard `git push` options (e.g., `--force`, `-f`).
*   **Behavior**:
    1.  **Pre-push checks (if `.neurons` file exists)**:
        *   If there are modified neurons (from `get_modified_neurons`) AND `ALLOW_LOCAL_MODIFICATIONS=false` in `[SYNC_POLICY]` AND the push is not forced (i.e., no `--force` or `-f` among `git_push_options`), the command errors out, instructing to reset neurons, change policy, or use `--force`.
        *   If `--push-to-brain` is used but `ALLOW_PUSH_TO_BRAIN=false` in `[SYNC_POLICY]`, it errors out.
    2.  Executes `git push` with filtered arguments (removes `--push-to-brain`) for the consumer repository.
    3.  If the `git push` is successful and `--push-to-brain` was specified (and `neurons_config` and `modified_neurons` are available), it proceeds to export modified neurons using `brain.sync.export_neurons_to_brain`.
*   **Exit Codes**: Returns Git's exit code if `git push` fails. Returns 0 on success, or 1 if neuron policy checks fail or neuron exporting encounters errors.

#### `brain status`

Shows the status of the consumer repository, including the status of neuron files.

*   **Usage**: `brain status [git_status_options...]`
*   **Arguments**: Standard `git status` options. Brain adds its output after Git's.
*   **Behavior**:
    1.  Executes `git status` with any specified options.
    2.  If a `.neurons` file is present and loaded successfully:
        *   Identifies and lists any mapped neurons that are locally modified (using `get_modified_neurons`).
        *   Provides warnings/notes based on `SYNC_POLICY` (e.g., if local modifications are disallowed but present, or notes about exporting).
        *   If `--neuron-mappings` or `-v`/`--verbose` are passed as arguments to `brain status`, it lists all configured neuron mappings.
*   **Exit Codes**: Returns Git's exit code on `git status` failure. Returns 1 if neuron configuration loading fails. Otherwise 0.

#### `brain clone`

Clones a repository and then sets up its neurons if configured.

*   **Usage**: `brain clone <repository_url> [directory] [git_clone_options...]`
*   **Behavior**:
    1.  Executes `git clone` with all provided arguments.
    2.  If the clone is successful and the cloned repository (path determined from `args`) contains a `.neurons` file at its root:
        *   It changes directory into the cloned repository.
        *   Loads the `.neurons` file.
        *   Performs a full neuron synchronization (equivalent to `brain sync` for all neurons using `sync_all_neurons`).
        *   Changes back to the original directory.
*   **Exit Codes**: Returns Git's exit code if `git clone` fails. Otherwise 0 (even if neuron setup or sync has issues, current code returns 0 after successful clone).

#### `brain checkout`

Checks out a branch/path and optionally synchronizes neurons.

*   **Usage**: `brain checkout <branch_or_path...> [--sync-neurons | --no-sync-neurons] [git_checkout_options...]`
*   **Arguments**:
    *   `--sync-neurons`: (Brain-specific flag) Force neuron synchronization after checkout.
    *   `--no-sync-neurons`: (Brain-specific flag) Prevent neuron synchronization after checkout, even if `AUTO_SYNC_ON_CHECKOUT` is true.
    *   Other arguments are standard `git checkout` arguments.
*   **Behavior**:
    1.  Executes `git checkout` with filtered arguments (Brain-specific flags removed).
    2.  If the checkout is successful and a `.neurons` file exists and loads:
        *   Synchronization occurs if (`AUTO_SYNC_ON_CHECKOUT=true` in `[SYNC_POLICY]` AND `--no-sync-neurons` was NOT given) OR if `--sync-neurons` was explicitly given. `AUTO_SYNC_ON_CHECKOUT` defaults to `false` if not in config.
*   **Exit Codes**: Returns Git's exit code if `git checkout` fails. Returns 1 if neuron configuration loading fails or `sync_all_neurons` encounters errors. Otherwise 0.

#### `brain init`

Initializes a Git repository and can optionally set it up as a brain or with a neuron configuration.

*   **Usage**: `brain init [directory] [--as-brain] [--brain-id <id>] [--brain-description <desc>] [--with-neurons] [git_init_options...]`
*   **Arguments**:
    *   `[directory]`: (Optional) Standard `git init` directory argument.
    *   `--as-brain`: (Brain-specific flag) Initialize as a brain repository.
    *   `--brain-id <id>`: (Brain-specific) ID for the brain if `--as-brain` is used. Defaults to the basename of the repository directory.
    *   `--brain-description <desc>`: (Brain-specific) Description for the brain if `--as-brain` is used. Defaults to "Brain repository: <brain_id>".
    *   `--with-neurons`: (Brain-specific flag) Initialize with a basic `.neurons` configuration file.
    *   Other arguments are standard `git init` options, passed through.
*   **Behavior**:
    1.  Executes `git init` with filtered arguments.
    2.  If successful, and in the target directory (changes to `directory` if specified):
        *   If `--as-brain` is used, creates and populates a `.brain` file. The `[EXPORT]` section defaults to `* = readonly`.
        *   If `--with-neurons` is used, creates a skeleton `.neurons` file with default `SYNC_POLICY` and empty `BRAINS` and `MAP` sections.
*   **Exit Codes**: Returns Git's exit code if `git init` fails. Otherwise 0.

#### Other Git Commands

Any other Git command (e.g., `commit`, `branch`, `merge`, `log`) invoked via `brain <command> [args]` will be passed directly to `git <command> [args]` by `brain.cli.main`.
Example: `brain commit -m "My changes"` is equivalent to `git commit -m "My changes"`.