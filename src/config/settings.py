from typing import Dict, Any
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

@dataclass
class SolverSettings:
    """Solver-specific settings"""
    max_run_time: int = 3600  # Default max solve time in seconds
    gap_limit: float = 0.01   # Default optimality gap
    solver_name: str = "CBC"  # Default solver

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
    allow_fractional_resources: bool = False
    enforce_cohort_sizes: bool = True
    track_resource_attributes: bool = True

@dataclass
class LoggingSettings:
    """Logging-related settings"""
    log_level: str = "INFO"
    log_file: str = "network_optimizer.log"
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    backup_count: int = 2

class Settings:
    """Global settings configuration"""
    
    def __init__(self, config_file: str = None):
        """Initialize settings
        
        Args:
            config_file: Optional path to config file
        """
        # Initialize default settings
        self.solver = SolverSettings()
        self.network = NetworkSettings()
        self.resources = ResourceSettings()
        self.logging = LoggingSettings()
        
        # Load from file if provided
        if config_file:
            self.load_from_file(config_file)

    def load_from_file(self, config_file: str) -> None:
        """Load settings from config file"""
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        # Load and parse config file
        # This could be JSON, YAML, or other format based on needs
        pass

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
        if 'solver' in settings_dict:
            for key, value in settings_dict['solver'].items():
                setattr(self.solver, key, value)
        
        if 'network' in settings_dict:
            for key, value in settings_dict['network'].items():
                setattr(self.network, key, value)
        
        if 'resources' in settings_dict:
            for key, value in settings_dict['resources'].items():
                setattr(self.resources, key, value)
        
        if 'logging' in settings_dict:
            for key, value in settings_dict['logging'].items():
                setattr(self.logging, key, value)

    def validate(self) -> None:
        """Validate settings configuration"""
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