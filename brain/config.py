"""
Configuration handling for Brain.

This module provides functions for loading and parsing the
.brain and .neurons configuration files.
"""

import os
import configparser
from typing import Dict, Any, Optional


class BrainConfigError(Exception):
    """
    Description:
        Exception raised for errors in brain configuration.
        
    Parameters:
        message (str): Error message describing the configuration issue.
    """
    pass


class NeuronsConfigError(Exception):
    """
    Description:
        Exception raised for errors in neurons configuration.
        
    Parameters:
        message (str): Error message describing the configuration issue.
    """
    pass


def load_brain_config(file_path: str = '.brain') -> Dict[str, Any]:
    """
    Description:
        Load and parse a .brain configuration file.
    
    Parameters:
        file_path (str): Path to the .brain file (default: '.brain')
    
    Returns:
        config (Dict[str, Any]): Parsed brain configuration containing ID, DESCRIPTION,
                                 EXPORT paths with permissions, ACCESS settings, and
                                 UPDATE_POLICY configurations.
    
    Raises:
        BrainConfigError: If the configuration file is not found or has invalid format
    """
    # --------------------------------------------------------------
    # STEP 1: Verify file existence.
    # --------------------------------------------------------------
    if not os.path.exists(file_path):
        raise BrainConfigError(f"Brain configuration file not found: {file_path}")
    
    # --------------------------------------------------------------
    # STEP 2: Initialize configuration and parser.
    # --------------------------------------------------------------
    config: Dict[str, Any] = {} # Initialize config dict
    parser = configparser.ConfigParser(strict=True, allow_no_value=True)
    parser.optionxform = str  # Preserve case sensitivity in keys

    try:
        # --------------------------------------------------------------
        # STEP 3: Read and parse the configuration file.
        # --------------------------------------------------------------
        parser.read(file_path)
        
        # --------------------------------------------------------------
        # STEP 4: Validate and extract the BRAIN section.
        # --------------------------------------------------------------
        if 'BRAIN' not in parser:
            raise BrainConfigError("Missing required [BRAIN] section")
        
        brain_section = parser['BRAIN']
        
        if 'ID' not in brain_section:
            raise BrainConfigError("Missing required ID field in [BRAIN] section")
        
        config['ID'] = brain_section['ID']
        
        # Extract optional DESCRIPTION if present
        if 'DESCRIPTION' in brain_section:
            config['DESCRIPTION'] = brain_section['DESCRIPTION']
        
        # --------------------------------------------------------------
        # STEP 5: Validate and extract the EXPORT section.
        # --------------------------------------------------------------
        if 'EXPORT' not in parser:
            raise BrainConfigError("Missing required [EXPORT] section")
        
        config['EXPORT'] = {}
        for path_pattern, permission_str in parser['EXPORT'].items():
            # Clean up path pattern
            path_pattern = path_pattern.strip()
            
            # Handle empty permission (defaults to readonly)
            if permission_str is None: 
                permission_str = "readonly" 
            else:
                permission_str = permission_str.strip()

            # Skip empty path patterns
            if not path_pattern:
                # This case should ideally not happen with a valid INI structure
                # but can be a safeguard. Consider logging a warning if it occurs.
                continue 
            
            # Validate permission values
            if permission_str not in ['readonly', 'readwrite']:
                raise BrainConfigError(f"Invalid permission '{permission_str}' for path '{path_pattern}'")
            
            # Store path with its permission
            config['EXPORT'][path_pattern] = permission_str
        
        # --------------------------------------------------------------
        # STEP 6: Extract optional ACCESS section if present.
        # --------------------------------------------------------------
        if 'ACCESS' in parser:
            config['ACCESS'] = {}
            for entity, paths_str in parser['ACCESS'].items():
                entity = entity.strip() # Ensure entity key is stripped
                
                # Handle empty paths list
                if paths_str is None: 
                    path_list = []
                else:
                    # Create list from comma-separated paths
                    path_list = [p.strip() for p in paths_str.split(',') if p.strip()]
                
                config['ACCESS'][entity] = path_list
        
        # --------------------------------------------------------------
        # STEP 7: Extract optional UPDATE_POLICY section if present.
        # --------------------------------------------------------------
        if 'UPDATE_POLICY' in parser:
            config['UPDATE_POLICY'] = {}
            for key, value_str in parser['UPDATE_POLICY'].items():
                # Handle empty values for policies
                if value_str is None: 
                    # Determine default or raise error for empty UPDATE_POLICY values
                    # For now, let's assume boolean policies default to False if explicitly empty.
                    # Or, one could raise an error: raise BrainConfigError(f"Empty value for '{key}' in [UPDATE_POLICY]")
                    # This behavior needs to be clearly defined. For now, assign a default or skip.
                    # Example: config['UPDATE_POLICY'][key] = False 
                    continue # Or, if strict, raise error.

                # Process based on value type
                value_str_lower = value_str.lower().strip() # Strip value before comparison
                
                # ===============
                # Sub step 7.1: Handle boolean values.
                # ===============
                if value_str_lower in ['true', 'yes', '1']:
                    config['UPDATE_POLICY'][key] = True
                elif value_str_lower in ['false', 'no', '0']:
                    config['UPDATE_POLICY'][key] = False
                
                # ===============
                # Sub step 7.2: Handle PROTECTED_PATHS specially.
                # ===============
                # Check for specific keys that expect list values, like PROTECTED_PATHS
                # This check must be case-sensitive as parser.optionxform = str
                elif key == 'PROTECTED_PATHS': 
                    config['UPDATE_POLICY'][key] = [p.strip() for p in value_str.split(',') if p.strip()]
                
                # ===============
                # Sub step 7.3: Handle all other values as strings.
                # ===============
                else:
                    config['UPDATE_POLICY'][key] = value_str.strip() # Store other values as stripped strings
    
    except (configparser.Error, ValueError) as e: # ValueError for things like int conversion if attempted
        raise BrainConfigError(f"Error parsing brain configuration: {str(e)}")
    
    return config


def save_brain_config(config: Dict[str, Any], file_path: str = '.brain') -> None:
    """
    Description:
        Save a brain configuration dictionary to a file in INI format.
    
    Parameters:
        config (Dict[str, Any]): Brain configuration dictionary containing well-typed values
                              (e.g., booleans as Python bool, lists as Python list)
        file_path (str): Path to save the .brain file (default: '.brain')
    
    Returns:
        None
    
    Raises:
        BrainConfigError: If the configuration cannot be saved due to IO errors
    """
    # --------------------------------------------------------------
    # STEP 1: Initialize configuration parser.
    # --------------------------------------------------------------
    parser = configparser.ConfigParser()
    parser.optionxform = str  # Preserve case sensitivity

    # --------------------------------------------------------------
    # STEP 2: Build BRAIN section.
    # --------------------------------------------------------------
    parser['BRAIN'] = {}
    # Ensure ID is present, even if empty string, as it's schema-required (though load checks non-empty)
    parser['BRAIN']['ID'] = config.get('ID', '') 
    
    # Only write DESCRIPTION if it's present in the config dict
    if 'DESCRIPTION' in config: # More explicit than config.get('DESCRIPTION') which might be None
        parser['BRAIN']['DESCRIPTION'] = config['DESCRIPTION']
    
    # --------------------------------------------------------------
    # STEP 3: Build EXPORT section.
    # --------------------------------------------------------------
    parser['EXPORT'] = {} 
    for path, permission in config.get('EXPORT', {}).items():
        parser['EXPORT'][path] = str(permission) # Permissions are 'readonly' or 'readwrite' (strings)
    
    # --------------------------------------------------------------
    # STEP 4: Build ACCESS section if present.
    # --------------------------------------------------------------
    # Only write ACCESS section if it has content in the config
    if config.get('ACCESS'): 
        parser['ACCESS'] = {}
        for entity, paths_data in config['ACCESS'].items():
            # If it's not, ','.join will raise a TypeError.
            try:
                parser['ACCESS'][entity] = ','.join(paths_data)
            except TypeError: # Catches if paths_data is not an iterable of strings
                 # This indicates a malformed config input dict for 'ACCESS' paths.
                 # Production code might log this or raise a more specific internal error.
                 # For now, convert to string to avoid crashing save, but this path indicates bad input.
                parser['ACCESS'][entity] = str(paths_data)
    
    # --------------------------------------------------------------
    # STEP 5: Build UPDATE_POLICY section if present.
    # --------------------------------------------------------------
    if config.get('UPDATE_POLICY'):
        parser['UPDATE_POLICY'] = {}
        for key, value in config['UPDATE_POLICY'].items():
            
            # ===============
            # Sub step 5.1: Handle boolean values.
            # ===============
            if type(value) is bool:
                parser['UPDATE_POLICY'][key] = str(value).lower()
            
            # ===============
            # Sub step 5.2: Handle list values (like PROTECTED_PATHS).
            # ===============
            elif type(value) is list: # Check for list type specifically for join
                try:
                    parser['UPDATE_POLICY'][key] = ','.join(value)
                except TypeError: # If list contains non-strings
                    parser['UPDATE_POLICY'][key] = str(value) # Fallback, indicates bad input
            
            # ===============
            # Sub step 5.3: Handle all other values.
            # ===============
            else:
                parser['UPDATE_POLICY'][key] = str(value)
    
    # --------------------------------------------------------------
    # STEP 6: Write configuration to file.
    # --------------------------------------------------------------
    try:
        with open(file_path, 'w', encoding='utf-8') as f: # Ensure utf-8 encoding
            parser.write(f)
    except (IOError, OSError) as e:
        raise BrainConfigError(f"Error saving brain configuration: {str(e)}")


def load_neurons_config(file_path: str = '.neurons') -> Dict[str, Any]:
    """
    Description:
        Load and parse a .neurons configuration file, which defines brain connections
        and mapping relationships.
    
    Parameters:
        file_path (str): Path to the .neurons file (default: '.neurons')
    
    Returns:
        config (Dict[str, Any]): Parsed neurons configuration containing BRAINS connections,
                                 SYNC_POLICY settings, and MAP relationships.
    
    Raises:
        NeuronsConfigError: If the configuration file is not found or has invalid format
    """
    # --------------------------------------------------------------
    # STEP 1: Verify file existence.
    # --------------------------------------------------------------
    if not os.path.exists(file_path):
        raise NeuronsConfigError(f"Neurons configuration file not found: {file_path}")
    
    # --------------------------------------------------------------
    # STEP 2: Initialize configuration with defaults.
    # --------------------------------------------------------------
    config: Dict[str, Any] = { 
        'BRAINS': {},
        'SYNC_POLICY': { # Define all default sync policies explicitly
            'AUTO_SYNC_ON_PULL': True,
            'CONFLICT_STRATEGY': 'prompt',
            'ALLOW_LOCAL_MODIFICATIONS': False,
            'ALLOW_PUSH_TO_BRAIN': False,
            'AUTO_SYNC_ON_CHECKOUT': False # Adding this based on checkout.py usage
        },
        'MAP': []
    }
    
    # Initialize parser with strict mode enabled
    parser = configparser.ConfigParser(strict=True, allow_no_value=True)
    parser.optionxform = str  # Preserve case sensitivity in keys

    try:
        # --------------------------------------------------------------
        # STEP 3: Read and parse the configuration file.
        # --------------------------------------------------------------
        # Ensure reading with UTF-8, as it's saved with UTF-8
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        parser.read_string(content)
        
        # --------------------------------------------------------------
        # STEP 4: Process BRAIN sections.
        # --------------------------------------------------------------
        for section_name in parser.sections():
            if section_name.startswith('BRAIN:'):
                # Extract brain ID from section name
                brain_id = section_name[len('BRAIN:'):].strip()
                if not brain_id:
                    raise NeuronsConfigError(f"Empty brain ID in section name: '{section_name}'")

                section_data = parser[section_name]
                
                # Validate required REMOTE field
                remote_val = section_data.get('REMOTE')
                if not remote_val: # Also checks for empty string
                    raise NeuronsConfigError(f"Missing or empty REMOTE field in [{section_name}] section")
                
                # Create brain entry with required REMOTE value
                config['BRAINS'][brain_id] = {'REMOTE': remote_val.strip()} # Strip remote_val
                
                # Add optional BRANCH if present
                branch_val = section_data.get('BRANCH')
                if branch_val: 
                    config['BRAINS'][brain_id]['BRANCH'] = branch_val.strip() # Strip branch_val
                
                # Add optional ARGS if present
                args_val = section_data.get('ARGS') # Git arguments for brain operations
                if args_val:
                    config['BRAINS'][brain_id]['ARGS'] = args_val.strip()
        
        # --------------------------------------------------------------
        # STEP 5: Process SYNC_POLICY section if present.
        # --------------------------------------------------------------
        if 'SYNC_POLICY' in parser:
            for key, value_str in parser['SYNC_POLICY'].items():
                policy_key_upper = key.upper() # Standardize internal keys
                
                # Handle empty values
                if value_str is None: # Handle key= (empty value)
                    # If key is a known boolean policy, it should have a default.
                    # If it's a string policy (like CONFLICT_STRATEGY), empty might be invalid.
                    # For now, if value_str is None, we let the pre-defined default in `config` stand.
                    # If it's a new/unknown policy, it will not be updated here.
                    if policy_key_upper not in config['SYNC_POLICY']:
                        # This means it's a custom policy not in defaults, and it's empty.
                        # Store as empty string or raise error depending on desired strictness.
                        config['SYNC_POLICY'][policy_key_upper] = "" 
                    continue 

                # Process values based on policy type
                value_str_lower_stripped = value_str.lower().strip()
                
                # ===============
                # Sub step 5.1: Handle boolean policies.
                # ===============
                if policy_key_upper in ['AUTO_SYNC_ON_PULL', 'ALLOW_LOCAL_MODIFICATIONS', 
                                        'ALLOW_PUSH_TO_BRAIN', 'AUTO_SYNC_ON_CHECKOUT']: # Known boolean keys
                    if value_str_lower_stripped in ['true', 'yes', '1']:
                        config['SYNC_POLICY'][policy_key_upper] = True
                    elif value_str_lower_stripped in ['false', 'no', '0']:
                        config['SYNC_POLICY'][policy_key_upper] = False
                    else: # Invalid boolean value
                        raise NeuronsConfigError(f"Invalid boolean value '{value_str}' for '{key}' in [SYNC_POLICY]")
                
                # ===============
                # Sub step 5.2: Handle string policies.
                # ===============
                else: # For other policies like CONFLICT_STRATEGY, store as stripped string
                    config['SYNC_POLICY'][policy_key_upper] = value_str.strip() 
        
        # --------------------------------------------------------------
        # STEP 6: Process MAP section.
        # --------------------------------------------------------------
        # Handle MAP section
        if not parser.has_section('MAP'):
             # If strict mode requires MAP section even if empty:
             raise NeuronsConfigError("Missing required [MAP] section")

        # Determine default brain ID if only one brain exists
        default_brain_id: Optional[str] = None
        if len(config['BRAINS']) == 1:
            default_brain_id = next(iter(config['BRAINS']))

        # Check if MAP section actually has items. parser.items('MAP') is empty if section is `[MAP]\n`.
        # If section exists and has items, then proceed.
        if parser.has_section('MAP'):
            map_items = dict(parser.items('MAP'))
            for map_key, map_value_str_raw in map_items.items():
                # Validate map values
                if map_value_str_raw is None or not map_value_str_raw.strip():
                    raise NeuronsConfigError(f"Empty value for mapping key '{map_key}' in [MAP] section.")

                map_value_str = map_value_str_raw.strip()
                parts = map_value_str.split('::')
                
                # Initialize mapping components
                brain_id_in_map: Optional[str] = None
                source_path: Optional[str] = None
                dest_path: Optional[str] = None

                # ===============
                # Sub step 6.1: Parse mapping format (2 or 3 parts).
                # ===============
                if len(parts) == 2:
                    # Format: source::dest (uses default brain)
                    if not default_brain_id:
                        raise NeuronsConfigError(
                            f"Mapping '{map_key} = {map_value_str}' uses default brain syntax (source::dest) "
                            f"but no single default brain is defined, or multiple brains exist. Please specify brain_id."
                        )
                    brain_id_in_map = default_brain_id
                    source_path = parts[0].strip()
                    dest_path = parts[1].strip()
                elif len(parts) == 3:
                    # Format: brain_id::source::dest
                    brain_id_in_map = parts[0].strip()
                    source_path = parts[1].strip()
                    dest_path = parts[2].strip()
                else:
                    raise NeuronsConfigError(f"Invalid mapping format for '{map_key} = {map_value_str}'. Expected 'brain_id::source::dest' or 'source::dest'.")

                # ===============
                # Sub step 6.2: Validate mapping components.
                # ===============
                if not brain_id_in_map or not source_path or not dest_path:
                    raise NeuronsConfigError(f"Incomplete mapping for '{map_key} = {map_value_str}'. All parts (brain_id, source, destination) must be non-empty.")

                if brain_id_in_map not in config['BRAINS']:
                    raise NeuronsConfigError(f"Unknown brain '{brain_id_in_map}' in mapping '{map_key} = {map_value_str}'")
                
                # ===============
                # Sub step 6.3: Add valid mapping to config.
                # ===============
                config['MAP'].append({
                    'brain_id': brain_id_in_map,
                    'source': source_path,
                    'destination': dest_path,
                    '_map_key': map_key.strip() # Store the original key from .neurons file
                })
            
            # ===============
            # Sub step 6.4: Validate that at least one mapping was processed.
            # ===============
            # This check from original code implies that if MAP section exists, it must result in some valid mappings.
            # If map_items is not empty but config['MAP'] is, it means all items were invalid.
            if map_items and not config['MAP']:
                 raise NeuronsConfigError("No valid mappings defined in [MAP] section or all mappings were invalid.")

    except (configparser.Error, ValueError) as e:
        raise NeuronsConfigError(f"Error parsing neurons configuration: {str(e)}")
    
    return config


def save_neurons_config(config: Dict[str, Any], file_path: str = '.neurons') -> None:
    """
    Description:
        Save a neurons configuration dictionary to a file in INI format.
    
    Parameters:
        config (Dict[str, Any]): Neurons configuration dictionary containing well-typed values
                              for BRAINS, SYNC_POLICY, and MAP sections
        file_path (str): Path to save the .neurons file (default: '.neurons')
    
    Returns:
        None
    
    Raises:
        NeuronsConfigError: If the configuration cannot be saved due to IO errors
    """
    # --------------------------------------------------------------
    # STEP 1: Initialize configuration parser.
    # --------------------------------------------------------------
    parser = configparser.ConfigParser()
    parser.optionxform = str  # Preserve case sensitivity

    # --------------------------------------------------------------
    # STEP 2: Build BRAIN sections.
    # --------------------------------------------------------------
    for brain_id, brain_cfg_data in config.get('BRAINS', {}).items():
        section_name = f"BRAIN:{brain_id}"
        parser[section_name] = {} # Ensure section is created
        for key, value in brain_cfg_data.items():
            parser[section_name][key] = str(value)
    
    # --------------------------------------------------------------
    # STEP 3: Build SYNC_POLICY section if present.
    # --------------------------------------------------------------
    if config.get('SYNC_POLICY'): # Only write section if it has content
        parser['SYNC_POLICY'] = {}
        for key, value in config['SYNC_POLICY'].items():
            if type(value) is bool:
                parser['SYNC_POLICY'][key] = str(value).lower()
            else:
                parser['SYNC_POLICY'][key] = str(value) # For strings like 'prompt'
    
    # --------------------------------------------------------------
    # STEP 4: Build MAP section.
    # --------------------------------------------------------------
    parser['MAP'] = {} # Ensure MAP section is always present
    for i, mapping in enumerate(config.get('MAP', [])):
        # Use stored _map_key if available, otherwise generate one
        map_key_name = mapping.get('_map_key')
        if not map_key_name: 
             map_key_name = f"map{i}" # Fallback key naming
        
        # Ensure all parts of the mapping are present before formatting
        b_id = mapping.get('brain_id')
        src = mapping.get('source')
        dst = mapping.get('destination')
        
        if b_id is None or src is None or dst is None:
            # This would indicate a malformed mapping dict was passed to save_neurons_config
            # Consider logging a warning or raising an error for robustness.
            # For now, skip potentially malformed entries to prevent save error.
            continue # Or raise NeuronsConfigError("Malformed mapping item in config to save")

        # Format the mapping string
        value_str = f"{b_id}::{src}::{dst}"
        parser['MAP'][map_key_name] = value_str
    
    # --------------------------------------------------------------
    # STEP 5: Write configuration to file.
    # --------------------------------------------------------------
    try:
        with open(file_path, 'w', encoding='utf-8') as f: # Ensure utf-8 encoding
            parser.write(f)
    except (IOError, OSError) as e:
        raise NeuronsConfigError(f"Error saving neurons configuration: {str(e)}")


def get_current_repo_neurons_config() -> Optional[Dict[str, Any]]:
    """
    Description:
        Get the neurons configuration for the current repository by
        loading the '.neurons' file from the current working directory.
    
    Parameters:
        None
    
    Returns:
        config (Optional[Dict[str, Any]]): Parsed neurons configuration or None if not found or error
    
    Raises:
        NeuronsConfigError: If the configuration file is found but cannot be loaded or parsed
    """
    try:
        return load_neurons_config() # Defaults to '.neurons' in CWD
    except NeuronsConfigError as e:
        # Do not print directly from here in a library function.
        # Let the caller decide how to handle/report the error.
        # For CLI commands, they will catch this if they call it and it raises.
        # The demo script specifically prints this for its own diagnostic purposes.
        # print(f"Error in get_current_repo_neurons_config: {e}", file=sys.stderr)
        raise # Re-raise the exception for the caller to handle
    

def get_current_repo_brain_config() -> Optional[Dict[str, Any]]:
    """
    Description:
        Get the brain configuration for the current repository by
        loading the '.brain' file from the current working directory.

    Parameters:
        None
    
    Returns:
        config (Optional[Dict[str, Any]]): Parsed brain configuration or None if not found
    
    Raises:
        BrainConfigError: If the configuration file is found but cannot be loaded or parsed
    """
    try:
        return load_brain_config() # Defaults to '.brain' in CWD
    except BrainConfigError:
        raise # Re-raise for the caller


def is_brain_repo() -> bool:
    """
    Description:
        Check if the current repository is a brain repository by looking
        for a '.brain' configuration file in the current working directory.
    
    Parameters:
        None
    
    Returns:
        result (bool): True if the repository has a .brain file in CWD, False otherwise
    """
    return os.path.exists('.brain')


def is_neuron_repo() -> bool:
    """
    Description:
        Check if the current repository uses neurons by looking for
        a '.neurons' configuration file in the current working directory.
    
    Parameters:
        None
    
    Returns:
        result (bool): True if the repository has a .neurons file in CWD, False otherwise
    """
    return os.path.exists('.neurons')