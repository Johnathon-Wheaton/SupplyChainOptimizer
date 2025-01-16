from itertools import product
from typing import Dict, Any
import pulp
import logging

class ConstraintManager:
    """Coordinates the addition of all constraint types to the model."""
    
    def __init__(self, model: pulp.LpProblem, sets: Dict[str, Any], 
                 params: Dict[str, Any], vars: Dict[str, Any]):
        self.model = model
        self.sets = sets
        self.params = params
        self.vars = vars
        self.logger = logging.getLogger(__name__)
        
        # Initialize constraint generators
        self.flow_constraints = FlowConstraintGenerator(model, sets, params, vars)
        self.capacity_constraints = CapacityConstraintGenerator(model, sets, params, vars)
        self.cost_constraints = CostConstraintGenerator(model, sets, params, vars)

    def add_all_constraints(self):
        """Adds all constraints to the model."""
        try:
            # Add flow constraints
            self.flow_constraints.add_flow_conservation_constraints()
            self.flow_constraints.add_demand_satisfaction_constraints()
            self.flow_constraints.add_age_tracking_constraints()
            
            # Add capacity constraints
            self.capacity_constraints.add_node_capacity_constraints()
            self.capacity_constraints.add_transportation_capacity_constraints()
            
            # Add cost constraints
            self.cost_constraints.add_transportation_cost_constraints()
            self.cost_constraints.add_operating_cost_constraints()
            
            self.logger.info("Successfully added all constraints to the model")
            
        except Exception as e:
            self.logger.error(f"Error adding constraints: {str(e)}")
            raise