import pulp
from itertools import product
from typing import Dict, Any

class ObjectiveFunctions:
    """Defines individual objective functions for the optimization"""
    
    def __init__(self, variables: Dict[str, Any], network_sets: Dict[str, Any]):
        self.variables = variables
        self.network_sets = network_sets
    
    def minimize_maximum_transit_distance(self) -> pulp.LpVariable:
        """Objective: Minimize the maximum transit distance"""
        return self.variables['max_transit_distance']
    
    def minimize_maximum_age(self) -> pulp.LpVariable:
        """Objective: Minimize the maximum age"""
        return self.variables['max_age']
    
    def maximize_capacity(self) -> pulp.LpVariable:
        """Objective: Maximize total capacity"""
        return -self.variables['total_arrived_and_completed_product']
    
    def minimize_maximum_utilization(self) -> pulp.LpVariable:
        """Objective: Minimize the maximum capacity utilization"""
        return self.variables['max_capacity_utilization']
    
    def minimize_plan_over_plan_change(self) -> pulp.LpVariable:
        """Objective: Minimize plan-over-plan changes"""
        return self.variables['total_volume_moved']
    
    def minimize_dropped_volume(self) -> pulp.LpAffineExpression:
        """Objective: Minimize total dropped volume"""
        return pulp.lpSum(
            self.variables['dropped_demand'][(n, p, t)] 
            for n in self.network_sets['NODES'] 
            for p in self.network_sets['PRODUCTS'] 
            for t in self.network_sets['PERIODS']
        )
    
    def minimize_carried_over_volume(self) -> pulp.LpAffineExpression:
        """Objective: Minimize total carried over volume"""
        return (
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
            )
        )
    
    def minimize_cost(self) -> pulp.LpAffineExpression:
        """Objective: Minimize total cost"""
        return (
            self.variables['grand_total_transportation_costs'] +
            self.variables['grand_total_operating_costs'] +
            self.variables['grand_total_t_capacity_option'] +
            self.variables['grand_total_c_capacity_option'] +
            self.variables['grand_total_carried_and_dropped_volume_cost'] +
            self.variables['grand_total_launch_cost'] +
            self.variables['grand_total_shut_down_cost'] +
            self.variables['grand_total_pop_cost'] +
            self.variables['grand_total_age_violation_cost'] +
            self.variables['resource_grand_total_cost']
        )