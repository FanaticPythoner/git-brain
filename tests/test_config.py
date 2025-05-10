"""
Tests for the configuration handling module.

These tests verify that the configuration parser correctly handles
.brain and .neurons files.
"""

import os
import tempfile
import unittest

from brain.config import (
    BrainConfigError, 
    NeuronsConfigError,
    load_brain_config, 
    load_neurons_config,
    save_brain_config,
    save_neurons_config
)


class TestBrainConfig(unittest.TestCase):
    """Test loading and parsing .brain configuration files."""
    
    def test_load_valid_brain_config(self):
        """
        Description:
            Tests loading a valid .brain configuration file with all possible sections.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration matches expected values
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .brain file with test content.
        # --------------------------------------------------------------
        content = (
            "[BRAIN]\n"
            "ID = test-brain\n" 
            "DESCRIPTION = Test brain repository\n\n"
            "[EXPORT]\n"
            "libs/**/*.py = readonly\n"
            "config/*.json = readwrite\n\n"
            "[ACCESS]\n"
            "user1 = libs/**/*.py, config/*.json\n" 
            "group_all = *\n\n"
            "[UPDATE_POLICY]\n"
            "REQUIRE_REVIEW = true\n"
            "PROTECTED_PATHS = libs/core/*,other/path\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".brain", encoding='utf-8') as f:
            f.write(content)
            brain_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Load the configuration and verify its contents.
            # --------------------------------------------------------------
            config = load_brain_config(brain_file)
            
            # ===============
            # Sub step 2.1: Verify basic brain properties.
            # ===============
            self.assertEqual(config['ID'], 'test-brain')
            self.assertEqual(config['DESCRIPTION'], 'Test brain repository')
            
            # ===============
            # Sub step 2.2: Verify EXPORT section.
            # ===============
            self.assertIn('EXPORT', config)
            self.assertEqual(config['EXPORT']['libs/**/*.py'], 'readonly')
            self.assertEqual(config['EXPORT']['config/*.json'], 'readwrite')
            
            # ===============
            # Sub step 2.3: Verify ACCESS section.
            # ===============
            self.assertIn('ACCESS', config)
            self.assertEqual(config['ACCESS']['user1'], ['libs/**/*.py', 'config/*.json'])
            self.assertEqual(config['ACCESS']['group_all'], ['*'])
            
            # ===============
            # Sub step 2.4: Verify UPDATE_POLICY section.
            # ===============
            self.assertIn('UPDATE_POLICY', config)
            self.assertEqual(config['UPDATE_POLICY']['REQUIRE_REVIEW'], True)
            self.assertEqual(config['UPDATE_POLICY']['PROTECTED_PATHS'], ['libs/core/*', 'other/path'])
        finally:
            # Clean up the temporary file.
            os.unlink(brain_file)
    
    def test_load_minimal_brain_config(self):
        """
        Description:
            Tests loading a minimal valid .brain file with only the required fields.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration has minimal required fields
                  and does not contain optional sections
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .brain file with minimal content.
        # --------------------------------------------------------------
        content = (
            "[BRAIN]\n"
            "ID = minimal-brain\n\n"
            "[EXPORT]\n" 
            "libs/* = readonly\n" 
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".brain", encoding='utf-8') as f:
            f.write(content)
            brain_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Load the configuration and verify its contents.
            # --------------------------------------------------------------
            config = load_brain_config(brain_file)
            
            # ===============
            # Sub step 2.1: Verify required fields are present.
            # ===============
            self.assertEqual(config['ID'], 'minimal-brain')
            self.assertIn('EXPORT', config)
            self.assertEqual(config['EXPORT']['libs/*'], 'readonly')
            
            # ===============
            # Sub step 2.2: Verify optional fields are not present.
            # ===============
            self.assertNotIn('DESCRIPTION', config) 
            self.assertNotIn('ACCESS', config)
            self.assertNotIn('UPDATE_POLICY', config)
        finally:
            # Clean up the temporary file.
            os.unlink(brain_file)
    
    def test_missing_required_id_field(self):
        """
        Description:
            Tests that loading a .brain file without a required ID field raises the
            appropriate error.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that a BrainConfigError is raised with appropriate message
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .brain file without ID field.
        # --------------------------------------------------------------
        content = (
            "[BRAIN]\n"
            "DESCRIPTION = Test brain repository\n\n"
            "[EXPORT]\n"
            "libs/* = readonly\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".brain", encoding='utf-8') as f:
            f.write(content)
            brain_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Attempt to load the config and verify the error.
            # --------------------------------------------------------------
            with self.assertRaises(BrainConfigError) as cm:
                load_brain_config(brain_file)
            # Verify the error message mentions the missing ID field.
            self.assertIn("Missing required ID field", str(cm.exception))
        finally:
            # Clean up the temporary file.
            os.unlink(brain_file)

    def test_missing_export_section(self):
        """
        Description:
            Tests that loading a .brain file without the required EXPORT section
            raises the appropriate error.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that a BrainConfigError is raised with appropriate message
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .brain file without EXPORT section.
        # --------------------------------------------------------------
        content = (
            "[BRAIN]\n"
            "ID = test-brain\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".brain", encoding='utf-8') as f:
            f.write(content)
            brain_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Attempt to load the config and verify the error.
            # --------------------------------------------------------------
            with self.assertRaises(BrainConfigError) as cm:
                load_brain_config(brain_file)
            # Check the actual error message more reliably.
            self.assertTrue("Missing required [EXPORT] section" in str(cm.exception))
        finally:
            # Clean up the temporary file.
            os.unlink(brain_file)

    def test_save_brain_config(self):
        """
        Description:
            Tests that saving a brain configuration to a file and then loading it back
            preserves all configuration values correctly.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration matches the original one
        """
        # --------------------------------------------------------------
        # STEP 1: Create a test configuration dictionary.
        # --------------------------------------------------------------
        config_to_save = {
            'ID': 'test-brain-save', 'DESCRIPTION': 'Test Save Brain Repo',
            'EXPORT': {'src/**/*.js': 'readonly', 'assets/data.json': 'readwrite'},
            'ACCESS': {'group1': ['src/**/*.js', 'assets/*'], 'admin': ['*']},
            'UPDATE_POLICY': {'AUTO_APPROVE': False, 'NOTIFY_LIST': 'dev@example.com,qa@example.com'}
        }
        
        # --------------------------------------------------------------
        # STEP 2: Create a temporary file and save/load the configuration.
        # --------------------------------------------------------------
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".brain", encoding='utf-8') as f:
            brain_file_path = f.name
        
        try:
            # ===============
            # Sub step 2.1: Save the configuration to the file.
            # ===============
            save_brain_config(config_to_save, brain_file_path)
            
            # ===============
            # Sub step 2.2: Load the configuration back from the file.
            # ===============
            loaded_config = load_brain_config(brain_file_path)
            
            # --------------------------------------------------------------
            # STEP 3: Verify that loaded configuration matches the original.
            # --------------------------------------------------------------
            self.assertEqual(loaded_config['ID'], config_to_save['ID'])
            self.assertEqual(loaded_config['DESCRIPTION'], config_to_save['DESCRIPTION'])
            self.assertEqual(loaded_config['EXPORT'], config_to_save['EXPORT'])
            self.assertEqual(loaded_config['ACCESS'], config_to_save['ACCESS'])
            self.assertEqual(loaded_config['UPDATE_POLICY']['AUTO_APPROVE'], False)
            self.assertEqual(loaded_config['UPDATE_POLICY']['NOTIFY_LIST'], 'dev@example.com,qa@example.com')
        finally:
            # Clean up the temporary file.
            os.unlink(brain_file_path)


class TestNeuronsConfig(unittest.TestCase):
    """Test loading and parsing .neurons configuration files."""
    
    def test_load_valid_neurons_config(self):
        """
        Description:
            Tests loading a valid .neurons configuration file with all possible sections.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration matches expected values
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .neurons file with test content.
        # --------------------------------------------------------------
        content = (
            "[BRAIN:core-lib]\n"
            "REMOTE = git@github.com:org/core-lib.git\nBRANCH = main\n\n"
            "[BRAIN:analytics]\n"
            "REMOTE = git@github.com:org/analytics.git\nBRANCH = stable\n\n"
            "[SYNC_POLICY]\n"
            "AUTO_SYNC_ON_PULL = true\nCONFLICT_STRATEGY = prompt\n"
            "ALLOW_LOCAL_MODIFICATIONS = false\nALLOW_PUSH_TO_BRAIN = false\n\n"
            "[MAP]\n"
            "map_str = core-lib::libs/utils/strings.py::src/utils/strings.py\n"
            "map_cfg = core-lib::libs/config/::config/\n"
            "map_model = analytics::models/linear.py::src/models/linear.py\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".neurons", encoding='utf-8') as f:
            f.write(content)
            neurons_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Load the configuration and verify its contents.
            # --------------------------------------------------------------
            config = load_neurons_config(neurons_file)
            
            # ===============
            # Sub step 2.1: Verify BRAINS section entries.
            # ===============
            self.assertIn('core-lib', config['BRAINS'])
            self.assertEqual(config['BRAINS']['core-lib']['REMOTE'], 'git@github.com:org/core-lib.git')
            
            # ===============
            # Sub step 2.2: Verify SYNC_POLICY settings.
            # ===============
            self.assertEqual(config['SYNC_POLICY']['AUTO_SYNC_ON_PULL'], True)
            
            # ===============
            # Sub step 2.3: Verify MAP entries.
            # ===============
            self.assertEqual(len(config['MAP']), 3)
            map_values = [(m['brain_id'], m['source'], m['destination']) for m in config['MAP']]
            self.assertIn(('core-lib', 'libs/utils/strings.py', 'src/utils/strings.py'), map_values)
        finally:
            # Clean up the temporary file.
            os.unlink(neurons_file)
    
    def test_load_minimal_neurons_config(self):
        """
        Description:
            Tests loading a minimal valid .neurons file with only the required fields.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration has minimal required fields
                  and default values for optional settings
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .neurons file with minimal content.
        # --------------------------------------------------------------
        content = (
            "[BRAIN:minimal]\n"
            "REMOTE = git@github.com:org/minimal.git\n\n"
            "[MAP]\n"
            "map0 = minimal::lib/utils.py::src/utils.py\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".neurons", encoding='utf-8') as f:
            f.write(content)
            neurons_file = f.name
        
        try:
            # --------------------------------------------------------------
            # STEP 2: Load the configuration and verify its contents.
            # --------------------------------------------------------------
            config = load_neurons_config(neurons_file)
            
            # ===============
            # Sub step 2.1: Verify required fields are present.
            # ===============
            self.assertEqual(config['BRAINS']['minimal']['REMOTE'], 'git@github.com:org/minimal.git')
            self.assertEqual(config['MAP'][0]['source'], 'lib/utils.py')
            
            # ===============
            # Sub step 2.2: Verify default values for optional settings.
            # ===============
            # Default value for AUTO_SYNC_ON_PULL should be True.
            self.assertEqual(config['SYNC_POLICY']['AUTO_SYNC_ON_PULL'], True) 
        finally:
            # Clean up the temporary file.
            os.unlink(neurons_file)

    def test_missing_map_section_error(self):
        """
        Description:
            Tests that loading a .neurons file without the required MAP section
            raises the appropriate error.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that a NeuronsConfigError is raised with appropriate message
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .neurons file without MAP section.
        # --------------------------------------------------------------
        content = "[BRAIN:core-lib]\nREMOTE = git@example.com/repo.git\n"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".neurons", encoding='utf-8') as f:
            f.write(content); neurons_file = f.name
        try:
            # --------------------------------------------------------------
            # STEP 2: Attempt to load the config and verify the error.
            # --------------------------------------------------------------
            with self.assertRaises(NeuronsConfigError) as cm:
                load_neurons_config(neurons_file)
            # Verify the error message mentions the missing MAP section.
            self.assertIn("Missing required [MAP] section", str(cm.exception))
        finally: 
            # Clean up the temporary file.
            os.unlink(neurons_file)

    def test_empty_map_section_allowed(self):
        """
        Description:
            Tests that loading a .neurons file with an empty MAP section is allowed.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the configuration loads successfully with an empty MAP
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .neurons file with empty MAP section.
        # --------------------------------------------------------------
        content = "[BRAIN:core-lib]\nREMOTE = r\n\n[MAP]\n" 
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".neurons", encoding='utf-8') as f:
            f.write(content); neurons_file = f.name
        try:
            # --------------------------------------------------------------
            # STEP 2: Load the configuration and verify empty MAP.
            # --------------------------------------------------------------
            config = load_neurons_config(neurons_file)
            # Verify that the MAP section is empty but exists.
            self.assertEqual(len(config['MAP']), 0)
        finally:
            # Clean up the temporary file.
            os.unlink(neurons_file)

    def test_unknown_brain_in_map(self):
        """
        Description:
            Tests that loading a .neurons file with a MAP entry referencing an
            undefined brain raises the appropriate error.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that a NeuronsConfigError is raised with appropriate message
        """
        # --------------------------------------------------------------
        # STEP 1: Create a temporary .neurons file with unknown brain in MAP.
        # --------------------------------------------------------------
        content = (
            "[BRAIN:core-lib]\nREMOTE = git@example.com/core.git\n\n"
            "[MAP]\n"
            "map_unknown = unknown_brain::path/src::path/dst\n"
        )
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".neurons", encoding='utf-8') as f:
            f.write(content); neurons_file = f.name
        try:
            # --------------------------------------------------------------
            # STEP 2: Attempt to load the config and verify the error.
            # --------------------------------------------------------------
            with self.assertRaisesRegex(NeuronsConfigError, "Unknown brain 'unknown_brain'"):
                load_neurons_config(neurons_file)
        finally:
            # Clean up the temporary file.
            os.unlink(neurons_file)

    def test_save_neurons_config(self):
        """
        Description:
            Tests that saving a neurons configuration to a file and then loading it back
            preserves all configuration values correctly.
        
        Parameters:
            None
            
        Returns:
            None: Asserts that the loaded configuration matches the original one
        """
        # --------------------------------------------------------------
        # STEP 1: Create a test configuration dictionary.
        # --------------------------------------------------------------
        config_to_save = {
            'BRAINS': {'core': {'REMOTE': 'url', 'BRANCH': 'dev'}},
            'SYNC_POLICY': {'AUTO_SYNC_ON_PULL': False, 'CONFLICT_STRATEGY': 'prefer_brain'},
            'MAP': [{'brain_id': 'core', 'source': 's', 'destination': 'd', '_map_key': 'customKey'}]
        }
        
        # --------------------------------------------------------------
        # STEP 2: Create a temporary file and save/load the configuration.
        # --------------------------------------------------------------
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".neurons", encoding='utf-8') as f:
            neurons_file_path = f.name
        try:
            # ===============
            # Sub step 2.1: Save the configuration to the file.
            # ===============
            save_neurons_config(config_to_save, neurons_file_path)
            
            # ===============
            # Sub step 2.2: Load the configuration back from the file.
            # ===============
            loaded_config = load_neurons_config(neurons_file_path)
            
            # --------------------------------------------------------------
            # STEP 3: Verify that loaded configuration matches the original.
            # --------------------------------------------------------------
            self.assertEqual(loaded_config['BRAINS']['core']['BRANCH'], 'dev')
            self.assertEqual(loaded_config['SYNC_POLICY']['AUTO_SYNC_ON_PULL'], False)
            self.assertEqual(loaded_config['MAP'][0]['_map_key'], 'customKey')
            self.assertEqual(loaded_config['MAP'][0]['source'], 's')
        finally:
            # Clean up the temporary file.
            os.unlink(neurons_file_path)

if __name__ == '__main__':
    unittest.main()