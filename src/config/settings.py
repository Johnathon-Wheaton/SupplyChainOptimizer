from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
import json
import yaml
import logging
import os

@dataclass
class SolverSettings:
    """Solver-specific settings"""
    max_run_time: int = 3600
    gap_limit: float = 0.01
    solver_name: str = "HiGHS"
    # solver_name: str = "CBC"
    # solver_name: str = "SCIP"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    solver_file_path = os.path.join(script_dir, "../solvers", "highs.exe")
    # solver_file_path = os.path.join(script_dir, "../solvers/Cbc-master-x86_64-w64-mingw32/bin", "cbc.exe")
    # solver_file_path = os.path.join(script_dir, "../solvers", "SCIPOptSuite-9.2.1-win64.exe")

@dataclass
class NetworkSettings:
    """Network-related settings"""
    big_m: int = 999999999
    allow_partial_shipments: bool = True
    enforce_direct_shipping: bool = False
    max_intermediate_stops: int = 2

@dataclass
class ResourceSettings:
    """Resource-related settings"""
    allow_fractional_resources: bool = False #TODO: Integrate fractional resources
    enforce_cohort_sizes: bool = True #TODO: Integrate cohor size enforcement option

@dataclass
class LoggingSettings:
    """Logging-related settings"""
    log_level: str = "INFO"
    log_file: str = "network_optimizer.log"
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    backup_count: int = 2

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class Settings:
    """Global settings configuration"""
    
    def __init__(self, config_file: str = None):
        """Initialize settings
        
        Args:
            config_file: Optional path to config file
        """
        self.solver = SolverSettings()
        self.network = NetworkSettings()
        self.resources = ResourceSettings()
        self.logging = LoggingSettings()
        
        if config_file:
            self.load_from_file(config_file)
            self.validate()

    def load_from_file(self, config_file: str) -> None:
        """Load settings from config file
        
        Args:
            config_file: Path to config file (JSON or YAML)
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ConfigurationError: If config file format is invalid
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        try:
            # Determine file type from extension
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(config_path, 'r') as f:
                    config_dict = yaml.safe_load(f)
            elif config_path.suffix.lower() == '.json':
                with open(config_path, 'r') as f:
                    config_dict = json.load(f)
            else:
                raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")

            # Update settings
            self.update(config_dict)

        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigurationError(f"Error parsing config file: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file: {str(e)}")

    def save_to_file(self, config_file: str) -> None:
        """Save current settings to file
        
        Args:
            config_file: Path to save config file
            
        Raises:
            ConfigurationError: If file cannot be written or format is unsupported
        """
        config_path = Path(config_file)
        
        try:
            config_dict = self.to_dict()
            
            # Save based on file extension
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                with open(config_path, 'w') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
            elif config_path.suffix.lower() == '.json':
                with open(config_path, 'w') as f:
                    json.dump(config_dict, f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported config file format: {config_path.suffix}")
                
        except Exception as e:
            raise ConfigurationError(f"Error saving config file: {str(e)}")

    @classmethod
    def load_default(cls) -> 'Settings':
        """Load default settings"""
        return cls()

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'Settings':
        """Create Settings instance from dictionary
        
        Args:
            config_dict: Dictionary containing settings
            
        Returns:
            New Settings instance
        """
        settings = cls()
        settings.update(config_dict)
        settings.validate()
        return settings

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            'solver': {
                'max_run_time': self.solver.max_run_time,
                'gap_limit': self.solver.gap_limit,
                'solver_name': self.solver.solver_name
            },
            'network': {
                'big_m': self.network.big_m,
                'allow_partial_shipments': self.network.allow_partial_shipments,
                'enforce_direct_shipping': self.network.enforce_direct_shipping,
                'max_intermediate_stops': self.network.max_intermediate_stops
            },
            'resources': {
                'allow_fractional_resources': self.resources.allow_fractional_resources,
                'enforce_cohort_sizes': self.resources.enforce_cohort_sizes,
                'track_resource_attributes': self.resources.track_resource_attributes
            },
            'logging': {
                'log_level': self.logging.log_level,
                'log_file': self.logging.log_file,
                'max_file_size': self.logging.max_file_size,
                'backup_count': self.logging.backup_count
            }
        }

    def update(self, settings_dict: Dict[str, Any]) -> None:
        """Update settings from dictionary"""
        try:
            if 'solver' in settings_dict:
                for key, value in settings_dict['solver'].items():
                    if hasattr(self.solver, key):
                        setattr(self.solver, key, value)
                    else:
                        logging.warning(f"Unknown solver setting: {key}")
            
            if 'network' in settings_dict:
                for key, value in settings_dict['network'].items():
                    if hasattr(self.network, key):
                        setattr(self.network, key, value)
                    else:
                        logging.warning(f"Unknown network setting: {key}")
            
            if 'resources' in settings_dict:
                for key, value in settings_dict['resources'].items():
                    if hasattr(self.resources, key):
                        setattr(self.resources, key, value)
                    else:
                        logging.warning(f"Unknown resource setting: {key}")
            
            if 'logging' in settings_dict:
                for key, value in settings_dict['logging'].items():
                    if hasattr(self.logging, key):
                        setattr(self.logging, key, value)
                    else:
                        logging.warning(f"Unknown logging setting: {key}")
                        
        except Exception as e:
            raise ConfigurationError(f"Error updating settings: {str(e)}")

    def validate(self) -> None:
        """Validate settings configuration
        
        Raises:
            ConfigurationError: If any settings are invalid
        """
        try:
            if self.solver.max_run_time <= 0:
                raise ValueError("max_run_time must be positive")
            
            if not (0 <= self.solver.gap_limit <= 1):
                raise ValueError("gap_limit must be between 0 and 1")
            
            if self.network.big_m <= 0:
                raise ValueError("big_m must be positive")
            
            if self.network.max_intermediate_stops < 0:
                raise ValueError("max_intermediate_stops cannot be negative")
            
            if self.logging.max_file_size <= 0:
                raise ValueError("max_file_size must be positive")
            
            if self.logging.backup_count < 0:
                raise ValueError("backup_count cannot be negative")
            
            if self.logging.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                raise ValueError("Invalid log_level")
                
        except ValueError as e:
            raise ConfigurationError(str(e))