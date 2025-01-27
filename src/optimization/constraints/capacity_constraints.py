from itertools import product
import pulp
from .base_constraint import BaseConstraint

class CapacityConstraints(BaseConstraint):
    """Handles capacity-related constraints in the network"""
    
    def build(self, model: pulp.LpProblem) -> None:
        """Build capacity constraints"""
        self._build_processing_capacity_constraints(model)
        self._build_carrying_capacity_constraints(model)
        self._build_max_utilization_constraints(model)
        self._build_assembly_constraints(model)
        self._build_max_carried_demand_constraints(model)
        self._build_capacity_option_cost_constraints(model)

    def _build_processing_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to processing capacity"""
        if self.parameters['resource_capacity_consumption']:
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
                                self.parameters['capacity_type_hierarchy'].get((c2, c), 0)
                                for p in self.network_sets['PRODUCTS']
                                for c2 in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                            ) +
                            pulp.lpSum(
                                self.variables['processed_product'][n, p, t2] * 
                                self.parameters['resource_capacity_consumption'].get((p, t2, g, n, c2), 0) * 
                                self.parameters['capacity_type_hierarchy'].get((c2, c), 0)
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
    
    def _build_assembly_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for assembly requirements between products"""
        for t, p1, p2, n, g in product(
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODES'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n,g),0) == 1:
                if (self.parameters['processing_assembly_p1_required'].get((n,g,p1,p2)) is not None and 
                    self.parameters['processing_assembly_p2_required'].get((n,g,p1,p2)) is not None):
                    expr = (
                        self.variables['processed_product'][n,p1,t] * 
                        self.parameters['processing_assembly_p1_required'][n,g,p1,p2] == 
                        self.variables['processed_product'][n,p2,t] * 
                        self.parameters['processing_assembly_p2_required'][n,g,p1,p2]
                    )
                    model += (expr, f"processed_volume_assembly_constraints_{n}_{t}_{p1}_{p2}")

    def _build_max_carried_demand_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for maximum carried demand"""
        # Add '@' to sets for aggregation
        nodes = list(self.network_sets['NODES']) + ['@']
        receiving_nodes = list(self.network_sets['RECEIVING_NODES']) + ['@']
        departing_nodes = list(self.network_sets['DEPARTING_NODES']) + ['@']
        periods = list(self.network_sets['PERIODS']) + ['@']
        products = list(self.network_sets['PRODUCTS']) + ['@']

        # Maximum dropped demand constraints
        for n_index in nodes:
            for g_index in self.network_sets['NODEGROUPS']:
                if n_index == '@' or self.parameters['node_in_nodegroup'].get((n_index, g_index), 0) == 1:
                    nodes_list = self.network_sets['NODES'] if n_index == '@' else [n_index]
                    
                    for t_index in periods:
                        periods_list = self.network_sets['PERIODS'] if t_index == '@' else [t_index]
                        
                        for p_index in products:
                            products_list = self.network_sets['PRODUCTS'] if p_index == '@' else [p_index]
                            
                            expr = (
                                self.parameters['max_dropped'].get(
                                    (t_index, p_index, n_index, g_index), 
                                    self.big_m
                                ) >= pulp.lpSum(
                                    self.variables['dropped_demand'][n, p, t]
                                    for n in nodes_list
                                    for p in products_list
                                    for t in periods_list
                                )
                            )
                            model += (expr, f"Max_Dropped_{t_index}_{p_index}_{n_index}_{g_index}")

        # Maximum inbound carried demand constraints
        for n_index in receiving_nodes:
            for g_index in self.network_sets['NODEGROUPS']:
                if n_index == '@' or self.parameters['node_in_nodegroup'].get((n_index, g_index), 0) == 1:
                    nodes_list = self.network_sets['RECEIVING_NODES'] if n_index == '@' else [n_index]
                    
                    for t_index in periods:
                        periods_list = self.network_sets['PERIODS'] if t_index == '@' else [t_index]
                        
                        for p_index in products:
                            products_list = self.network_sets['PRODUCTS'] if p_index == '@' else [p_index]
                            
                            expr = (
                                self.parameters['ib_max_carried'].get(
                                    (t_index, p_index, n_index, g_index), 
                                    self.big_m
                                ) >= pulp.lpSum(
                                    self.variables['ib_carried_over_demand'][n, p, t]
                                    for n in nodes_list
                                    for p in products_list
                                    for t in periods_list
                                )
                            )
                            model += (expr, f"IB_Max_Carried_{t_index}_{p_index}_{n_index}_{g_index}")

        # Maximum outbound carried demand constraints
        for n_index in departing_nodes:
            for g_index in self.network_sets['NODEGROUPS']:
                if n_index == '@' or self.parameters['node_in_nodegroup'].get((n_index, g_index), 0) == 1:
                    nodes_list = self.network_sets['DEPARTING_NODES'] if n_index == '@' else [n_index]
                    
                    for t_index in periods:
                        periods_list = self.network_sets['PERIODS'] if t_index == '@' else [t_index]
                        
                        for p_index in products:
                            products_list = self.network_sets['PRODUCTS'] if p_index == '@' else [p_index]
                            
                            expr = (
                                self.parameters['ob_max_carried'].get(
                                    (t_index, p_index, n_index, g_index), 
                                    self.big_m
                                ) >= pulp.lpSum(
                                    self.variables['ob_carried_over_demand'][n, p, t]
                                    for n in nodes_list
                                    for p in products_list
                                    for t in periods_list
                                )
                            )
                            model += (expr, f"OB_Max_Carried_{t_index}_{p_index}_{n_index}_{g_index}")

    def _build_capacity_option_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for capacity option costs"""
        # Capacity option costs by period and node
        for t, n, e_c in product(
            self.network_sets['PERIODS'],
            self.network_sets['NODES'],
            self.network_sets['C_CAPACITY_EXPANSIONS']
        ):
            expr = (
                self.variables['c_capacity_option_cost'][t, n, e_c] ==
                self.parameters['period_weight'].get(int(t), 1) * 
                self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                self.parameters['carrying_expansions'].get((t, n, e_c), 0) +
                self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                pulp.lpSum(
                    self.parameters['carrying_expansions_persisting_cost'].get((t2, n, e_c), 0) 
                    for t2 in self.network_sets['PERIODS'] 
                    if int(t2) >= int(t)
                )
            )
            model += (expr, f"CarryingCapacityOptionCost_{t}_{n}_{e_c}")

        # Capacity option costs by location type
        for n, e_c in product(
            self.network_sets['NODES'],
            self.network_sets['C_CAPACITY_EXPANSIONS']
        ):
            expr = (
                self.variables['c_capacity_option_cost_by_location_type'][n, e_c] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t), 1) * 
                    self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                    self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                    for t in self.network_sets['PERIODS']
                )
            )
            model += (expr, f"CarryingCapacityOptionCostByLocationType_{n}_{e_c}")

        # Capacity option costs by period type
        for e_c, t in product(
            self.network_sets['C_CAPACITY_EXPANSIONS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                self.variables['c_capacity_option_cost_by_period_type'][e_c, t] ==
                self.parameters['period_weight'].get(int(t), 1) * 
                pulp.lpSum(
                    self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                    self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                    for n in self.network_sets['NODES']
                )
            )
            model += (expr, f"CarryingCapacityOptionCostByPeriodType_{e_c}_{t}")

        # Capacity option costs by location
        for n in self.network_sets['NODES']:
            expr = (
                self.variables['c_capacity_option_cost_by_location'][n] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t), 1) * 
                    self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                    self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                    for t, e_c in product(
                        self.network_sets['PERIODS'],
                        self.network_sets['C_CAPACITY_EXPANSIONS']
                    )
                )
            )
            model += (expr, f"CarryingCapacityOptionCostByLocation_{n}")

        # Capacity option costs by period
        for t in self.network_sets['PERIODS']:
            expr = (
                self.variables['c_capacity_option_cost_by_period'][t] ==
                self.parameters['period_weight'].get(int(t), 1) * 
                pulp.lpSum(
                    self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                    self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                    for n, e_c in product(
                        self.network_sets['NODES'],
                        self.network_sets['C_CAPACITY_EXPANSIONS']
                    )
                )
            )
            model += (expr, f"CarryingCapacityOptionCostByPeriod_{t}")

        # Capacity option costs by type
        for e_c in self.network_sets['C_CAPACITY_EXPANSIONS']:
            expr = (
                self.variables['c_capacity_option_cost_by_type'][e_c] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t), 1) * 
                    self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                    self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                    for n, t in product(
                        self.network_sets['NODES'],
                        self.network_sets['PERIODS']
                    )
                )
            )
            model += (expr, f"CarryingCapacityOptionCostByType_{e_c}")

        # Grand total capacity option cost
        expr = (
            self.variables['grand_total_c_capacity_option'] ==
            pulp.lpSum(
                self.parameters['period_weight'].get(int(t), 1) * 
                self.variables['use_carrying_capacity_option'][n,e_c,t] * 
                self.parameters['carrying_expansions'].get((t, n, e_c), 0) 
                for n, t, e_c in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS'],
                    self.network_sets['C_CAPACITY_EXPANSIONS']
                )
            )
        )
        model += (expr, "GrandTotalCarryingCapacityOption")

    def _build_processing_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to processing capacity"""
        if self.parameters['resource_capacity_consumption']:
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
                                self.parameters['capacity_type_hierarchy'].get((c2, c), 0)
                                for p in self.network_sets['PRODUCTS']
                                for c2 in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                            ) +
                            pulp.lpSum(
                                self.variables['processed_product'][n, p, t2] * 
                                self.parameters['resource_capacity_consumption'].get((p, t2, g, n, c2), 0) * 
                                self.parameters['capacity_type_hierarchy'].get((c2, c), 0)
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