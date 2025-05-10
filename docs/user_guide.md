User Guide
----------

This section provides practical guidance on using Brain for common development tasks.

### Initializing Repositories

#### Initializing a Git Repository with Brain (Consumer)

If you are starting a new project that will consume neurons:

1.  Initialize a standard Git repository:
    '''bash
    git init -b main my-new-project
    cd my-new-project
    '''
2.  You can then proceed to add brains and neurons.
    The `brain init --with-neurons` command can create a basic `.neurons` file structure for you after `git init`:
    '''bash
    # After git init in my-new-project
    brain init --with-neurons
    # This creates a skeleton .neurons file with default SYNC_POLICY and empty BRAINS/MAP.
    # You still need to run `brain add-brain` and `brain add-neuron`.
    '''

#### Initializing a Brain Repository

If you are creating a new repository to host shared code:

1.  Initialize a standard Git repository:
    '''bash
    git init -b main shared-components
    cd shared-components
    '''
2.  Run the `brain brain-init` command:
    '''bash
    brain brain-init --id my-components --description "Shared UI components" --export "src/*=readonly" --export "config/dev.json=readwrite"
    '''
    This creates the `.brain` file with the specified ID, description, and export rules.
3.  Add your shared code, commit, and (optionally) push to a remote.

### Managing Brains

#### Adding a Brain

To connect your consumer repository to a brain repository:

'''bash
brain add-brain <brain_id> <remote_url> [branch]
'''

*   `<brain_id>`: A unique alias for this brain within your consumer project (e.g., `shared_utils`, `design_assets`).
*   `<remote_url>`: The Git URL (HTTPS, SSH, or `file://` for local brains) of the brain repository.
*   `[branch]`: (Optional) The specific branch in the brain repository to track. Defaults to `main`.

Example:
'''bash
brain add-brain common-utils git@github.com:my-org/common-utils.git dev
'''
This adds a section to `.neurons`:
'''ini
[BRAIN:common-utils]
REMOTE = git@github.com:my-org/common-utils.git
BRANCH = dev
'''
Brain verifies the repository and warns if `.brain` is missing (prompting interactively).

### Managing Neurons

#### Adding a Neuron Mapping

Once a brain is added, map neurons from it:

'''bash
brain add-neuron <brain_id>::<source_path_in_brain>::<destination_path_in_consumer>
'''

*   `<brain_id>`: The alias defined via `brain add-brain`.
*   `<source_path_in_brain>`: Path in the brain repository. For directories, ensure consistent use of trailing `/` if relying on it for type detection in some contexts, though `sync_neuron` primarily checks `os.path.isdir` on the brain source.
*   `<destination_path_in_consumer>`: Path in your consumer project. For directories, ensure consistent use of trailing `/`.

Example:
'''bash
brain add-neuron common-utils::helpers/strings.py::src/lib/string_helpers.py
brain add-neuron common-utils::assets/icons/::static/common_icons/
'''
This updates the `[MAP]` section in `.neurons` and immediately syncs the new neuron. Destination directories are created if they don't exist.

#### Listing Neurons

To see configured neurons:
'''bash
brain list
'''
Output:
'''
Neurons in repository: 2

  src/lib/string_helpers.py (common-utils)
  static/common_icons/ (common-utils)
'''

For details (status: Modified, Missing, OK; size):
'''bash
brain list --verbose
'''
Filter by brain: `brain list --brain=common-utils`

#### Removing a Neuron Mapping

To remove a mapping:
'''bash
brain remove-neuron <path_in_consumer> [--delete]
'''
*   `<path_in_consumer>`: Destination path of the neuron.
*   `--delete`: (Optional) Also deletes the local file at `<path_in_consumer>` (uses `os.unlink`, fails for directories).

Example: `brain remove-neuron src/lib/string_helpers.py`
Removes mapping from `.neurons`. File remains unless `--delete` is used.

### Synchronization Workflow

#### Pulling and Automatic Sync

`brain pull` is recommended:
'''bash
brain pull [git-pull-arguments]
'''
Executes `git pull`, then (if `AUTO_SYNC_ON_PULL=true` in `.neurons`, default is true) syncs all neurons.

#### Manual Synchronization
'''bash
brain sync [neuron_path_in_consumer...] [--strategy=<strategy>] [--reset]
'''
*   `[neuron_path_in_consumer...]`: Syncs only specified neurons. If omitted, syncs all.
*   `--strategy=<strategy>`: Overrides `CONFLICT_STRATEGY` (`prompt`, `prefer_brain`, `prefer_local`).
*   `--reset`: Temporarily allows local modifications to be overwritten (influences `prompt` strategy if `ALLOW_LOCAL_MODIFICATIONS` is false, effectively making it `prefer_brain`).

#### Conflict Resolution

Handled by `brain.sync.handle_conflicts` based on effective strategy:
*   `prompt` (default): Interactive choice `(b)rain, (l)ocal, (m)erge`. `(m)erge` uses `git merge-file` for text files. Non-interactive defaults to `prefer_brain`.
*   `prefer_brain`: Overwrites local changes.
*   `prefer_local`: Keeps local changes.

If `ALLOW_LOCAL_MODIFICATIONS=false` (default) and `CONFLICT_STRATEGY=prompt`, conflicts are resolved as `prefer_brain`.

### Exporting Neuron Changes to a Brain

If a neuron is intended to be `readwrite` (defined in brain's `.brain`) and consumer's `.neurons` has `ALLOW_PUSH_TO_BRAIN=true`:

1.  Modify the neuron in your consumer repository.
2.  Commit the changes.
3.  Export:
    *   `brain export <path_to_modified_neuron_in_consumer> [--force]`
        (If no path, exports all Git-detected modified neurons. `--force` bypasses confirmation, not policy).
    *   `brain push --push-to-brain [git-push-arguments]`
        (Pushes consumer repo, then exports modified neurons).

Export process: Clones brain (or uses local non-bare directly), copies changes, commits, and pushes (if not direct local modification).

### Working with Multiple Brains

1.  Add each brain:
    '''bash
    brain add-brain core-services git@github.com:my-org/core-services.git
    brain add-brain frontend-assets https://github.com/my-org/frontend-assets.git
    '''
2.  Add neurons, specifying the `brain_id`:
    '''bash
    brain add-neuron core-services::auth/client.py::src/auth_client.py
    brain add-neuron frontend-assets::styles/main.css::static/css/theme.css
    '''

### Special Handling: `requirements.txt` (Python)

Brain can merge neuron-specific Python dependencies:
*   **Neuron-Specific Requirements Location**:
    *   Directory neuron (e.g., `my_dir/`): `my_dir/requirements.txt` or `my_dir/my_dirrequirements.txt` (inside the neuron source in the brain).
    *   File neuron (e.g., `utils.py`): `utils.pyrequirements.txt` (adjacent to `utils.py` in the brain).
*   **Merging**: During sync, Brain reads consumer's root `requirements.txt` and the neuron's requirements.
    *   New packages are added.
    *   For packages in both, if versions are `==` and parseable by `packaging.version`, the higher is chosen. Otherwise, the neuron's version string is preferred if different.
    *   Consumer's root `requirements.txt` is updated.