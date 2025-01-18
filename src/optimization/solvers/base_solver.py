from abc import ABC, abstractmethod
from typing import Dict, Any
import pulp
from optimization.objectives.objective_handler import ObjectiveHandler

class BaseSolver(ABC):
    """Abstract base class for optimization solvers"""
    
    def __init__(self, variables: Dict[str, Any], network_sets: Dict[str, Any], 
                 parameters: Dict[str, Any], input_data: Dict[str, Any]):
        self.variables = variables
        self.network_sets = network_sets
        self.parameters = parameters
        self.input_data = input_data
        self.objective_handler = ObjectiveHandler(variables, network_sets, parameters)

    @abstractmethod
    def solve(self) -> Dict[str, Any]:
        """Solve the optimization problem
        
        Returns:
            Dictionary containing optimization results
        """
        pass

    @abstractmethod
    def build_model(self) -> Any:
        """Build the optimization model
        
        Returns:
            The constructed model object
        """
        pass