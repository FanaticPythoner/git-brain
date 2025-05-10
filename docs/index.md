Welcome to the Brain Documentation!
===================================

**Brain: Git Extension for Code Sharing without Duplication.**

Brain is a Git extension designed to facilitate the sharing of code modules or assets—termed "neurons"—between different Git repositories. Instead of relying on submodules or manual copying, Brain allows consumer repositories to link to specific files or directories from central "brain" repositories. These neurons can then be synchronized, ensuring that consumer projects stay up-to-date with the shared code, while also providing mechanisms for controlled contributions back to the brain.

**Version**: 0.1.0 (as per `brain/__init__.py`)

**License**: GNU General Public License v3.0 (GPLv3) (as per `setup.py`)

Introduction
------------

### What is Brain?

In collaborative software development, especially across multiple projects or teams, the need to share common utilities, libraries, configurations, or assets arises frequently. Traditional methods like copy-pasting lead to divergence and maintenance nightmares. Git submodules can be complex to manage. Brain offers a solution by treating shared code entities as "neurons" that are version-controlled in dedicated "brain" repositories and selectively "mapped" into consumer repositories.

Brain integrates with your standard Git workflow, augmenting commands like `pull`, `push`, `clone`, `status`, `checkout`, and `init` with neuron-aware operations, while also providing its own suite of commands for managing brains and neurons.

### Key Features

*   **Centralized Code, Local Integration**: Share code from central brain repositories. Neurons are physically present (copied) into the consumer's working directory during synchronization.
*   **Granular Sharing**: Share individual files or entire directories as neurons.
*   **Git-Native Workflow**: Brain commands are extensions of Git. Standard Git operations are augmented to be neuron-aware.
*   **Configuration-Driven**: Behavior is controlled by two simple INI files (using case-sensitive keys):
    *   `.brain` (in brain repositories): Defines brain ID, description, and what can be shared (`[EXPORT]` section) with `readonly` or `readwrite` permissions.
    *   `.neurons` (in consumer repositories): Defines which brains to connect to (`[BRAIN:<brain_id>]` sections), how neurons are mapped (`[MAP]` section), and synchronization policies (`[SYNC_POLICY]`).
*   **Conflict Management**: Strategies for handling discrepancies between local neuron modifications and updates from the brain (e.g., `prefer_brain`, `prefer_local`, `prompt` which uses `git merge-file` for text).
*   **Permission Control (Conceptual & Partial)**: Brain repositories can define `readonly` or `readwrite` permissions for exported neurons in `.brain`. The consumer's `ALLOW_PUSH_TO_BRAIN` policy in `.neurons` governs export.
*   **Two-Way Synchronization (Optional & Governed)**: Consumers can export modifications made to neurons back to the brain repository if policies allow (consumer's `ALLOW_PUSH_TO_BRAIN=true`). The neuron's `readwrite` status in the brain's `.brain` file is a key intended part of this governance, though not fully enforced on export by current `export_neurons_to_brain` logic.
*   **Requirements Merging (Python)**: Special handling for Python `requirements.txt` files, allowing neuron-specific dependencies to be merged into the consumer's main requirements file during sync.