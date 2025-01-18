import pulp
from typing import Dict, Any
import pandas as pd
from .base_solver import BaseSolver

class MILPSolver(BaseSolver):
    """MILP implementation of the solver"""
    
    def build_model(self) -> pulp.LpProblem:
        """Build the MILP model"""
        model = pulp.LpProblem(name="Network_Optimization", sense=pulp.LpMinimize)
        return model

    def solve(self) -> Dict[str, Any]:
        """Solve the optimization problem using MILP
        
        Returns:
            Dictionary containing optimization results
        """
        results = {}
        
        # Get ordered objectives
        objectives_input = self.input_data['objectives_input']
        objectives_input_ordered = objectives_input.sort_values(by='Priority')
        priority_list = objectives_input_ordered['Priority'].unique()
        
        # Build initial model
        model = self.build_model()
        base_model = model
        
        # Create solver
        solver = pulp.PULP_CBC_CMD(
            timeLimit=self.parameters['Max Run Time'][1],
            gapRel=self.parameters['Gap Limit'][1]
        )
        
        # Solve with hierarchical objectives
        for x in priority_list:
            current_objectives = objectives_input_ordered[objectives_input_ordered['Priority'] == x]
            
            if x < max(priority_list):
                model_w_objective = base_model.copy()
                for m in current_objectives['Objective']:
                    self.objective_handler.set_single_objective(model_w_objective, m)
                        
                base_model = self.objective_handler.solve_and_set_constraint(
                    model_w_objective,
                    current_objectives['Objective'],
                    current_objectives['Relaxation'],
                    solver
                )
            else:
                model_w_objective = base_model.copy()
                for m in current_objectives['Objective']:
                    self.objective_handler.set_single_objective(model_w_objective, m)
                        
                result = model_w_objective.solve(solver)
                
        # Process results
        results['model'] = result
        results['variables'] = self.variables
        results['sets'] = self.network_sets
        
        return results