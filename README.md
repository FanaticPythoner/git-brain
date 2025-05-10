![Git-Brain_logo_512x512](https://github.com/FanaticPythoner/git-brain/blob/main/docs/assets/Git-Brain_logo_512x512.png?raw=true)


# Brain: Intelligent Asset & Code Synchronization for Git.

**🧠 Eradicate code & asset duplication across projects! Brain repositories serve "neurons"—your chosen files, folders, and their dependencies—which Brain then intelligently and selectively syncs into any Git consumer repository. Think submodules, on steroids, and without the headaches.**

Is your organization grappling with the complexities of managing shared configurations, critical build infrastructure, or versioned design assets across a sprawling Git landscape? Are you seeking a more robust, governable alternative to the limitations of Git submodules or the chaos of ad-hoc file sharing?

Brain is a **language-agnostic Git extension, architected with enterprise-scale challenges in mind.** It provides a powerful framework for sharing and synchronizing *any* versioned asset—we call them "neurons." Whether it's **Terraform modules, JSON schemas, CI/CD pipeline configurations, security policies, legal templates, or critical software libraries and their dependencies**, Brain is *designed* to ensure they are managed centrally with clarity and consumed consistently.

**Our vision is to provide a foundational layer for reducing silos, accelerating secure delivery, and enforcing universal standards across your most critical version-controlled assets and code.**

[![PyPI version](https://img.shields.io/pypi/v/git-brain.svg)](https://pypi.org/project/git-brain/)
[![Documentation](https://img.shields.io/badge/docs-gh--pages-blue.svg)](https://fanaticpythoner.github.io/git-brain/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## 🔥 Why Brain Will Revolutionize Your Workflow (And Save Your Sanity)

Traditional methods for sharing versioned assets and code are often cumbersome and error-prone. Here’s how Brain fixes them:

*   🤯 **Obliterate Submodule Overload & Complexity:**
    *   **The Pain:** Git submodules are clunky, bring in entire repositories when you might only need a fraction, and their state management is a constant source of "did I update it right?" anxiety, often leading to detached HEADs and CI failures.
    *   **The Brain Solution:** Share *only* the specific files or directories (neurons) you need from a Brain repository. Synchronization is explicit and integrated (e.g., `brain pull`). No more unnecessary baggage or submodule update rituals.

*   🚫 **Annihilate Copy-Paste Catastrophes & Version Drift:**
    *   **The Pain:** Manual copying of assets or code across projects is a recipe for disaster, leading to version drift, bugs propagating (or critical fixes *not* propagating), and no single source of truth. It's technical debt accumulating interest.
    *   **The Brain Solution:** Neurons are synced from a single, version-controlled Brain repository. Updates are intentional, trackable, and consistent.

*   🎯 **Pinpoint Precision Sharing for Any Asset Type:**
    *   **The Pain:** Need just one configuration file, a directory of icons, or a specific build script? Submodules are too coarse. Manual copying is too risky.
    *   **The Brain Solution:** Map `configs/production.json` from your `ops-brain` to `deploy/configs/prod.json` in your app. Share `marketing-assets-brain::brand_guidelines/logos/` to `static/company_logos/`. It's language-agnostic and works for *any* file or folder.

*   💻 **Feels Like Git, Because It *Works Intelligently With* Git:**
    *   **The Pain:** New tools often mean a steep learning curve, disrupting established workflows.
    *   **The Brain Solution:** Brain uses commands like `brain pull`, `brain push`, `brain status`. If you know Git, you're already familiar. Brain intelligently extends your existing Git commands.

*   🧩 **Clear, Controllable Configuration *for Enterprise Governance*:**
    *   **The Pain:** "Magic" configurations that are hard to understand, debug, or audit.
    *   **The Brain Solution:** Two simple INI files (case-sensitive keys):
        *   `.brain` (in the Brain repository): Defines what's shareable (which neurons) and the permissions (`readonly` or `readwrite`) for those neurons.
        *   `.neurons` (in consumer repositories): Defines connections to Brain repositories and how their neurons are mapped into the local project structure.
        These files are human-readable and version-controllable, providing a clear audit trail.

*   🤝 **Smart Conflict Resolution & *Defined* Contribution Paths:**
    *   **The Pain:** "My version or their version?!" Sync conflicts are inevitable. Contributing changes back to a shared resource can be convoluted.
    *   **The Brain Solution:** Choose your conflict strategy (`prefer_brain`, `prefer_local`, or `prompt` with 3-way merge for text files using `git merge-file`). `readwrite` permissions on neurons (in `.brain`) combined with `ALLOW_PUSH_TO_BRAIN=true` (in `.neurons`) allow consumers to `brain export` their improvements.

*   🔗 **Dependency Sanity for Code Neurons (Python Focus, *Extensible Concept*):**
    *   **The Pain:** Shared code often has its own dependencies. Managing these across multiple consuming projects can lead to `requirements.txt` hell.
    *   **The Brain Solution:** Brain offers special handling for Python. If a neuron has an associated `requirements.txt` (e.g., `my_neuron_dir/requirements.txt`, `my_neuron_dir/<dirname>requirements.txt`, or `my_neuron_file.pyrequirements.txt`), Brain intelligently merges these dependencies into your consumer project's main `requirements.txt` during sync.

## 🚀 Quick Start: Experience the "Aha!" Moment in Minutes

Stop wrestling, start syncing.

### 1. Install Brain
```bash
pip install git-brain
```

### 2. Create Your First "Brain" Repository (The Central Source)
Imagine you have a set of shared Terraform modules or CI pipeline configurations.
```bash
# Create and initialize your Brain repository
mkdir shared-infra-brain
cd shared-infra-brain
git init -b main # Or your default branch name
brain brain-init --id common-infra --description "Standardized infrastructure modules & CI configs"

# Configure what's shareable in the .brain file (created by brain-init)
# Example .brain:
#   [BRAIN]
#   ID = common-infra
#   DESCRIPTION = Standardized infrastructure modules & CI configs
#   [EXPORT]
#   terraform/modules/vpc/ = readonly
#   ci/pipelines/default_build.yml = readwrite # Consumers can propose improvements
#   scripts/deploy_helpers.sh = readonly

# Create your actual shared assets
mkdir -p terraform/modules/vpc ci/pipelines scripts
echo "# Standard VPC Terraform Module v1" > terraform/modules/vpc/main.tf
echo "name: Default CI Build Pipeline v1" > ci/pipelines/default_build.yml
echo "#!/bin/bash\necho 'Deploy helper script v1'" > scripts/deploy_helpers.sh
chmod +x scripts/deploy_helpers.sh

git add .
git commit -m "feat: Initial set of shared infrastructure neurons"
# Optional: Push to a remote (e.g., GitHub, GitLab)
# git remote add origin <your-brain-repo-url>
# git push -u origin main
```

### 3. Use Neurons in Your "Consumer" Project
```bash
# Navigate to your existing project, or create a new one
cd ..
mkdir my-service-deployment
cd my-service-deployment
git init -b main

# Add the Brain (use file:// for local paths or http/ssh for remotes)
# Example for a local brain (adjust path as needed):
INFRA_BRAIN_PATH_ABS=$(cd ../shared-infra-brain && pwd) # Get absolute path
brain add-brain infra-main "file://${INFRA_BRAIN_PATH_ABS}" main

# Map specific "neurons" into your project. They appear like regular files/folders!
brain add-neuron infra-main::terraform/modules/vpc/::infra/modules/vpc/
brain add-neuron infra-main::ci/pipelines/default_build.yml::.gitlab-ci.yml

# Your .neurons file is created/updated, and neurons are synced!
ls infra/modules/vpc/
cat .gitlab-ci.yml

# Commit this Brain setup
git add .
git commit -m "feat: Integrate common infrastructure neurons via Brain"
```

### 4. The Effortless Daily Workflow
*   **Infrastructure Update in the Brain:** A new version of `default_build.yml` is committed to `shared-infra-brain`.
*   **Sync Your Service Project:** In `my-service-deployment`:
    ```bash
    brain pull # Recommended: pulls project changes AND syncs neurons (if AUTO_SYNC_ON_PULL=true)
    # OR
    brain sync # Just sync neurons
    ```
    Your `.gitlab-ci.yml` is now updated with the latest version from the Brain.

*   **Proposing a Change to a Neuron (Potentially `readwrite`):**
    You've improved `.gitlab-ci.yml` (mapped from `ci/pipelines/default_build.yml`) in your `my-service-deployment` project.
    (Ensure `ALLOW_PUSH_TO_BRAIN=true` and `ALLOW_LOCAL_MODIFICATIONS=true` in `.neurons` for this project if you intend to modify and export).
    ```bash
    # After committing your changes to .gitlab-ci.yml in my-service-deployment
    brain export .gitlab-ci.yml
    # OR, if you're pushing project changes anyway:
    # brain push --push-to-brain
    ```
    The `shared-infra-brain` now has your improvements as a new commit to `ci/pipelines/default_build.yml` (assuming `readwrite` permission was effectively granted and export successful).

## 🌱 Current Status & Our Enterprise Vision

Brain is currently in its **Alpha stage (v0.1.0)**. While the core functionality for sharing and synchronizing neurons is robust, we are actively working towards features and hardening. See [Vision & Roadmap](https://fanaticpythoner.github.io/git-brain/vision_roadmap/) for details.

## 📖 Core Concepts: Brains, Neurons, Consumers

Refer to [Core Concepts](https://fanaticpythoner.github.io/git-brain/core_concepts/) for detailed explanations.

## ⚙️ Configuration Deep Dive

Brain's power and control come from two straightforward INI configuration files. See [Configuration Files](https://fanaticpythoner.github.io/git-brain/configuration_files/) for details.

### `.brain` File (Located in the Brain Repository Root)
Defines the brain's identity and, crucially, what "neurons" it offers for sharing and under what conditions.

```ini
[BRAIN]
ID = global-brand-assets
DESCRIPTION = Official company branding materials and guidelines

[EXPORT]
logos/standard/color.svg = readonly
logos/standard/white.svg = readonly
fonts/primary_typeface.ttf = readonly
style_guides/corporate_identity.pdf = readonly
templates/presentations/quarterly_review.pptx = readwrite
src/shared_utils/ = readonly
configs/common.json = readwrite
```
*   **`[BRAIN]`**: Contains the unique `ID` and `DESCRIPTION`.
*   **`[EXPORT]`**: Lists shareable paths and their permissions (`readonly` or `readwrite`).
*(For advanced `[ACCESS]` and `[UPDATE_POLICY]` sections, see the [Configuration Files](https://fanaticpythoner.github.io/git-brain/configuration_files/) documentation.)*

### `.neurons` File (Located in the Consumer Repository Root)
Specifies which Brains this project connects to, how neurons are mapped into the local filesystem, and the policies for synchronization.

```ini
[BRAIN:brand-kit]
REMOTE = git@github.com:our-org/global-brand-assets.git
BRANCH = main

[BRAIN:ci-cd-pipelines]
REMOTE = file:///opt/shared-git/common-ci-cd-pipelines
BRANCH = stable

[SYNC_POLICY]
AUTO_SYNC_ON_PULL = true
CONFLICT_STRATEGY = prompt
ALLOW_LOCAL_MODIFICATIONS = false
ALLOW_PUSH_TO_BRAIN = false
AUTO_SYNC_ON_CHECKOUT = true

[MAP]
main_logo = brand-kit::logos/standard/color.svg::src/assets/images/company_logo.svg
style_guide_pdf = brand-kit::style_guides/corporate_identity.pdf::docs/branding/main_style_guide.pdf
default_ci = ci-cd-pipelines::gitlab/standard_build.yml::.gitlab/ci/default.yml
shared_utilities = brand-kit::src/shared_utils/::lib/common_utils/
common_config = brand-kit::configs/common.json::config/app_config.json
```
*   **`[BRAIN:<alias>]`**: Defines a connection to a brain, its `REMOTE` URL, and `BRANCH`.
*   **`[SYNC_POLICY]`**: Sets rules for synchronization, conflicts, and local changes. (Defaults apply if not specified).
*   **`[MAP]`**: Maps neurons using the format `key_name = brain_alias::path_in_brain::path_in_consumer`.
*(Consult the [Configuration Files](https://fanaticpythoner.github.io/git-brain/configuration_files/) documentation for a comprehensive explanation of all options and defaults.)*

## 🎛️ Full Command Reference

Brain seamlessly integrates with your Git workflow. Invoke as `brain <command>`.
See [Command Reference](https://fanaticpythoner.github.io/git-brain/command_reference/) for a detailed list of arguments and options.

**Brain-Specific Commands:**
*   `brain brain-init`: Initialize a directory as a new Brain repository.
*   `brain add-brain`: Register an external Brain in your consumer project.
*   `brain add-neuron`: Map a neuron from a Brain into your consumer project.
*   `brain remove-neuron`: Unmap a neuron (optionally delete local files).
*   `brain sync`: Manually synchronize neurons.
*   `brain export`: Export local neuron changes back to Brains.
*   `brain list`: Display configured neurons.

**Git Commands Enhanced by Brain:**
*   `brain pull`: `git pull` then auto-syncs neurons.
*   `brain push`: `git push` with neuron policy checks and optional `--push-to-brain`.
*   `brain status`: `git status` augmented with neuron modification status.
*   `brain clone`: `git clone` then auto-sets-up/syncs neurons.
*   `brain checkout`: `git checkout` then optionally syncs neurons.
*   `brain init`: `git init` with optional Brain/consumer setup flags.

## 💡 Advanced Scenarios & Use Cases

*   **Managing Environment-Specific Configurations:** Use different Brain branches (e.g., `dev`, `staging`, `prod`) for configuration neurons.
*   **Distributing Boilerplate/Templates:** A "project-templates" Brain can serve skeleton structures.
*   **Shared CI/CD Pipelines:** Standardize build/deployment by sharing pipeline configurations.
*   **Cross-Functional Asset Sharing:** Enable marketing, legal, design teams to manage versioned assets in dedicated Brains.

## 🤝 Contributing & Getting Involved

Brain aims to solve a widespread problem. We welcome your expertise and feedback!

*   ⭐ **Star this repository on GitHub!**
*   🚀 **Try Brain:** Integrate it into a pilot project.
*   🐞 **Report Bugs & Request Features:** Open an issue.
*   🛠️ **Contribute:** Pull requests are welcome!

## 📜 License

Brain is licensed under the **GNU General Public License v3.0**.
See the `LICENSE` file (expected to be in the repository root) for the full license text.
