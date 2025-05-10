# Vision & Roadmap

Brain (v0.1.0) has established a strong foundation as a language-agnostic Git extension for intelligently sharing and synchronizing versioned files and directories ("neurons") from central "Brain" repositories to any number of consumer repositories. It currently excels at reducing duplication, managing local vs. remote changes with configurable conflict strategies, and even offers specialized Python dependency merging.

Our vision is to evolve Brain into an indispensable tool for **governed, scalable, and deeply integrated asset and code synchronization**, particularly for teams and enterprises managing complex inter-repository dependencies and striving for consistency.

## Current Capabilities (v0.1.0 - Alpha)

**Foundation:**
*   **Core Model:** Central Brain repositories serve versioned Neurons (files or directories) to Consumer repositories.
*   **Configuration:** Driven by `.brain` (ID, description, export paths with `readonly`/`readwrite` permissions) and `.neurons` (brain connections, sync policies, neuron mappings) INI files. Case-sensitive keys are used.
*   **Language Agnostic Sync:** Any file or folder type can be a Neuron.
*   **CLI Interface:** Comprehensive command suite (`brain-init`, `add-brain`, `add-neuron`, `remove-neuron`, `sync`, `export`, `list`).
*   **Git Command Integration:** Neuron-aware versions of `pull`, `push`, `status`, `clone`, `checkout`, `init`.
*   **Conflict Resolution:** Strategies (`prompt`, `prefer_brain`, `prefer_local`) with `git merge-file` for text-based prompts. `prompt` defaults to `prefer_brain` in non-interactive sessions.
*   **Conditional Export:** Export of locally modified Neurons back to Brains, governed by the consumer's global `ALLOW_PUSH_TO_BRAIN` policy.
*   **Python Dependency Merging:** Automatic merging of Neuron-associated `requirements.txt` into the consumer's root `requirements.txt`. Specific lookup paths for neuron requirements are:
    *   Directory Neuron (e.g., `my_dir/`): `my_dir/requirements.txt` or `my_dir/my_dirrequirements.txt`.
    *   File Neuron (e.g., `utils.py`): `utils.pyrequirements.txt`.
*   **Local Brain Optimization for Export:** Direct commits to local non-bare Brain repositories during export (if clean and on the correct branch), bypassing clone-push for efficiency.

**Observed Limitations & Areas for Growth (Based on Current Code):**
*   **`[ACCESS]` & `[UPDATE_POLICY]` in `.brain`:** While parsed by `config.py`, these sections are **not yet actively enforced** by the command logic (e.g., `add-neuron`, `sync`, `export`).
*   **Neuron-Level Permission Enforcement During Export:** The `export_neurons_to_brain` function does not currently re-verify a specific neuron's `readwrite` permission from the target Brain's `.brain` configuration before committing changes to that Brain. It relies on the `modified_neurons` list (typically from `get_modified_neurons`) and the consumer's `ALLOW_PUSH_TO_BRAIN` policy.
*   **Granular Neuron Versioning by Consumer:** Consumers track a *branch* of a Brain. There's no built-in mechanism to pin a specific Neuron mapping to an immutable Git commit/tag within the Brain.
*   **Auditing & Operational Insight:** Lacks dedicated audit logs or centralized status reporting beyond Git history and CLI output (though verbose debug logging to stderr is present).
*   **Advanced Dependency Ecosystems:** Python `requirements.txt` handling is a specialized feature. Generalizing intelligent dependency management is a future goal.
*   **User/Group Identity for Permissions:** The `[ACCESS]` section implies entity identification, but the mechanism to link these entities to actual Git users/teams is not yet defined.
*   **Distribution:** Currently relies on `pip install`. Self-contained installers would simplify setup for users less familiar with Python environments.

## The Future Vision: Evolving Brain

Our roadmap is focused on maturing Brain from a powerful utility into a strategic platform for asset and code management within Git.

### Phase 1: Solidifying Governance, Stability, & Developer Experience (Near-Term Focus)

This phase aims to build directly upon the existing architecture to deliver features crucial for team and early enterprise adoption, as well as improving the core developer experience.

1.  **Full Enforcement of `.brain` Policies:**
    *   **Implement `[ACCESS]` Section Logic:**
        *   **Goal:** Define how `<entity_identifier>` in the `.brain` file's `[ACCESS]` section is resolved (e.g., based on consumer repo URL, user, or other context).
        *   **Action:** Modify `add-neuron` and `sync` operations to check consumer context against these rules.
        *   **Impact:** True granular access control.
    *   **Implement `[UPDATE_POLICY]` Section Logic (e.g., `PROTECTED_PATHS`):**
        *   **Goal:** Enforce policies like `PROTECTED_PATHS` during `brain export`.
        *   **Impact:** Adds safety for critical Neurons.
    *   **Strict Neuron-Level Permission Enforcement on Export:**
        *   **Goal:** Ensure `export_neurons_to_brain` verifies a neuron's `readwrite` permission from the target Brain's `.brain` config before committing.
        *   **Impact:** Strengthens governance.

2.  **Neuron Version Pinning for Consumers:**
    *   **Goal:** Allow `.neurons` `[MAP]` entries to specify a Git commit SHA or tag from the Brain for a Neuron.
    *   **Syntax Idea:** `map_key = brain_id::source_path@v1.2.3::dest_path` or `map_key = brain_id::source_path@commit_sha::dest_path`
    *   **Action:** Modify `sync_neuron` to checkout the specific commit/tag in the temporary brain clone. Add `brain update-neuron <dest_path> [--version <tag_or_sha> | --latest]` command.
    *   **Impact:** **Crucial for production stability and reproducible builds in consumers.**

3.  **Enhanced Conflict Resolution & Diffing:**
    *   **Goal:** Improve the `prompt` strategy by potentially offering more advanced merge options or integration with external diff/merge tools configured by the user.
    *   **Impact:** Smoother developer experience during conflicts.

4.  **Basic Auditing & Operational Logging:**
    *   **Goal:** Implement a local Brain operational log file (e.g., in `.git/brain/logs/operation.log`) recording key actions, statuses, and errors.
    *   **Impact:** Essential traceability for troubleshooting.

5.  **Refined CLI Experience & Distribution:**
    *   **Goal:** Ensure consistent verbose/quiet modes across all commands, clear progress indicators for long operations (like cloning), and add "dry-run" flags where applicable (e.g., `brain sync --dry-run`). **Develop self-contained, cross-platform installers (e.g., using PyInstaller, Nuitka) to simplify distribution.**
    *   **Impact:** Improved usability, predictability, and wider accessibility.

6.  **Integrated Development Environment (IDE) Support - VS Code Extension (Initial):**
    *   **Goal:** Provide an official VS Code extension for Brain.
    *   **Features (Initial):**
        *   Syntax highlighting for `.brain` and `.neurons` files.
        *   Visual indicators (e.g., gutter icons, file decorations) for files/folders identified as mapped Neurons.
        *   Context menu actions or palette commands for common Brain operations (`sync selected neuron`, `sync all`, `list modified neurons`, `export neuron`).
        *   Basic status integration with VS Code's Source Control view (e.g., showing modified neurons).
    *   **Impact:** Significantly enhances developer productivity by integrating Brain into common workflows.

### Phase 2: Scaling, Broader Integration, & Project Maturity (Mid-Term)

1.  **Performance & Scalability Enhancements:**
    *   **Goal:** Optimize for scenarios with thousands of Neurons, large binary assets, and numerous consumers. This might involve more efficient cloning strategies or delta transfers.
    *   **Impact:** Ensures Brain remains performant at scale.

2.  **API for Scripting & Advanced CI/CD Integration:**
    *   **Goal:** Formalize and expose core Brain functionalities as a stable Python API for programmatic use.
    *   **Action:** Refactor command handlers to be more library-friendly, returning structured data instead of just exit codes/print statements.
    *   **Impact:** Enables deep automation, custom tooling, and richer CI/CD pipeline integrations.

3.  **Robust CI/CD for Brain Itself:**
    *   **Goal:** Implement a comprehensive Continuous Integration / Continuous Deployment pipeline for the Brain project on a platform like GitHub Actions.
    *   **Features:** Automated testing (unit, integration, E2E potentially using the demo script as a base), linting, code quality checks, automated release packaging for PyPI, and **automated building/testing of the self-contained installers.**
    *   **Impact:** Ensures project stability, quality, and reliable releases of Brain itself.

4.  **Webhook / Notification System (Conceptual):**
    *   **Goal:** Allow Brains to (optionally) notify consumers or trigger external systems (e.g., CI pipelines) when significant changes occur in exported Neurons.
    *   **Impact:** Facilitates proactive updates and automation in consumer projects.

5.  **Generalized Dependency Awareness (Research & Prototyping):**
    *   **Goal:** Extend the concept of intelligent dependency-merging beyond Python `requirements.txt` to other common ecosystems (e.g., `package.json` for Node.js, `pom.xml` for Java/Maven, `go.mod` for Go).
    *   **Impact:** Increases Brain's value for polyglot development environments.

### Phase 3: Advanced Enterprise Features & Platform Thinking (Long-Term Vision)

1.  **Centralized Brain Discovery & Management (Optional Server Component):**
    *   **Goal:** A web UI/service for organizations to register Brains, manage global policies, browse Neuron catalogs, visualize dependencies, and monitor sync health across consumers.
    *   **Impact:** Elevates Brain to a managed platform, crucial for large organizations.

2.  **Advanced Role-Based Access Control (RBAC) & Policy Engine:**
    *   **Goal:** Integrate with enterprise identity systems (LDAP, SAML, OAuth2) for fine-grained permissions on Brains, Neurons, and operations. Implement a more sophisticated policy engine.
    *   **Impact:** Meets stringent enterprise security and governance requirements.

3.  **Neuron Lifecycle Management & Semantic Versioning Awareness:**
    *   **Goal:** Introduce explicit Neuron versioning within Brains, support for deprecation workflows, SemVer awareness in Neurons, and allow consumers to pin to version ranges.
    *   **Impact:** Advanced control over Neuron evolution and consumer stability.

## Join Us in Building the Future of Shared Assets

Brain's current Alpha version already solves significant pain points. With the community's involvement and feedback, especially from those tackling complex inter-repository dependencies at scale, we can realize this ambitious vision.

*   **Try Brain:** See the [Quick Start](https://fanaticpythoner.github.io/git-brain/quickstart/).
*   **Report Issues & Suggest Features:** Visit the project's issue tracker.
*   **Contribute:** Refer to `CONTRIBUTING.md` (if available) for guidelines.

Let's make managing shared, versioned resources in Git intelligent, reliable, and finally, a pleasure.