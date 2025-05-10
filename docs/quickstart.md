Quick Start
-----------

This quick start guide will walk you through setting up a brain repository, a consumer repository, and performing basic neuron synchronization.

### 1. Creating a Brain Repository

A brain repository is a standard Git repository that has been initialized to serve neurons.

```bash
# 1. Create a directory for your shared code
mkdir our-shared-library
cd our-shared-library

# 2. Initialize it as a Git repository
# The demo script uses 'git init -b main'. Adapt if your default is different.
git init -b main

# 3. Initialize it as a Brain repository
# This creates the .brain configuration file.
brain brain-init --id our-lib --description "Our company's shared utility library"

# 4. Configure exportable neurons in the .brain file
# Open .brain and define what can be shared.
# Example content for .brain:
#   [BRAIN]
#   ID = our-lib
#   DESCRIPTION = Our company's shared utility library
#
#   [EXPORT]
#   # path_in_brain_repo = permission (readonly or readwrite)
#   utils/common.py = readonly
#   assets/branding/ = readonly
#   config/api_keys_template.json = readwrite
#
# For this quick start, let's use echo to create it:
echo "[BRAIN]" > .brain
echo "ID = our-lib" >> .brain
echo "DESCRIPTION = Our company's shared utility library" >> .brain
echo "" >> .brain
echo "[EXPORT]" >> .brain
echo "utils/common.py = readonly" >> .brain
echo "assets/branding/ = readonly" >> .brain
echo "config/api_keys_template.json = readwrite" >> .brain

# 5. Create the actual shared files and directories
mkdir -p utils
echo "# Shared Python utilities v1" > utils/common.py

mkdir -p assets/branding
echo "CompanyLogo-v1" > assets/branding/logo.svg

mkdir -p config
echo '{ "SERVICE_API_KEY": "YOUR_KEY_HERE" }' > config/api_keys_template.json

# 6. Add all files to Git and commit
git add .
git commit -m "Initial commit of shared library neurons"

# 7. (Optional) Push to a remote Git server if others need to access it
# git remote add origin <your-remote-git-server-url>/our-shared-library.git
# git push -u origin main
```

You now have a brain repository named `our-lib` ready to serve neurons.

### 2. Creating a Consumer Repository and Using Neurons

A consumer repository is any Git project that wants to use code from a brain repository.

```bash
# 1. Create a directory for your project (outside the brain repo directory)
cd .. # Go up from our-shared-library
mkdir my-application
cd my-application

# 2. Initialize it as a Git repository
git init -b main

# 3. Add the brain repository to your project's configuration
# Replace <path_to_our-shared-library_repo> with the actual file path or remote URL.
# For a local brain repository (assuming our-shared-library is a sibling directory):
BRAIN_REPO_PATH_ABS=$(cd ../our-shared-library && pwd)
brain add-brain our-lib "file://${BRAIN_REPO_PATH_ABS}" main
# This command creates/updates the .neurons file.

# 4. Add specific neurons from the brain to your project
# Format: brain add-neuron <brain_id>::<path_in_brain>::<path_in_consumer>
brain add-neuron our-lib::utils/common.py::src/shared/common_utils.py
brain add-neuron our-lib::assets/branding/::static/branding_assets/

# These commands update .neurons and immediately sync the neuron files.

# 5. Verify the neuron files are present
ls src/shared/
ls static/branding_assets/
cat src/shared/common_utils.py

# 6. Add the .neurons file and the synced neuron files to Git and commit
git add .
git commit -m "Added neurons from our-lib"
```

Your application now uses `common.py` and the branding assets from `our-shared-library`.

### 3. Daily Workflow Example

#### a. Updating a Neuron in the Brain Repository

```bash
# Navigate to the brain repository
cd ../our-shared-library

# Modify a shared file
echo "# Shared Python utilities v2 - added new_function" >> utils/common.py
git add utils/common.py
git commit -m "Updated common.py with new_function"

# (Optional) Push changes if it's a remote brain
# git push origin main
```

#### b. Synchronizing Neurons in the Consumer Repository

```bash
# Navigate to the consumer repository
cd ../my-application

# Pull changes from your project's origin and sync neurons
# The `brain pull` command first performs a `git pull` for the consumer
# repository, then, if AUTO_SYNC_ON_PULL is true (default), it syncs neurons.
brain pull

# Alternatively, to just sync neurons without pulling the consumer repo:
# brain sync

# Verify the neuron update
cat src/shared/common_utils.py
# This should now show "# Shared Python utilities v2..."

# If AUTO_SYNC_ON_PULL=false in .neurons, you'd run `brain sync` manually after `git pull`.
```

#### c. Modifying a Neuron (Potentially `readwrite`) and Exporting

Let's assume `config/api_keys_template.json` was mapped as a neuron (and its definition in the brain's `.brain` file allows `readwrite`).

```bash
# In the consumer repository (my-application)
# First, map the neuron if you haven't
brain add-neuron our-lib::config/api_keys_template.json::app_config/api_keys.json

# To enable export, you need to configure .neurons:
# Open .neurons and under [SYNC_POLICY], ensure/add:
#   ALLOW_LOCAL_MODIFICATIONS = true  (to avoid warnings/blocks on local changes)
#   ALLOW_PUSH_TO_BRAIN = true      (to enable `brain export` or `brain push --push-to-brain`)
#
# For this demo, you might manually edit .neurons or use a script.
# The demo script brain_neurons_local_simulation_demo.py directly modifies the .neurons
# file for project_beta_direct to set these policies.

# Modify the neuron locally
echo '{ "SERVICE_API_KEY": "MY_ACTUAL_KEY_FOR_PROJECT", "PROJECT_SPECIFIC_SETTING": true }' > app_config/api_keys.json
git add app_config/api_keys.json
git commit -m "Configured API key for my-application"

# Export this change back to the brain repository
# Option 1: Explicit export command
brain export app_config/api_keys.json

# Option 2: During push (if you also want to push consumer repo changes)
# brain push --push-to-brain

# Verify in the brain repository
cd ../our-shared-library
# If the brain is local non-bare and export was direct, change is already there.
# If brain is remote or bare, you'd typically `git pull` in a separate clone of the brain.
git log -p config/api_keys_template.json
cat config/api_keys_template.json
# This should show the changes made in the consumer.
# The brain repository will have a new commit for the exported change.
```

This quick start covers the fundamental operations. Explore the "Command Reference" and "Configuration Files" sections for more advanced features and detailed explanations.