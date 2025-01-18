from typing import Dict, Any, List
import pulp
from itertools import product
from .objective_functions import ObjectiveFunctions

class ObjectiveHandler:
    """Handles setting and managing optimization objectives"""
    
    def __init__(self, variables: Dict[str, Any], network_sets: Dict[str, Any], parameters: Dict[str, Any]):
        self.variables = variables
        self.network_sets = network_sets
        self.parameters = parameters
        self.big_m = 999999999
        self.objective_functions = ObjectiveFunctions(variables, network_sets)

    def set_single_objective(self, model: pulp.LpProblem, objective: str) -> None:
        """Set a single objective function
        
        Args:
            model: PuLP model to set objective for
            objective: Name of the objective to set
        """
        if objective == "Minimize Maximum Transit Distance":
            objective_function = self.objective_functions.minimize_maximum_transit_distance()
            
        elif objective == "Minimize Maximum Age":
            objective_function = self.objective_functions.minimize_maximum_age()
            
        elif objective == "Maximize Capacity":
            # Drop constraint that end volume must equal demand
            for n_r, t, p in product(self.network_sets['RECEIVING_NODES'], 
                                   self.network_sets['PERIODS'], 
                                   self.network_sets['PRODUCTS']):
                try:
                    del model.constraints[f"arrived_and_completed_product_equals_demand_{n_r}_{t}_{p}".replace(" ", "_").replace("-", "_")]
                except:
                    continue
            objective_function = self.objective_functions.maximize_capacity()
            
        elif objective == "Minimize Maximum Utilization":
            objective_function = self.objective_functions.minimize_maximum_utilization()
            
        elif objective == "Minimize Plan-Over-Plan Change":
            objective_function = self.objective_functions.minimize_plan_over_plan_change()
            
        elif objective == "Minimize Dropped Volume":
            objective_function = self.objective_functions.minimize_dropped_volume()
            
        elif objective == "Minimize Carried Over Volume":
            objective_function = self.objective_functions.minimize_carried_over_volume()
            
        elif objective == "Minimize Cost":
            objective_function = self.objective_functions.minimize_cost()

        model += objective_function, "Objective"

    def solve_and_set_constraint(self, model: pulp.LpProblem, objectives: List[str], 
                               relaxations: List[float], solver: pulp.LpSolver) -> pulp.LpProblem:
        """Solve model and set constraint for previous objective
        
        Args:
            model: PuLP model to solve and constrain
            objectives: List of objective names
            relaxations: List of relaxation values for each objective
            solver: PuLP solver to use
        
        Returns:
            Updated PuLP model with new constraints
        """
        result = model.solve(solver)
        
        for t in range(len(objectives)):
            if objectives[t] == "Minimize Maximum Transit Distance":
                max_distance_solution = self.variables['max_transit_distance'].varValue
                model += (self.variables['max_transit_distance'] <= max_distance_solution * (1 + relaxations[t]))
                
            elif objectives[t] == "Minimize Maximum Age":
                max_age_solution = self.variables['max_age'].varValue
                model += (self.variables['max_age'] <= max_age_solution * (1 + relaxations[t]))
                
            elif objectives[t] == "Maximize Capacity":
                # Drop constraint that end volume must equal demand
                for n_r, t2, p in product(self.network_sets['RECEIVING_NODES'], 
                                        self.network_sets['PERIODS'], 
                                        self.network_sets['PRODUCTS']):
                    try:
                        del model.constraints[f"arrived_and_completed_product_equals_demand_{n_r}_{t2}_{p}".replace(" ", "_").replace("-", "_")]
                    except:
                        continue
                total_capacity = self.variables['total_arrived_and_completed_product'].varValue
                model += (self.variables['total_arrived_and_completed_product'] >= total_capacity * (1 - relaxations[t]))
                
            elif objectives[t] == "Minimize Maximum Utilization":
                max_utilization_solution = self.variables['max_capacity_utilization'].varValue
                model += (self.variables['max_capacity_utilization'] <= max_utilization_solution * (1 + relaxations[t]))
                
            elif objectives[t] == "Minimize Plan-Over-Plan Change":
                vol_moved_solution = self.variables['total_volume_moved'].varValue
                model += (self.variables['total_volume_moved'] <= vol_moved_solution * (1 + relaxations[t]))
                
            elif objectives[t] == "Minimize Dropped Volume":
                dropped_volume = sum(
                    self.variables['dropped_demand'][n,p,t].varValue
                    for n in self.network_sets['NODES']
                    for p in self.network_sets['PRODUCTS']
                    for t in self.network_sets['PERIODS']
                )
                model += (
                    pulp.lpSum(
                        self.variables['dropped_demand'][(n, p, t)] 
                        for n in self.network_sets['NODES']
                        for p in self.network_sets['PRODUCTS']
                        for t in self.network_sets['PERIODS']
                    ) <= dropped_volume * (1 + relaxations[t])
                )
                
            elif objectives[t] == "Minimize Carried Over Volume":
                carried_over_volume = (
                    sum(self.variables['ib_carried_over_demand'][n_r,p,t].varValue
                        for n_r in self.network_sets['RECEIVING_NODES']
                        for p in self.network_sets['PRODUCTS']
                        for t in self.network_sets['PERIODS']) +
                    sum(self.variables['ob_carried_over_demand'][n_d,p,t].varValue
                        for n_d in self.network_sets['DEPARTING_NODES']
                        for p in self.network_sets['PRODUCTS']
                        for t in self.network_sets['PERIODS'])
                )
                model += (
                    pulp.lpSum(
                        self.variables['ib_carried_over_demand'][(n_r, p, t)] 
                        for n_r in self.network_sets['RECEIVING_NODES']
                        for p in self.network_sets['PRODUCTS']
                        for t in self.network_sets['PERIODS']
                    ) + 
                    pulp.lpSum(
                        self.variables['ob_carried_over_demand'][(n_d, p, t)] 
                        for n_d in self.network_sets['DEPARTING_NODES']
                        for p in self.network_sets['PRODUCTS']
                        for t in self.network_sets['PERIODS']
                    ) <= carried_over_volume * (1 + relaxations[t])
                )
                
            elif objectives[t] == "Minimize Cost":
                total_cost = (
                    self.variables['grand_total_transportation_costs'].varValue +
                    self.variables['grand_total_operating_costs'].varValue +
                    self.variables['grand_total_c_capacity_option'].varValue +
                    self.variables['grand_total_t_capacity_option'].varValue +
                    self.variables['grand_total_carried_and_dropped_volume_cost'].varValue +
                    self.variables['grand_total_launch_cost'].varValue +
                    self.variables['grand_total_shut_down_cost'].varValue +
                    self.variables['grand_total_pop_cost'].varValue +
                    self.variables['grand_total_age_violation_cost'].varValue +
                    self.variables['resource_grand_total_cost'].varValue
                )
                model += (
                    (self.variables['grand_total_transportation_costs'] +
                     self.variables['grand_total_operating_costs'] +
                     self.variables['grand_total_t_capacity_option'] +
                     self.variables['grand_total_c_capacity_option'] +
                     self.variables['grand_total_carried_and_dropped_volume_cost'] +
                     self.variables['grand_total_launch_cost'] +
                     self.variables['grand_total_shut_down_cost'] +
                     self.variables['grand_total_pop_cost'] +
                     self.variables['grand_total_age_violation_cost'] +
                     self.variables['resource_grand_total_cost']
                    ) <= total_cost * (1 + relaxations[t])
                )
        
        return model