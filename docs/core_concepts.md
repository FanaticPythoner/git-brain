Core Concepts
-------------

Understanding these core concepts is key to effectively using Brain.

### Brain Repository

*   A **Brain Repository** is a standard Git repository that serves as a central source for shared code or assets (neurons).
*   It is identified by a `.brain` configuration file at its root.
*   The `.brain` file specifies:
    *   A unique `ID` for the brain.
    *   An optional `DESCRIPTION`.
    *   An `[EXPORT]` section detailing which files/directories (neurons) can be shared and their default permissions (`readonly` or `readwrite`).
    *   Optional `[ACCESS]` and `[UPDATE_POLICY]` sections for finer-grained control (these are parsed but their enforcement is not fully implemented in the current command logic).

### Consumer Repository

*   A **Consumer Repository** is any Git project that utilizes neurons from one or more brain repositories.
*   It is identified by a `.neurons` configuration file at its root.
*   The `.neurons` file specifies:
    *   Definitions for each brain it connects to under `[BRAIN:<brain_id>]` sections, including the brain's `REMOTE` URL and `BRANCH`.
    *   A `[SYNC_POLICY]` section dictating how neurons are synchronized, conflicts are handled, and if local modifications or exports are permitted.
    *   A `[MAP]` section (required) that defines the explicit mappings between neurons in a brain and their corresponding paths in the consumer repository.

### Neurons

*   A **Neuron** is a file or a directory that is shared from a brain repository.
*   Neurons are defined in the `[EXPORT]` section of a brain's `.brain` file, along with their `readonly` or `readwrite` permissions.
*   Consumer repositories map these neurons to local paths using the `[MAP]` section in their `.neurons` file.
*   When synchronized, the content of the neuron from the brain repository is copied into the consumer repository at the specified destination path.

### Synchronization

*   **Syncing** is the process of updating neurons in the consumer repository with the versions from their respective brain repositories (`brain.sync.sync_neuron` and `sync_all_neurons`).
*   This can be triggered automatically (e.g., on `brain pull` if `AUTO_SYNC_ON_PULL=true`, on `brain checkout` if `AUTO_SYNC_ON_CHECKOUT=true` or `--sync-neurons` flag is used) or manually (`brain sync`).
*   Conflict resolution strategies (`prefer_brain`, `prefer_local`, `prompt`) can be defined in the consumer's `[SYNC_POLICY]` or overridden during a manual `brain sync`. The `prompt` strategy uses `git merge-file` for text files.

### Exporting

*   **Exporting** is the process of sending changes made to neurons in a consumer repository back to their source brain repository (`brain.sync.export_neurons_to_brain`).
*   This is only allowed if `ALLOW_PUSH_TO_BRAIN=true` in the consumer's `[SYNC_POLICY]`.
*   The `brain export` command or `brain push --push-to-brain` facilitates this.
*   The brain repository receives these changes as new commits.
*   **Note**: The current export mechanism primarily checks the consumer's `ALLOW_PUSH_TO_BRAIN` policy. It does not re-verify the `readwrite` permission of the specific neuron from the *brain's `.brain` file* at the time of export.