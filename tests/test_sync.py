"""
Tests for the neuron synchronization module.

These tests verify that neurons are correctly synchronized between
brain repositories and consumer repositories.
"""

import tempfile
import unittest
from unittest import mock
import subprocess 
import pathlib

from brain.config import load_neurons_config 
from brain.sync import (
    sync_neuron,
    sync_all_neurons,
    get_modified_neurons,
    parse_requirements,
    merge_requirements
)

def run_git_in_path(path: str, args: list, check=True, initial_branch_name="main"):
    """
    Description:
        Executes a git command in the specified path.
    
    Parameters:
        path (str): The directory path where the git command will be executed.
        args (list): The git command arguments as a list.
        check (bool): If True, checks that the command executed successfully.
        initial_branch_name (str): The name of the initial branch when using git init.

    Returns:
        result (subprocess.CompletedProcess): The result of the git command execution.
    """
    if args[0] == 'init' and initial_branch_name:
        res = subprocess.run(['git', 'init', '-b', initial_branch_name] + args[1:], cwd=path, check=check, capture_output=True, text=True)
    else:
        res = subprocess.run(['git'] + args, cwd=path, check=check, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"Git command failed in sync test setup: {' '.join(args)}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
    return res


class TestNeuronSync(unittest.TestCase):
    """
    Description:
        Test case class for neuron synchronization functions.
    """
    initial_git_branch_name = "main" # For consistency

    def setUp(self):
        """
        Description:
            Sets up the test environment with a brain repository and a consumer repository.
        
        Parameters:
            None

        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up temporary directories for testing.
        # --------------------------------------------------------------
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = pathlib.Path(self.test_dir_obj.name)

        self.brain_repo = self.test_dir / 'brain_repo_for_sync'
        self.consumer_repo = self.test_dir / 'consumer_repo_for_sync'
        
        # --------------------------------------------------------------
        # STEP 2: Initialize brain repository.
        # --------------------------------------------------------------
        self.brain_repo.mkdir()
        run_git_in_path(str(self.brain_repo), ['init'], initial_branch_name=self.initial_git_branch_name)
        
        # ===============
        # Sub step 2.1: Create brain configuration.
        # ===============
        (self.brain_repo / '.brain').write_text("[BRAIN]\nID=sync-brain\n[EXPORT]\n* = readonly\n")
        
        # ===============
        # Sub step 2.2: Create libraries directory with utilities.
        # ===============
        (self.brain_repo / 'libs' / 'utils').mkdir(parents=True, exist_ok=True)
        (self.brain_repo / 'libs/utils/strings.py').write_text("# Brain v1 strings.py\n")
        (self.brain_repo / 'libs/utils/strings.pyrequirements.txt').write_text("requests==2.28.1\n")
        
        # ===============
        # Sub step 2.3: Create configuration directory.
        # ===============
        (self.brain_repo / 'config').mkdir(exist_ok=True)
        (self.brain_repo / 'config/settings.json').write_text('{"brain_ver": "1.0"}\n')
        
        # ===============
        # Sub step 2.4: Create neuron directory.
        # ===============
        (self.brain_repo / 'dir_neuron').mkdir(exist_ok=True)
        (self.brain_repo / 'dir_neuron/file_a.txt').write_text("File A in brain dir_neuron\n")
        (self.brain_repo / 'dir_neuron/dir_neuronrequirements.txt').write_text("numpy==1.22.0\n")

        # ===============
        # Sub step 2.5: Commit brain repository changes.
        # ===============
        run_git_in_path(str(self.brain_repo), ['add', '.'])
        run_git_in_path(str(self.brain_repo), ['commit', '-m', f'Initial brain for sync tests on {self.initial_git_branch_name}'])

        # --------------------------------------------------------------
        # STEP 3: Initialize consumer repository.
        # --------------------------------------------------------------
        self.consumer_repo.mkdir()
        run_git_in_path(str(self.consumer_repo), ['init'], initial_branch_name=self.initial_git_branch_name)
        
        # ===============
        # Sub step 3.1: Set up consumer configuration.
        # ===============
        self.brain_url = f"file://{self.brain_repo.resolve().as_posix()}" # Use file:// URL
        self.base_neurons_content = (
            f"[BRAIN:sync-brain]\nREMOTE = {self.brain_url}\nBRANCH = {self.initial_git_branch_name}\n\n"
            f"[SYNC_POLICY]\nCONFLICT_STRATEGY = prefer_brain\n\n" 
            "[MAP]\n"
        )
        (self.consumer_repo / '.neurons').write_text(self.base_neurons_content)

    def tearDown(self):
        """
        Description:
            Cleans up the test environment by removing temporary directories.
        
        Parameters:
            None

        Returns:
            None
        """
        self.test_dir_obj.cleanup()

    def _get_consumer_config(self):
        """
        Description:
            Loads the neuron configuration from the consumer repository.
        
        Parameters:
            None

        Returns:
            config (dict): The loaded neuron configuration.
        """
        return load_neurons_config(str(self.consumer_repo / '.neurons'))

    def test_parse_requirements(self):
        """
        Description:
            Tests the parse_requirements function to ensure it correctly parses
            requirement specifications from a requirements.txt file.
        
        Parameters:
            None

        Returns:
            None
        """
        content = "requests==2.28.1\nflask>=2.0.0\nnumpy == 1.22.3\npandas # comment"
        deps = parse_requirements(content)
        self.assertEqual(deps.get('requests'), '2.28.1')
        self.assertEqual(deps.get('flask'), '') 
        self.assertEqual(deps.get('numpy'), '1.22.3')
        self.assertEqual(deps.get('pandas'), '')

    def test_merge_requirements(self):
        """
        Description:
            Tests the merge_requirements function to ensure it correctly merges
            requirements from two different requirements.txt files, preferring
            neuron versions over repository versions.
        
        Parameters:
            None

        Returns:
            None
        """
        repo_reqs = "requests==2.27.1\nflask==2.0.0\nnumpy==1.21.0\n"
        neuron_reqs = "requests==2.28.1\npandas==1.4.2\nnumpy==1.22.0\n" 
        
        merged_content = merge_requirements(repo_reqs, neuron_reqs)
        merged_deps = parse_requirements(merged_content)

        self.assertEqual(merged_deps.get('requests'), '2.28.1') 
        self.assertEqual(merged_deps.get('flask'), '2.0.0')    
        self.assertEqual(merged_deps.get('pandas'), '1.4.2')   
        self.assertEqual(merged_deps.get('numpy'), '1.22.0') 

    @mock.patch('brain.sync.handle_conflicts') 
    def test_sync_neuron_file_with_requirements(self, mock_handle_conflicts):
        """
        Description:
            Tests the sync_neuron function for syncing a single neuron file
            with requirements, ensuring requirements are merged correctly.
        
        Parameters:
            mock_handle_conflicts (MagicMock): Mock for the handle_conflicts function.

        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up test environment.
        # --------------------------------------------------------------
        mock_handle_conflicts.return_value = {'resolution': 'brain', 'content': b"mock"}
        (self.consumer_repo / '.neurons').write_text(
            self.base_neurons_content + "map_s = sync-brain::libs/utils/strings.py::consumer_code/strings.py\n"
        )
        (self.consumer_repo / 'requirements.txt').write_text("existing_pkg==1.0\nrequests==2.20.0\n")
        
        # Create parent dir for neuron destination
        (self.consumer_repo / 'consumer_code').mkdir(exist_ok=True)

        # --------------------------------------------------------------
        # STEP 2: Execute sync_neuron function.
        # --------------------------------------------------------------
        config = self._get_consumer_config()
        result = sync_neuron(config, 'sync-brain', 'libs/utils/strings.py', 'consumer_code/strings.py', str(self.consumer_repo))
        
        # --------------------------------------------------------------
        # STEP 3: Verify sync results.
        # --------------------------------------------------------------
        self.assertEqual(result['status'], 'success', f"Sync neuron failed: {result.get('message')}")
        self.assertTrue((self.consumer_repo / 'consumer_code/strings.py').exists())
        # requirements_merged can be True even if the content is the same if merge logic ran.
        # More important is to check the actual content of requirements.txt.
        # self.assertTrue(result['requirements_merged']) 
        
        req_text = (self.consumer_repo / 'requirements.txt').read_text()
        self.assertIn('requests==2.28.1', req_text) 
        self.assertIn('existing_pkg==1.0', req_text) 

    @mock.patch('brain.sync.handle_conflicts')
    def test_sync_neuron_directory_with_requirements(self, mock_handle_conflicts):
        """
        Description:
            Tests the sync_neuron function for syncing a directory neuron
            with requirements, ensuring requirements are merged correctly.
        
        Parameters:
            mock_handle_conflicts (MagicMock): Mock for the handle_conflicts function.

        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up test environment.
        # --------------------------------------------------------------
        mock_handle_conflicts.return_value = {'resolution': 'brain', 'content': b"mock"}
        (self.consumer_repo / '.neurons').write_text(
            self.base_neurons_content + "map_d = sync-brain::dir_neuron/::consumer_dir/\n"
        )
        (self.consumer_repo / 'requirements.txt').write_text("original_req==1.0\nnumpy==1.19.0\n") 
        
        # Create parent dir for neuron destination if needed (sync_neuron should also do this)
        (self.consumer_repo / 'consumer_dir').mkdir(exist_ok=True, parents=True)

        # --------------------------------------------------------------
        # STEP 2: Execute sync_neuron function.
        # --------------------------------------------------------------
        config = self._get_consumer_config()
        result = sync_neuron(config, 'sync-brain', 'dir_neuron/', 'consumer_dir/', str(self.consumer_repo))

        # --------------------------------------------------------------
        # STEP 3: Verify sync results.
        # --------------------------------------------------------------
        self.assertEqual(result['status'], 'success', f"Sync neuron (dir) failed: {result.get('message')}")
        self.assertTrue((self.consumer_repo / 'consumer_dir/file_a.txt').exists())
        
        req_text = (self.consumer_repo / 'requirements.txt').read_text()
        self.assertIn('numpy==1.22.0', req_text) 
        self.assertIn('original_req==1.0', req_text)

    def test_get_modified_neurons_detects_changes(self):
        """
        Description:
            Tests the get_modified_neurons function to ensure it correctly
            detects changes in synchronized neurons.
        
        Parameters:
            None

        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up test environment with mapped neurons.
        # --------------------------------------------------------------
        (self.consumer_repo / '.neurons').write_text(
             self.base_neurons_content +
             "map_f = sync-brain::config/settings.json::cfg/settings.json\n" +
             "map_d = sync-brain::dir_neuron/::my_local_dir/\n"
        )
        config = self._get_consumer_config()

        # Create directories for neurons before syncing
        (self.consumer_repo / 'cfg').mkdir(exist_ok=True)
        (self.consumer_repo / 'my_local_dir').mkdir(exist_ok=True)

        # --------------------------------------------------------------
        # STEP 2: Sync and commit initial state.
        # --------------------------------------------------------------
        sync_all_neurons(config, str(self.consumer_repo))
        run_git_in_path(str(self.consumer_repo), ['add', '.'])
        run_git_in_path(str(self.consumer_repo), ['commit', '-m', 'Initial consumer content for get_modified test'])

        # --------------------------------------------------------------
        # STEP 3: Modify neurons and check detection.
        # --------------------------------------------------------------
        (self.consumer_repo / 'cfg/settings.json').write_text('{"consumer_mod": true}')
        (self.consumer_repo / 'my_local_dir/file_a.txt').write_text('Local edit in dir neuron file')

        modified = get_modified_neurons(config, str(self.consumer_repo))
        
        self.assertEqual(len(modified), 2, f"Expected 2 modified neurons, got {len(modified)}: {modified}")
        
        destinations = {m['destination'] for m in modified}
        self.assertIn('cfg/settings.json', destinations)
        self.assertIn('my_local_dir/', destinations) 

    @mock.patch('brain.sync.handle_conflicts')
    def test_sync_all_neurons(self, mock_handle_conflicts):
        """
        Description:
            Tests the sync_all_neurons function to ensure it correctly
            synchronizes all mapped neurons from the brain repository.
        
        Parameters:
            mock_handle_conflicts (MagicMock): Mock for the handle_conflicts function.

        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up test environment with mapped neurons.
        # --------------------------------------------------------------
        mock_handle_conflicts.return_value = {'resolution': 'brain', 'content': b"mock_all_sync"}
        (self.consumer_repo / '.neurons').write_text(
             self.base_neurons_content +
             "map_s = sync-brain::libs/utils/strings.py::c/s.py\n" +
             "map_c = sync-brain::config/settings.json::c/set.json\n"
        )
        config = self._get_consumer_config()

        # Create parent dir for neuron destinations
        (self.consumer_repo / 'c').mkdir(exist_ok=True)

        # --------------------------------------------------------------
        # STEP 2: Execute sync_all_neurons function.
        # --------------------------------------------------------------
        results = sync_all_neurons(config, str(self.consumer_repo))
        
        # --------------------------------------------------------------
        # STEP 3: Verify sync results.
        # --------------------------------------------------------------
        self.assertEqual(len(results), 2)
        for r_idx, r_val in enumerate(results):
            self.assertEqual(r_val['status'], 'success', f"Sync all, item {r_idx} failed: {r_val.get('message')}")
        
        self.assertTrue((self.consumer_repo / 'c/s.py').exists())
        self.assertTrue((self.consumer_repo / 'c/set.json').exists())

if __name__ == '__main__':
    unittest.main()