from itertools import product
import pulp
from .base_constraint import BaseConstraint

class CostConstraints(BaseConstraint):
    """Handles cost-related constraints in the network"""
    def build(self, model: pulp.LpProblem) -> None:
        """Build cost constraints"""
        self._build_cost_constraints(model)
        self._build_cost_limit_constraints(model)

    def _build_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to costs"""
        for n, t, c, g in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['RESOURCE_COST_TYPES'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n, g), 0) == 1:
                expr = (
                    pulp.lpSum(
                        self.variables['processed_product'][n, p, t] * 
                        self.parameters['resource_cost'].get((p, t, g, n, c), 0) 
                        for p in self.network_sets['PRODUCTS']
                    ) +
                    pulp.lpSum(
                        self.variables['processed_product'][n, p, t2] * 
                        self.parameters['resource_cost'].get((p, t2, g, n, c), 0) 
                        for t2, p in product(
                            self.network_sets['PERIODS'], 
                            self.network_sets['PRODUCTS']
                        ) 
                        if int(t2) >= int(t) - int(self.parameters['resource_cost_periods'].get((p, t2, g, n, c), 0)) 
                        and int(t2) < int(t)
                    ) <= pulp.lpSum(
                        self.variables['resource_cost'][r, n, t, c] 
                        for r in self.network_sets['RESOURCES']
                    )
                )
                model += (expr, f"Cost_Constraint_{n}_{t}_{c}_{g}")