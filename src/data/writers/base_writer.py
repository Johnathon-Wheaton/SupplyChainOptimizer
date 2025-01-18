from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd

class BaseWriter(ABC):
    """Abstract base class for data writers"""
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        
    @abstractmethod
    def write(self, results: Dict[str, pd.DataFrame]) -> None:
        """Write optimization results to file
        
        Args:
            results: Dictionary of pandas DataFrames containing optimization results
        """
        pass