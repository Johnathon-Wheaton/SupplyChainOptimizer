import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
from functools import wraps
import time
from config import LoggingSettings

class NetworkOptimizerLogger:
    """Centralized logging configuration for the network optimizer"""
    
    def __init__(self, settings: LoggingSettings):
        """Initialize logger with settings
        
        Args:
            settings: Logging settings configuration
        """
        self.settings = settings
        self.logger = logging.getLogger('network_optimizer')
        self._configure_logger()
        
    def _configure_logger(self) -> None:
        """Configure logger with handlers and formatting"""
        self.logger.setLevel(self.settings.log_level)
        
        # Remove any existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Create formatters
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s(%(lineno)d) - %(message)s'
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        
        # File handler
        file_handler = RotatingFileHandler(
            filename=self.settings.log_file,
            maxBytes=self.settings.max_file_size,
            backupCount=self.settings.backup_count
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    @staticmethod
    def create_log_directory(directory: str = 'logs') -> None:
        """Create logging directory if it doesn't exist"""
        Path(directory).mkdir(exist_ok=True)

    def get_logger(self) -> logging.Logger:
        """Get configured logger instance"""
        return self.logger

def log_execution_time(logger: Optional[logging.Logger] = None):
    """Decorator to log function execution time
    
    Args:
        logger: Logger instance to use. If None, uses root logger.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            
            log = logger or logging.getLogger()
            log.info(f"{func.__name__} executed in {elapsed_time:.2f} seconds")
            
            return result
        return wrapper
    return decorator

class TimedOperation:
    """Context manager for timing operations
    
    Example:
        with TimedOperation("Processing data", logger):
            process_data()
    """
    
    def __init__(self, operation_name: str, logger: Optional[logging.Logger] = None):
        self.operation_name = operation_name
        self.logger = logger or logging.getLogger()
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.info(f"Starting {self.operation_name}...")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_time = time.time() - self.start_time
        if exc_type is None:
            self.logger.info(f"Completed {self.operation_name} in {elapsed_time:.2f} seconds")
        else:
            self.logger.error(f"Error in {self.operation_name} after {elapsed_time:.2f} seconds")

class SolverProgressLogger:
    """Logger for tracking solver progress"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger()
        self.start_time = None
        self.last_log_time = None
        self.log_interval = 10  # seconds
        
    def start_solve(self) -> None:
        """Log solver start"""
        self.start_time = time.time()
        self.last_log_time = self.start_time
        self.logger.info("Starting optimization...")
        
    def log_progress(self, current_objective: float, gap: float) -> None:
        """Log solver progress
        
        Args:
            current_objective: Current objective value
            gap: Current optimality gap
        """
        current_time = time.time()
        if current_time - self.last_log_time >= self.log_interval:
            elapsed_time = current_time - self.start_time
            self.logger.info(
                f"Progress - Time: {elapsed_time:.0f}s, "
                f"Objective: {current_objective:.2f}, "
                f"Gap: {gap:.2%}"
            )
            self.last_log_time = current_time
            
    def end_solve(self, final_objective: float, total_time: float) -> None:
        """Log solver completion
        
        Args:
            final_objective: Final objective value
            total_time: Total solve time in seconds
        """
        self.logger.info(
            f"Optimization complete - "
            f"Final objective: {final_objective:.2f}, "
            f"Total time: {total_time:.0f}s"
        )

def create_run_logger(run_id: str) -> logging.Logger:
    """Create logger for specific optimization run
    
    Args:
        run_id: Unique identifier for the optimization run
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(f'network_optimizer.run.{run_id}')
    
    # Create run-specific log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_handler = RotatingFileHandler(
        filename=f'logs/run_{run_id}_{timestamp}.log',
        maxBytes=5*1024*1024,
        backupCount=2
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger