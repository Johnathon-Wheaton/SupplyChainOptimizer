from itertools import product
import pulp
from .base_constraint import BaseConstraint

class ResourceConstraints(BaseConstraint):
    """Handles resource-related constraints in the network"""

    def build(self, model: pulp.LpProblem) -> None:
        """Build resource constraints"""
        self._build_resource_capacity_constraints(model)
        self._build_resource_cost_constraints(model)

    def _build_resource_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to resource capacity"""
        for n, t, c, g in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['RESOURCE_CAPACITY_TYPES'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n, g), 0) == 1:
                # Child capacity types
                if c in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']:
                    expr = (
                        pulp.lpSum(
                            self.variables['processed_product'][n, p, t] * 
                            self.parameters['resource_capacity_consumption'].get((p, t, g, n, c), 0) 
                            for p in self.network_sets['PRODUCTS']
                        ) +
                        pulp.lpSum(
                            self.variables['processed_product'][n, p, t2] * 
                            self.parameters['resource_capacity_consumption'].get((p, t2, g, n, c), 0) 
                            for t2, p in product(
                                self.network_sets['PERIODS'], 
                                self.network_sets['PRODUCTS']
                            ) 
                            if int(t2) >= int(t) - int(self.parameters['resource_capacity_consumption_periods'].get((p, t2, g, n, c), 0)) 
                            and int(t2) < int(t)
                        ) <= pulp.lpSum(
                            self.variables['resource_capacity'][r, n, t, c] 
                            for r in self.network_sets['RESOURCES']
                        )
                    )
                    model += (expr, f"Capacity_Constraint_{n}_{t}_{c}_{g}")