Configuration Files
-------------------

Brain's behavior is primarily controlled by two INI-style configuration files: `.brain` (for brain repositories) and `.neurons` (for consumer repositories). Both files use case-sensitive keys as `ConfigParser.optionxform` is set to `str`.

### `.brain` File

Located at the root of a brain repository. Defines the properties of the brain and what it shares.

**Sections and Keys:**

1.  **`[BRAIN]`** (Required)
    *   `ID`: (Required, String) A unique identifier for this brain. This ID is used by consumers to refer to this brain.
        *Example*: `ID = my-shared-library`
    *   `DESCRIPTION`: (Optional, String) A human-readable description of the brain's purpose.
        *Example*: `DESCRIPTION = Core utility functions and common assets`

2.  **`[EXPORT]`** (Required)
    Defines which files or directories within the brain repository can be shared as neurons and their permissions.
    *   **Format**: `<path_pattern_in_brain> = <permission>`
    *   `<path_pattern_in_brain>`: (String) A path relative to the brain repository's root. Can be a file or a directory. Path patterns are stored as literal strings; glob matching interpretation is handled by consuming logic if implemented (not directly by `config.py` loading).
    *   `<permission>`: (String) Specifies how consumers can interact with the neuron.
        *   `readonly` (Default if value is missing or empty string): Consumers can only pull updates.
        *   `readwrite`: Consumers can pull updates and, if policies align, export local modifications back to the brain.
    *   *Example*:
        ```ini
        [EXPORT]
        utils/logging.py = readonly
        utils/network.py =
        configs/defaults.json = readwrite
        assets/images/ = readonly
        ```
        Here, `utils/network.py` would default to `readonly`.

3.  **`[ACCESS]`** (Optional)
    Controls which entities (e.g., users, groups) can access which exported paths. *The provided `config.py` loads this section, but the enforcement logic is not detailed in the current command implementations.*
    *   **Format**: `<entity_identifier> = <comma_separated_path_patterns>`
    *   `<entity_identifier>`: (String) An identifier for a user, group, etc. `*` is a literal.
    *   `<comma_separated_path_patterns>`: (String) A comma-separated list of path patterns from the `[EXPORT]` section. `*` is a literal. Empty paths are filtered out.
    *   *Example*:
        ```ini
        [ACCESS]
        team-alpha = utils/logging.py, utils/network.py, configs/defaults.json
        public-consumers = assets/images/
        admin-group = *
        ```

4.  **`[UPDATE_POLICY]`** (Optional)
    Defines policies for neuron updates or contributions. *The provided `config.py` loads this section, but the enforcement logic is not detailed in current command implementations.*
    *   **Format**: `<policy_key> = <value>`
    *   Supported keys and value types (interpreted from `config.py`):
        *   Boolean keys (e.g., `REQUIRE_REVIEW`): Parsed from `true`, `yes`, `1` (case-insensitive) to `True`, and `false`, `no`, `0` to `False`.
        *   `PROTECTED_PATHS`: Parsed as a comma-separated string list.
        *   Other keys are stored as stripped strings. Empty values for keys are skipped during loading unless it's a known boolean policy.
    *   *Example*:
        ```ini
        [UPDATE_POLICY]
        REQUIRE_REVIEW = true
        PROTECTED_PATHS = utils/logging.py, core_modules/
        MIN_APPROVERS = 2
        SOME_OTHER_POLICY = some_value
        ```

**Example `.brain` file:**
```ini
[BRAIN]
ID = common-widgets
DESCRIPTION = Shared UI widgets for web projects

[EXPORT]
js/widgets/datepicker.js = readonly
js/widgets/modal.js = readwrite
css/widgets/ = readonly
assets/widget-icons/*.svg = readonly

[ACCESS]
frontend-team = js/widgets/*, css/widgets/*

[UPDATE_POLICY]
REQUIRE_REVIEW = true
PROTECTED_PATHS = js/widgets/datepicker.js
```

### `.neurons` File

Located at the root of a consumer repository. Defines connections to brains, neuron mappings, and synchronization policies.

**Sections and Keys:**

1.  **`[BRAIN:<brain_id>]`** (Required for each brain connection)
    Defines a connection to a specific brain repository. `<brain_id>` is a user-defined alias for the brain within this consumer project.
    *   `REMOTE`: (Required, String) The Git URL of the brain repository. Must be non-empty.
        *Example*: `REMOTE = git@github.com:my-org/common-widgets.git`
    *   `BRANCH`: (Optional, String) The specific branch in the brain repository to track. If not specified, consuming code (e.g. `add_neuron`, `sync_neuron`) typically defaults to `main`.
        *Example*: `BRANCH = release-v2`
    *   `ARGS`: (Optional, String) Additional arguments intended for Git commands when interacting with this brain. Parsed by `config.py` but not actively used by `temp_clone_repo` for passing these args.
        *Example*: `ARGS = --depth 1`

2.  **`[SYNC_POLICY]`** (Optional, but default values apply if section or keys are absent)
    Defines global policies for neuron handling. Default values are used if section or specific keys are missing.
    *   `AUTO_SYNC_ON_PULL`: (Boolean: `true`/`false`) Default: `True`.
        *Example*: `AUTO_SYNC_ON_PULL = true`
    *   `CONFLICT_STRATEGY`: (String: `prompt`/`prefer_brain`/`prefer_local`) Default: `prompt`.
        *Example*: `CONFLICT_STRATEGY = prefer_brain`
    *   `ALLOW_LOCAL_MODIFICATIONS`: (Boolean: `true`/`false`) Default: `False`.
        *Example*: `ALLOW_LOCAL_MODIFICATIONS = false`
    *   `ALLOW_PUSH_TO_BRAIN`: (Boolean: `true`/`false`) Default: `False`.
        *Example*: `ALLOW_PUSH_TO_BRAIN = false`
    *   `AUTO_SYNC_ON_CHECKOUT`: (Boolean: `true`/`false`) Default: `False`.
        *Example*: `AUTO_SYNC_ON_CHECKOUT = true`

3.  **`[MAP]`** (Required Section)
    Defines mappings of neurons. Each entry is a key-value pair. The key name (e.g., `map1`) is arbitrary but stored as `_map_key` in the parsed mapping. The value defines the actual mapping.
    *   **Format for value**: `<brain_id>::<source_path_in_brain>::<destination_path_in_consumer>`
        *   All parts must be non-empty. `<brain_id>` must be a defined brain.
    *   **Alternative Format (if only one brain is defined)**: `<source_path_in_brain>::<destination_path_in_consumer>`
        *   Brain ID is inferred if exactly one `[BRAIN:<brain_id>]` section exists.
    *   *Example*:
        ```ini
        [MAP]
        widget_datepicker = common-widgets::js/widgets/datepicker.js::src/components/shared/datepicker.js
        widget_modal = common-widgets::js/widgets/modal.js::src/components/shared/modal.js
        widget_styles = common-widgets::css/widgets/::static/css/shared_widgets/
        icons = assets-brain::icon_set_alpha/::static/icons/vendor_alpha/
        ```

**Example `.neurons` file:**
```ini
[BRAIN:common-widgets]
REMOTE = git@github.com:my-org/common-widgets.git
BRANCH = main

[BRAIN:utility-scripts]
REMOTE = file:///opt/shared-git-repos/utility-scripts
BRANCH = master

[SYNC_POLICY]
AUTO_SYNC_ON_PULL = true
CONFLICT_STRATEGY = prompt
ALLOW_LOCAL_MODIFICATIONS = false
ALLOW_PUSH_TO_BRAIN = false
AUTO_SYNC_ON_CHECKOUT = false

[MAP]
datepicker_js = common-widgets::js/widgets/datepicker.js::assets/js/vendor/datepicker.js
modal_styles = common-widgets::css/widgets/modal.css::assets/css/vendor/modal_style.css
backup_script = utility-scripts::backup/do_backup.sh::tools/backup.sh
```