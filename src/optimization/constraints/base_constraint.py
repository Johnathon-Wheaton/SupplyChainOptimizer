from abc import ABC, abstractmethod
from typing import Dict, Any
import pulp

class BaseConstraint(ABC):
    """Abstract base class for optimization constraints"""
    
    def __init__(self, variables: Dict[str, Any], network_sets: Dict[str, Any], parameters: Dict[str, Any]):
        self.variables = variables
        self.network_sets = network_sets
        self.parameters = parameters
        self.big_m = 999999999

    @abstractmethod
    def build(self, model: pulp.LpProblem) -> None:
        """Add constraints to the optimization model
        
        Args:
            model: PuLP model to add constraints to
        """
        pass