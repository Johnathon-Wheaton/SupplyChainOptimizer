from itertools import product
import pulp
from .base_constraint import BaseConstraint

class FlowConstraints(BaseConstraint):
    """Handles flow-related constraints in the network"""
    
    def build(self, model: pulp.LpProblem) -> None:
        # Extract commonly used sets
        DEPARTING_NODES = self.network_sets['DEPARTING_NODES']
        RECEIVING_NODES = self.network_sets['RECEIVING_NODES']
        PERIODS = self.network_sets['PERIODS']
        PRODUCTS = self.network_sets['PRODUCTS']
        MODES = self.network_sets['MODES']
        
        # Departed product by mode constraints
        for n_d, n_r, t, p in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS, PRODUCTS):
            constraint_expr = pulp.lpSum(
                self.variables['departed_product_by_mode'][n_d, n_r, p, t, m] 
                for m in MODES
            )
            model += (
                self.variables['departed_product'][n_d, n_r, p, t] == constraint_expr,
                f"departed_product_mode_sum_{n_d}_{n_r}_{t}_{p}"
            )

        # Arrived volume equals sum of upstream departures
        for n_r, t, p in product(RECEIVING_NODES, PERIODS, PRODUCTS):
            transport_periods = self.parameters.get('transport_periods', {})
            expr = (
                self.variables['arrived_product'][n_r, p, t] == 
                pulp.lpSum(
                    self.variables['departed_product_by_mode'][n_d, n_r, p, t2, m] 
                    for n_d in DEPARTING_NODES 
                    for m in MODES 
                    for t2 in PERIODS 
                    if int(t2) == int(t) - int(transport_periods.get((n_d, n_r, m), 0))
                )
            )
            model += (expr, f"Arrived_Equals_Departed_Constraint_{n_r}_{t}_{p}")