from itertools import product
import pulp
from .base_constraint import BaseConstraint

class TransportationConstraints(BaseConstraint):
    def build(self, model: pulp.LpProblem) -> None:
        self._build_transportation_constraints(model)
        self._build_transportation_cost_constraints(model)
    
    def _build_transportation_constraints(self, model: pulp.LpProblem) -> None:
        for n1, n2, t, g in product(
            self.network_sets['NODES'],
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n1, g), 0) == 1 and self.parameters['node_in_nodegroup'].get((n2, g), 0) == 1:
                expr = (
                    pulp.lpSum(
                        self.variables['transported_product'][n1, n2, p, t] 
                        for p in self.network_sets['PRODUCTS']
                    ) <= pulp.lpSum(
                        self.variables['transportation_capacity'][r, n1, n2, t] 
                        for r in self.network_sets['RESOURCES']
                    )
                )
                model += (expr, f"Transportation_Constraint_{n1}_{n2}_{t}_{g}")