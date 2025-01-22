from itertools import product
import pulp
from .base_constraint import BaseConstraint

class CapacityConstraints(BaseConstraint):
    """Handles capacity-related constraints in the network"""
    
    def build(self, model: pulp.LpProblem) -> None:
        """Build capacity constraints"""
        self._build_processing_capacity_constraints(model)
        self._build_carrying_capacity_constraints(model)
        self._build_transportation_capacity_constraints(model)
        self._build_max_utilization_constraints(model)

    def _build_processing_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to processing capacity"""
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

                # Parent capacity types
                if c in self.network_sets['RESOURCE_PARENT_CAPACITY_TYPES']:
                    expr = (
                        pulp.lpSum(
                            self.variables['processed_product'][n, p, t] * 
                            self.parameters['resource_capacity_consumption'].get((p, t, g, n, c2), 0) * 
                            self.parameters['capacity_type_heirarchy'].get((c2, c), 0)
                            for p in self.network_sets['PRODUCTS']
                            for c2 in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                        ) +
                        pulp.lpSum(
                            self.variables['processed_product'][n, p, t2] * 
                            self.parameters['resource_capacity_consumption'].get((p, t2, g, n, c2), 0) * 
                            self.parameters['capacity_type_heirarchy'].get((c2, c), 0)
                            for t2, p, c2 in product(
                                self.network_sets['PERIODS'],
                                self.network_sets['PRODUCTS'],
                                self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                            )
                            if int(t2) >= int(t) - int(self.parameters['resource_capacity_consumption_periods'].get((p, t2, g, n, c), 0))
                            and int(t2) < int(t)
                        ) <= pulp.lpSum(
                            self.variables['resource_capacity'][r, n, t, c] 
                            for r in self.network_sets['RESOURCES']
                        )
                    )
                    model += (expr, f"Parent_Capacity_Constraint_{n}_{t}_{c}_{g}")

    def _build_carrying_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to carrying capacity"""
        # Inbound carrying capacity constraints
        for t, n_r, u, g in product(
            self.network_sets['PERIODS'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['MEASURES'],
            self.network_sets['NODEGROUPS']
        ):
            expr = (
                self.parameters['ib_carrying_capacity'].get((t, n_r, u, g), self.big_m) +
                pulp.lpSum(
                    self.variables['use_carrying_capacity_option'][n_r, e_c, t2] *
                    self.parameters['ib_carrying_expansion_capacity'].get((t2, n_r, e_c), 0)
                    for e_c, t2 in product(
                        self.network_sets['C_CAPACITY_EXPANSIONS'],
                        self.network_sets['PERIODS']
                    )
                    if int(t2) <= int(t)
                ) >= pulp.lpSum(
                    self.variables['ib_carried_over_demand'][n_r, p, t] *
                    self.parameters['products_measures'].get((p, u), 0)
                    for p in self.network_sets['PRODUCTS']
                )
            )
            model += (expr, f"IB_CarryingCapacity_{t}_{n_r}_{u}_{g}")

        # Outbound carrying capacity constraints
        for t, n_d, u, g in product(
            self.network_sets['PERIODS'],
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['MEASURES'],
            self.network_sets['NODEGROUPS']
        ):
            expr = (
                self.parameters['ob_carrying_capacity'].get((t, n_d, u, g), self.big_m) +
                pulp.lpSum(
                    self.variables['use_carrying_capacity_option'][n_d, e_c, t2] *
                    self.parameters['ob_carrying_expansion_capacity'].get((t2, n_d, e_c), 0)
                    for e_c, t2 in product(
                        self.network_sets['C_CAPACITY_EXPANSIONS'],
                        self.network_sets['PERIODS']
                    )
                    if int(t2) <= int(t)
                ) >= pulp.lpSum(
                    self.variables['ob_carried_over_demand'][n_d, p, t] *
                    self.parameters['products_measures'].get((p, u), 0)
                    for p in self.network_sets['PRODUCTS']
                )
            )
            model += (expr, f"OB_CarryingCapacity_{t}_{n_d}_{u}_{g}")

    def _build_transportation_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to transportation capacity"""
        for t, o, d, m, u, g_o, g_d in product(
            self.network_sets['PERIODS'],
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['MODES'],
            self.network_sets['MEASURES'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['NODEGROUPS']
        ):
            if (self.parameters['node_in_nodegroup'].get((o, g_o), 0) == 1 and 
                self.parameters['node_in_nodegroup'].get((d, g_d), 0) == 1):
                
                # Base capacity + expansion capacity
                total_capacity = (
                    self.parameters['load_capacity'].get((t, o, d, m, u, g_o, g_d), self.big_m) +
                    pulp.lpSum(
                        self.variables['use_transportation_capacity_option'][o, d, e_t, t2] *
                        self.parameters['transportation_expansion_capacity'].get((e_t, m, 'unit', u), 0)
                        for e_t in self.network_sets['T_CAPACITY_EXPANSIONS']
                        for t2 in self.network_sets['PERIODS']
                        if int(t2) <= int(t)
                    )
                )

                # Constraint expression
                expr = (
                    pulp.lpSum(
                        self.variables['departed_measures'][o, d, p, t, m, u]
                        for p in self.network_sets['PRODUCTS']
                    ) <= total_capacity
                )
                model += (expr, f"Transportation_Capacity_{t}_{o}_{d}_{m}_{u}_{g_o}_{g_d}")

    def _build_max_utilization_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints tracking maximum utilization"""
        for n, t, c in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['RESOURCE_CAPACITY_TYPES']
        ):
            # Calculate current utilization
            expr = (
                self.variables['max_capacity_utilization'] >= 
                self.variables['node_utilization'][n, t, c]
            )
            model += (expr, f"max_capacity_utilization_constraint_{n}_{t}_{c}")