"""
Tests for the brain command implementations.

These tests verify that the brain commands work correctly.
"""

import os
import tempfile
import unittest
from unittest import mock
import subprocess 
import pathlib


from brain.commands.pull import handle_pull
from brain.commands.push import handle_push
from brain.commands.clone import handle_clone
from brain.commands.brain_init import handle_brain_init
from brain.commands.add_brain import handle_add_brain
from brain.commands.add_neuron import handle_add_neuron
from brain.commands.remove_neuron import handle_remove_neuron
from brain.commands.sync import handle_sync
from brain.commands.list import handle_list
from brain.commands.init import handle_init 

def run_git_in_path(path: str, args: list, check=True, initial_branch_name="main"):
    """
    Description:
        Executes a git command in the specified path with standardized branch naming.
    
    Parameters:
        path (str): The directory path where the git command will be executed
        args (list): List of git command arguments
        check (bool): Whether to raise an exception on command failure
        initial_branch_name (str): The name to use for the initial branch when running git init

    Returns:
        subprocess.CompletedProcess: Result of the git command execution
    """
    if args[0] == 'init' and initial_branch_name:
        # Modern Git might use 'main' by default, but older might use 'master'.
        # To ensure consistency for tests, we can set the initial branch.
        # `git init -b <branch_name>` sets the initial branch name.
        res = subprocess.run(['git', 'init', '-b', initial_branch_name] + args[1:], cwd=path, check=check, capture_output=True, text=True)
    else:
        res = subprocess.run(['git'] + args, cwd=path, check=check, capture_output=True, text=True)
    if check and res.returncode != 0:
        print(f"Git command failed in setup: {' '.join(args)}")
        print(f"Stdout: {res.stdout}")
        print(f"Stderr: {res.stderr}")
    return res


class TestCommandBase(unittest.TestCase):
    """Base class for command tests with shared setup."""
    
    initial_git_branch_name = "main" # Consistent branch name for test repos

    def setUp(self):
        """
        Description:
            Sets up the test environment by creating temporary directories and initializing git repositories.
            Creates a brain repository with sample files and a consumer repository.
        
        Parameters:
            None
    
        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Create temporary test directories.
        # --------------------------------------------------------------
        self.test_dir_obj = tempfile.TemporaryDirectory() 
        self.test_dir_path = pathlib.Path(self.test_dir_obj.name)

        self.brain_repo_path = self.test_dir_path / 'actual_brain_repo'
        self.consumer_repo_path = self.test_dir_path / 'actual_consumer_repo'
        
        # --------------------------------------------------------------
        # STEP 2: Initialize and configure the brain repository.
        # --------------------------------------------------------------
        self.brain_repo_path.mkdir()
        run_git_in_path(str(self.brain_repo_path), ['init'], initial_branch_name=self.initial_git_branch_name)
        
        # Create brain configuration file
        brain_file_content = (
            "[BRAIN]\nID = test-brain-base\nDESCRIPTION = Base Test Brain\n\n"
            "[EXPORT]\nlibs/utils/strings.py = readonly\nconfig/settings.json = readwrite\n"
            "single_file.txt = readonly\ndirectory_neuron/ = readonly\n"
        )
        (self.brain_repo_path / '.brain').write_text(brain_file_content)
        
        # ===============
        # Sub step 2.1: Create test files and directories in the brain repository.
        # ===============
        (self.brain_repo_path / 'libs' / 'utils').mkdir(parents=True, exist_ok=True)
        (self.brain_repo_path / 'libs/utils/strings.py').write_text("# Brain strings.py\n")
        (self.brain_repo_path / 'config').mkdir(exist_ok=True)
        (self.brain_repo_path / 'config/settings.json').write_text('{"brain_version": "1.0"}\n')
        (self.brain_repo_path / 'single_file.txt').write_text('Brain single file content\n')
        (self.brain_repo_path / 'directory_neuron').mkdir(exist_ok=True)
        (self.brain_repo_path / 'directory_neuron' / 'file_in_dir.txt').write_text('Content in dir_neuron\n')

        # ===============
        # Sub step 2.2: Commit the brain repository contents.
        # ===============
        run_git_in_path(str(self.brain_repo_path), ['add', '.'])
        run_git_in_path(str(self.brain_repo_path), ['commit', '-m', f'Initial brain setup on branch {self.initial_git_branch_name}'])

        # --------------------------------------------------------------
        # STEP 3: Initialize the consumer repository and set up working directory.
        # --------------------------------------------------------------
        self.consumer_repo_path.mkdir()
        run_git_in_path(str(self.consumer_repo_path), ['init'], initial_branch_name=self.initial_git_branch_name)
        
        # Save original working directory and change to consumer repository
        self.original_cwd = os.getcwd()
        os.chdir(str(self.consumer_repo_path)) 
    
    def tearDown(self):
        """
        Description:
            Cleans up the test environment by restoring the original working directory
            and removing temporary test directories.
        
        Parameters:
            None
    
        Returns:
            None
        """
        os.chdir(self.original_cwd)
        self.test_dir_obj.cleanup()

    def _write_neurons_file_to_consumer(self, content: str):
        """
        Description:
            Helper method to write the specified content to the .neurons file
            in the consumer repository.
        
        Parameters:
            content (str): The content to write to the .neurons file
    
        Returns:
            None
        """
        (self.consumer_repo_path / '.neurons').write_text(content)

    def get_brain_url_for_consumer(self) -> str:
        """
        Description:
            Creates a file:// URL for the brain repository that can be used
            by the consumer repository for git operations.
        
        Parameters:
            None
    
        Returns:
            str: The file URL to the brain repository
        """
        # Use file:// prefix for local git URLs for robustness with git clone
        return f"file://{self.brain_repo_path.resolve().as_posix()}"


class TestBrainInitCommand(unittest.TestCase):
    """Test the brain brain-init command."""
    
    def setUp(self):
        """
        Description:
            Sets up a test environment with a temporary directory for brain initialization tests.
        
        Parameters:
            None
    
        Returns:
            None
        """
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = pathlib.Path(self.test_dir_obj.name)
        self.original_cwd = os.getcwd()
        os.chdir(str(self.test_dir))
    
    def tearDown(self):
        """
        Description:
            Cleans up the test environment by restoring the original working directory
            and removing temporary directories.
        
        Parameters:
            None
    
        Returns:
            None
        """
        os.chdir(self.original_cwd)
        self.test_dir_obj.cleanup()
    
    def test_brain_init_command(self):
        """
        Description:
            Tests that the brain-init command correctly creates a .brain file with
            the specified ID and description.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['--id', 'cmd-test-brain', '--description', 'Cmd Test Desc']
        result = handle_brain_init(args)
        self.assertEqual(result, 0)
        brain_cfg_path = self.test_dir / '.brain'
        self.assertTrue(brain_cfg_path.exists())
        content = brain_cfg_path.read_text()
        self.assertIn('ID = cmd-test-brain', content)
        self.assertIn('DESCRIPTION = Cmd Test Desc', content)
    
    def test_brain_init_with_export(self):
        """
        Description:
            Tests that the brain-init command correctly handles export parameters
            and includes them in the generated .brain file.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['--id', 'export-brain', '--export', 'src/*.py=readonly', '--export', 'conf=readwrite']
        result = handle_brain_init(args)
        self.assertEqual(result, 0)
        content = (self.test_dir / '.brain').read_text()
        self.assertIn('src/*.py = readonly', content)
        self.assertIn('conf = readwrite', content)
    
    def test_brain_init_missing_id_exits(self):
        """
        Description:
            Tests that the brain-init command exits with an error when the required
            ID parameter is missing.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['--description', 'No ID Test']
        with self.assertRaises(SystemExit) as cm:
            handle_brain_init(args)
        self.assertEqual(cm.exception.code, 2)


class TestAddBrainCommand(TestCommandBase):
    def test_add_brain_command(self):
        """
        Description:
            Tests that the add-brain command correctly adds a brain entry to the .neurons
            configuration file with the specified name, URL, and branch.
        
        Parameters:
            None
    
        Returns:
            None
        """
        brain_url = self.get_brain_url_for_consumer()
        args = ['my-local-brain', brain_url, self.initial_git_branch_name]
        result = handle_add_brain(args)
        # If result is 1, print the error message from handle_add_brain (which is captured by test runner)
        self.assertEqual(result, 0, f"handle_add_brain failed with code {result}. Check test output for command's print statements.")
        
        neurons_cfg_path = self.consumer_repo_path / '.neurons'
        self.assertTrue(neurons_cfg_path.exists())
        content = neurons_cfg_path.read_text()
        self.assertIn('[BRAIN:my-local-brain]', content)
        self.assertIn(f'REMOTE = {brain_url}', content)
        self.assertIn(f'BRANCH = {self.initial_git_branch_name}', content)


class TestAddNeuronCommand(TestCommandBase):
    def setUp(self):
        """
        Description:
            Sets up the test environment for add-neuron command tests, extending the base
            setup with a .neurons file containing a reference to the brain repository.
        
        Parameters:
            None
    
        Returns:
            None
        """
        super().setUp()
        brain_url = self.get_brain_url_for_consumer()
        neurons_content = (
            f"[BRAIN:test-brain-base]\nREMOTE = {brain_url}\nBRANCH = {self.initial_git_branch_name}\n\n[MAP]\n"
        )
        self._write_neurons_file_to_consumer(neurons_content)

    def test_add_neuron_file(self):
        """
        Description:
            Tests that the add-neuron command correctly maps and syncs a single file
            from the brain repository to the consumer repository.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = [f'test-brain-base::single_file.txt::local_copy/single.txt']
        result = handle_add_neuron(args)
        self.assertEqual(result, 0, f"handle_add_neuron (file) failed with code {result}")
        content = (self.consumer_repo_path / '.neurons').read_text()
        # Check for the value part which includes the mapping string
        self.assertTrue(any(f'test-brain-base::single_file.txt::local_copy/single.txt' in line for line in content.splitlines()))
        
        neuron_file_path = self.consumer_repo_path / 'local_copy/single.txt'
        self.assertTrue(neuron_file_path.exists())
        self.assertIn('Brain single file content', neuron_file_path.read_text())

    def test_add_neuron_directory(self):
        """
        Description:
            Tests that the add-neuron command correctly maps and syncs a directory
            from the brain repository to the consumer repository.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = [f'test-brain-base::directory_neuron/::local_dir_neuron/']
        result = handle_add_neuron(args)
        self.assertEqual(result, 0, f"handle_add_neuron (directory) failed with code {result}")
        self.assertTrue((self.consumer_repo_path / 'local_dir_neuron' / 'file_in_dir.txt').exists())


class TestRemoveNeuronCommand(TestCommandBase):
    def setUp(self):
        """
        Description:
            Sets up the test environment for remove-neuron command tests with a
            pre-configured .neurons file and test files in the consumer repository.
        
        Parameters:
            None
    
        Returns:
            None
        """
        super().setUp()
        brain_url = self.get_brain_url_for_consumer()
        neurons_content = (
            f"[BRAIN:test-brain-base]\nREMOTE = {brain_url}\nBRANCH = {self.initial_git_branch_name}\n\n"
            "[MAP]\n"
            "map_single = test-brain-base::single_file.txt::consumer_single.txt\n"
            "map_utils = test-brain-base::libs/utils/strings.py::consumer_strings.py\n"
        )
        self._write_neurons_file_to_consumer(neurons_content)
        # Ensure files exist to be removed/kept
        (self.consumer_repo_path / 'consumer_single.txt').write_text("content to remove")
        (self.consumer_repo_path / 'consumer_strings.py').write_text("content to keep")


    def test_remove_neuron(self):
        """
        Description:
            Tests that the remove-neuron command correctly removes a mapping from
            the .neurons file without deleting the actual file.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['consumer_single.txt'] 
        result = handle_remove_neuron(args)
        self.assertEqual(result, 0)
        content = (self.consumer_repo_path / '.neurons').read_text()
        self.assertNotIn('consumer_single.txt', content) 
        self.assertIn('consumer_strings.py', content)
        self.assertTrue((self.consumer_repo_path / 'consumer_single.txt').exists())

    def test_remove_neuron_with_delete(self):
        """
        Description:
            Tests that the remove-neuron command correctly removes a mapping from
            the .neurons file and deletes the corresponding file when the --delete
            flag is provided.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['consumer_single.txt', '--delete']
        result = handle_remove_neuron(args)
        self.assertEqual(result, 0)
        self.assertFalse((self.consumer_repo_path / 'consumer_single.txt').exists())


class TestSyncCommand(TestCommandBase):
    def setUp(self):
        """
        Description:
            Sets up the test environment for sync command tests with a pre-configured
            .neurons file containing multiple neuron mappings and a sync policy.
        
        Parameters:
            None
    
        Returns:
            None
        """
        super().setUp()
        brain_url = self.get_brain_url_for_consumer()
        neurons_content = (
            f"[BRAIN:test-brain-base]\nREMOTE = {brain_url}\nBRANCH = {self.initial_git_branch_name}\n\n"
            f"[SYNC_POLICY]\nCONFLICT_STRATEGY = prefer_brain\n\n" 
            "[MAP]\nmap_str = test-brain-base::libs/utils/strings.py::synced_code/strings.py\n"
            "map_cfg = test-brain-base::config/settings.json::synced_code/settings.json\n"
        )
        self._write_neurons_file_to_consumer(neurons_content)

    def test_sync_all(self):
        """
        Description:
            Tests that the sync command correctly synchronizes all mapped neurons
            when no specific neuron is specified.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = [] 
        result = handle_sync(args)
        self.assertEqual(result, 0, f"handle_sync (all) failed with code {result}")
        self.assertTrue((self.consumer_repo_path / 'synced_code/strings.py').exists())
        self.assertTrue((self.consumer_repo_path / 'synced_code/settings.json').exists())

    def test_sync_specific_neuron(self):
        """
        Description:
            Tests that the sync command correctly synchronizes only the specified
            neuron when a specific neuron path is provided.
        
        Parameters:
            None
    
        Returns:
            None
        """
        args = ['synced_code/strings.py']
        result = handle_sync(args)
        self.assertEqual(result, 0, f"handle_sync (specific) failed with code {result}")
        self.assertTrue((self.consumer_repo_path / 'synced_code/strings.py').exists())
        # Ensure the other mapped neuron was NOT synced
        self.assertFalse((self.consumer_repo_path / 'synced_code/settings.json').exists())


@mock.patch('brain.commands.pull.sync_all_neurons') 
@mock.patch('subprocess.run') 
class TestPullCommand(TestCommandBase):
    def test_pull_calls_git_pull_and_sync(self, mock_subprocess_run, mock_sync_all_neurons_in_pull):
        """
        Description:
            Tests that the pull command correctly calls 'git pull' and synchronizes
            all neurons afterwards when AUTO_SYNC_ON_PULL is enabled.
        
        Parameters:
            mock_subprocess_run (mock.Mock): Mock object for subprocess.run
            mock_sync_all_neurons_in_pull (mock.Mock): Mock object for sync_all_neurons
    
        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up mocks and test environment.
        # --------------------------------------------------------------
        mock_subprocess_run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        mock_sync_all_neurons_in_pull.return_value = [{'status': 'success'}]

        brain_url = self.get_brain_url_for_consumer()
        neurons_content = (
            f"[BRAIN:test-brain-base]\nREMOTE = {brain_url}\nBRANCH = {self.initial_git_branch_name}\n\n"
            f"[SYNC_POLICY]\nAUTO_SYNC_ON_PULL = true\n\n[MAP]\n"
            "m = test-brain-base::single_file.txt::s.txt\n"
        )
        self._write_neurons_file_to_consumer(neurons_content)

        # --------------------------------------------------------------
        # STEP 2: Call the pull command and verify results.
        # --------------------------------------------------------------
        result = handle_pull([])
        self.assertEqual(result, 0)
        
        # Check if git pull was called
        git_pull_called = any(call.args[0][:2] == ['git', 'pull'] for call in mock_subprocess_run.call_args_list)
        self.assertTrue(git_pull_called, "'git pull' was not called")
        
        # Check if sync was called
        mock_sync_all_neurons_in_pull.assert_called_once()

@mock.patch('brain.commands.clone.sync_all_neurons') # Mock sync
@mock.patch('subprocess.run') # Mock git calls
class TestCloneCommand(unittest.TestCase):
    def setUp(self):
        """
        Description:
            Sets up a test environment for clone command tests with a source
            repository containing a .neurons configuration.
        
        Parameters:
            None
    
        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Create test directory and set up environment.
        # --------------------------------------------------------------
        self.test_dir_obj = tempfile.TemporaryDirectory()
        self.test_dir = pathlib.Path(self.test_dir_obj.name)
        self.original_cwd = os.getcwd()
        os.chdir(str(self.test_dir))

        self.initial_git_branch_name = "main" # For this standalone test setup

        # --------------------------------------------------------------
        # STEP 2: Create and initialize a source repository to clone from.
        # --------------------------------------------------------------
        self.source_repo_to_clone = self.test_dir / 'source_for_clone'
        self.source_repo_to_clone.mkdir()
        run_git_in_path(str(self.source_repo_to_clone), ['init'], initial_branch_name=self.initial_git_branch_name)
        (self.source_repo_to_clone / '.neurons').write_text( 
            "[BRAIN:dummy]\nREMOTE=dummy_url\n\n[MAP]\nd=dummy::s::d\n"
        )
        (self.source_repo_to_clone / 'a_file.txt').write_text("content") # Add a file to commit
        run_git_in_path(str(self.source_repo_to_clone), ['add', '.'])
        run_git_in_path(str(self.source_repo_to_clone), ['commit', '-m', f'init clone source on {self.initial_git_branch_name}'])


    def tearDown(self):
        """
        Description:
            Cleans up the test environment by restoring the original working directory
            and removing temporary directories.
        
        Parameters:
            None
    
        Returns:
            None
        """
        os.chdir(self.original_cwd)
        self.test_dir_obj.cleanup()

    def test_clone_with_neurons_triggers_sync(self, mock_subprocess_run, mock_sync_all_neurons_in_clone):
        """
        Description:
            Tests that the clone command correctly clones a repository and
            triggers neuron synchronization when a .neurons file exists.
        
        Parameters:
            mock_subprocess_run (mock.Mock): Mock object for subprocess.run
            mock_sync_all_neurons_in_clone (mock.Mock): Mock object for sync_all_neurons
    
        Returns:
            None
        """
        # --------------------------------------------------------------
        # STEP 1: Set up test parameters and mocks.
        # --------------------------------------------------------------
        cloned_dir_name = 'cloned_project'
        source_repo_url = f"file://{self.source_repo_to_clone.resolve().as_posix()}"


        def mock_git_clone_effect(cmd_args, **kwargs):
            """
            Description:
                Simulates git clone behavior by creating the target directory and
                copying the .neurons file from the source repository.
            
            Parameters:
                cmd_args (list): Command arguments
                **kwargs: Additional keyword arguments
            
            Returns:
                mock.Mock: Mock result of the command execution
            """
            if cmd_args[:2] == ['git', 'clone']:
                clone_target_dir_name = cmd_args[-1] 
                clone_target_dir = pathlib.Path(kwargs.get('cwd', os.getcwd())) / clone_target_dir_name
                clone_target_dir.mkdir(parents=True, exist_ok=True)
                
                # Simulate .neurons file being present in the cloned repo
                (clone_target_dir / '.neurons').write_text(
                    (self.source_repo_to_clone / '.neurons').read_text()
                )
                return mock.Mock(returncode=0, stdout="Cloned.", stderr="")
            return mock.Mock(returncode=1, stderr="Unhandled mock subprocess call")

        mock_subprocess_run.side_effect = mock_git_clone_effect
        mock_sync_all_neurons_in_clone.return_value = [] 

        # --------------------------------------------------------------
        # STEP 2: Execute the clone command and verify results.
        # --------------------------------------------------------------
        result = handle_clone([source_repo_url, cloned_dir_name])
        self.assertEqual(result, 0)
        
        # Check if git clone was called with correct arguments
        found_clone_call = any(
            call.args[0][:2] == ['git', 'clone'] and
            source_repo_url in call.args[0] and
            cloned_dir_name in call.args[0]
            for call in mock_subprocess_run.call_args_list
        )
        self.assertTrue(found_clone_call)
        mock_sync_all_neurons_in_clone.assert_called_once()


if __name__ == '__main__':
    unittest.main()