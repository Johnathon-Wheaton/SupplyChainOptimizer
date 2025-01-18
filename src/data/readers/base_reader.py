from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseReader(ABC):
    """Abstract base class for data readers"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """Read and return the input data
        
        Returns:
            Dict containing all necessary input values for the optimizer
        """
        pass