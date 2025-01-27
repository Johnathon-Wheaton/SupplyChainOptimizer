from itertools import product
import pulp
from .base_constraint import BaseConstraint

class ResourceConstraints(BaseConstraint):
    """Handles resource-related constraints in the network"""

    def build(self, model: pulp.LpProblem) -> None:
        """Build resource constraints"""
        self._build_resource_assignment_constraints(model)
        self._build_resource_capacity_constraints(model)
        self._build_resource_attribute_constraints(model)
        self._build_resource_binary_constraints(model)
        self._build_resource_cost_constraints(model)
        self._build_resource_attribute_limits_constraints(model)
        self._build_resource_utilization_constraints(model)

    def _build_resource_assignment_constraints(self, model: pulp.LpProblem) -> None:
        """Constraints for resource assignment across periods and node groups"""
        # Initial period resource assignment
        for r, n, t, g in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['NODES'], 
            self.network_sets['PERIODS'], 
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n,g), 0) == 1:
                if int(t) == 1:
                    # First period: initial resources + added - removed
                    expr = (self.variables['resources_assigned'][r,n,t] == 
                            self.parameters['resource_node_initial_count'].get((n,r,g), 0) + 
                            self.variables['resources_added'][r,n,t] - 
                            self.variables['resources_removed'][r,n,t])
                    model += (expr, f"initial_resources_assigned_{r}_{n}_{t}_{g}")
                else:
                    # Subsequent periods: previous period resources + added - removed
                    expr = (self.variables['resources_assigned'][r,n,t] == 
                            self.variables['resources_assigned'][r,n,str(int(t)-1)] + 
                            self.variables['resources_added'][r,n,t] - 
                            self.variables['resources_removed'][r,n,t])
                    model += (expr, f"resources_assigned_after_{r}_{n}_{t}_{g}")

        # Additional aggregation constraints for initial resources
        for r, n, t in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['NODES'], 
            self.network_sets['PERIODS']
        ):
            # Node-level initial resource check
            if int(t) == 1 and self.parameters['resource_node_initial_count'].get((n,r,'@'), None):
                expr = (
                    pulp.lpSum(self.variables['resources_assigned'][r,n,t] * 
                            self.parameters['node_in_nodegroup'].get((n,g), 0) 
                            for g in self.network_sets['NODEGROUPS']) == 
                    self.parameters['resource_node_initial_count'].get((n,r,'@'), 0) + 
                    pulp.lpSum(
                        self.variables['resources_added'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) - 
                        self.variables['resources_removed'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) 
                        for g in self.network_sets['NODEGROUPS']
                    )
                )
                model += (expr, f"initial_resources_assigned_{r}_{n}_{t}")

        # Resource-level constraints
        for r, t, g in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['PERIODS'], 
            self.network_sets['NODEGROUPS']
        ):
            # Aggregate resources by group
            if int(t) == 1 and self.parameters['resource_node_initial_count'].get(('@',r,g), None):
                expr = (
                    pulp.lpSum(self.variables['resources_assigned'][r,n,t] * 
                            self.parameters['node_in_nodegroup'].get((n,g), 0) 
                            for n in self.network_sets['NODES']) == 
                    self.parameters['resource_node_initial_count'].get(('@',r,g), 0) + 
                    pulp.lpSum(
                        self.variables['resources_added'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) - 
                        self.variables['resources_removed'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) 
                        for n in self.network_sets['NODES']
                    )
                )
                model += (expr, f"initial_resources_assigned_{r}_{t}_{g}")

        # Total resource constraint
        for r, t in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['PERIODS']
        ):
            if int(t) == 1 and self.parameters['resource_node_initial_count'].get(('@',r,'@'), None):
                expr = (
                    pulp.lpSum(self.variables['resources_assigned'][r,n,t] * 
                            self.parameters['node_in_nodegroup'].get((n,g), 0) 
                            for n in self.network_sets['NODES'] 
                            for g in self.network_sets['NODEGROUPS']) == 
                    self.parameters['resource_node_initial_count'].get(('@',r,'@'), 0) + 
                    pulp.lpSum(
                        self.variables['resources_added'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) - 
                        self.variables['resources_removed'][r,n,t] * 
                        self.parameters['node_in_nodegroup'].get((n,g), 0) 
                        for n in self.network_sets['NODES'] 
                        for g in self.network_sets['NODEGROUPS']
                    )
                )
                model += (expr, f"initial_resources_assigned_{r}_{t}")

    def _build_resource_capacity_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to resource capacity"""
        resource_capacity_by_type_sum = {}
        
        # Capacity calculation by type
        for r, t, n, c, g in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['PERIODS'],
            self.network_sets['NODES'],
            self.network_sets['RESOURCE_CAPACITY_TYPES'],
            self.network_sets['NODEGROUPS']
        ):
            # Calculate capacity demand
            if self.parameters['node_in_nodegroup'].get((n,g), 0) == 1:
                if c in self.network_sets['RESOURCE_PARENT_CAPACITY_TYPES']:
                    capacity_demand = sum(
                        self.parameters['resource_capacity_consumption'].get((p, t, g, n, c2), 0) * 
                        self.parameters['capacity_type_hierarchy'].get((c2, c), 0) 
                        for p in self.network_sets['PRODUCTS'] 
                        for c2 in self.network_sets['RESOURCE_CAPACITY_TYPES']
                    )
                else:
                    capacity_demand = sum(
                        self.parameters['resource_capacity_consumption'].get((p, t, g, n, c), 0) 
                        for p in self.network_sets['PRODUCTS']
                    )
                
                # Add capacity constraint if demand exists and capacity is defined
                if (capacity_demand > 0 and 
                    self.parameters['resource_capacity_by_type'].get((t, n, r, c, g), None) is not None):
                    resource_capacity_by_type_sum[(t,n,c,g)] = resource_capacity_by_type_sum.get((t,n,c,g), 0) + self.parameters['resource_capacity_by_type'].get((t,n,r,c,g),0)
                    expr = (
                        self.variables['resource_capacity'][r, n, t, c] <= 
                        self.variables['resources_assigned'][r, n, t] * 
                        self.parameters['resource_capacity_by_type'].get((t, n, r, c, g), 0)
                    )
                    model += (expr, f"capacity_based_on_resources_assigned_{r}_{t}_{n}_{c}_{g}")

    def _build_resource_attribute_constraints(self, model: pulp.LpProblem) -> None:
        """Constraints for resource attribute consumption"""
        for r, t, n, a in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['PERIODS'], 
            self.network_sets['NODES'], 
            self.network_sets['RESOURCE_ATTRIBUTES']
        ):
            if self.parameters['resource_attribute_consumption_per'].get((t, r, a), 0) != 0:
                expr = (
                    self.variables['resource_attribute_consumption'][r, t, n, a] == 
                    self.variables['resources_assigned'][r, n, t] * 
                    self.parameters['resource_attribute_consumption_per'].get((t, r, a), 0)
                )
                model += (expr, f"resource_attribute_consumption_{r}_{t}_{n}_{a}")

    def _build_resource_binary_constraints(self, model: pulp.LpProblem) -> None:
        """Constraints for binary variables related to resource addition/removal"""
        for r, n, t in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['NODES'], 
            self.network_sets['PERIODS']
        ):
            # Bounds for resources added
            expr1 = (
                self.variables['resources_added'][r, n, t] <= 
                self.variables['resources_added_binary'][r, n, t] * 
                self.big_m
            )
            model += (expr1, f"resource_added_binary_lb_{r}_{t}_{n}")
            
            expr2 = (
                self.variables['resources_added'][r, n, t] >= 
                self.variables['resources_added_binary'][r, n, t]
            )
            model += (expr2, f"resource_added_binary_ub_{r}_{t}_{n}")
            
            # Bounds for resources removed
            expr3 = (
                self.variables['resources_removed'][r, n, t] <= 
                self.variables['resources_removed_binary'][r, n, t] * 
                self.big_m
            )
            model += (expr3, f"resource_removed_binary_lb_{r}_{t}_{n}")
            
            expr4 = (
                self.variables['resources_removed'][r, n, t] >= 
                self.variables['resources_removed_binary'][r, n, t]
            )
            model += (expr4, f"resource_removed_binary_ub_{r}_{t}_{n}")

        # Cohort-based constraints for resource addition and removal
        for r, n, t, g in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['NODES'], 
            self.network_sets['PERIODS'], 
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n, g), 0) == 1:
                # Resource addition constraints
                expr1 = (
                    self.variables['resources_added'][r, n, t] >= 
                    self.variables['resource_cohorts_added'][r, n, t] * 
                    self.parameters['resource_add_cohort_count'].get((t, n, r, g), 1)
                )
                model += (expr1, f"resources_added_{r}_{t}_{n}_{g}")
                
                # Resource removal constraints
                expr2 = (
                    self.variables['resources_removed'][r, n, t] >= 
                    self.variables['resource_cohorts_removed'][r, n, t] * 
                    self.parameters['resource_remove_cohort_count'].get((t, n, r, g), 1)
                )
                model += (expr2, f"resources_removed_{r}_{t}_{n}_{g}")

    def _build_resource_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Constraints for resource-related costs"""
        for r, n, t, g in product(
            self.network_sets['RESOURCES'], 
            self.network_sets['NODES'], 
            self.network_sets['PERIODS'], 
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n, g), 0) == 1:
                # Resource addition cost
                expr1 = (
                    self.variables['resource_add_cost'][t, n, r] == 
                    self.variables['resource_cohorts_added'][r, n, t] * 
                    self.parameters['resource_add_cohort_count'].get((t, n, r, g), 1) * 
                    self.parameters['resource_fixed_add_cost'].get((t, n, r, g), 0)
                )
                model += (expr1, f"resources_added_cost_{r}_{t}_{n}_{g}")
                
                # Resource removal cost
                expr2 = (
                    self.variables['resource_remove_cost'][t, n, r] == 
                    self.variables['resource_cohorts_removed'][r, n, t] * 
                    self.parameters['resource_remove_cohort_count'].get((t, n, r, g), 1) * 
                    self.parameters['resource_fixed_remove_cost'].get((t, n, r, g), 0)
                )
                model += (expr2, f"resources_removed_cost_{r}_{t}_{n}_{g}")
                
                # Resource time-based cost
                expr3 = (
                    self.variables['resource_time_cost'][t, n, r] >= 
                    self.variables['resources_assigned'][r, n, t] * 
                    self.parameters['resource_cost_per_time'].get((t, n, r, g), 0)
                )
                model += (expr3, f"resources_time_cost_{r}_{t}_{n}_{g}")

        # Grand total resource cost
        expr = (
            self.variables['resource_grand_total_cost'] == 
            pulp.lpSum(
                self.variables['resource_add_cost'][t, n, r] + 
                self.variables['resource_remove_cost'][t, n, r] + 
                self.variables['resource_time_cost'][t, n, r] 
                for t, n, r in product(
                    self.network_sets['PERIODS'], 
                    self.network_sets['NODES'], 
                    self.network_sets['RESOURCES']
                )
            )
        )
        model += (expr, "resources_grand_total_cost")

    def _build_resource_attribute_limits_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for resource attribute limits"""
        # Add '@' to lists for aggregation
        resourceattributes = list(self.network_sets['RESOURCE_ATTRIBUTES']) + ['@']
        resources = list(self.network_sets['RESOURCES']) + ['@']
        nodes = list(self.network_sets['NODES']) + ['@']
        periods = list(self.network_sets['PERIODS']) + ['@']
        nodegroups = list(self.network_sets['NODEGROUPS']) + ['@']

        if (self.parameters.get('resource_attribute_min') or 
            self.parameters.get('resource_attribute_max')):
            
            for n_index in nodes:
                for g_index in nodegroups:
                    if n_index == '@' or self.parameters['node_in_nodegroup'].get((n_index, g_index), 0) == 1:
                        nodes_list = self.network_sets['NODES'] if n_index == '@' else [n_index]
                        
                        for t_index in periods:
                            periods_list = self.network_sets['PERIODS'] if t_index == '@' else [t_index]
                            
                            for r_index in resources:
                                resources_list = self.network_sets['RESOURCES'] if r_index == '@' else [r_index]
                                
                                # Resource addition min/max constraints
                                min_add_expr = (
                                    self.parameters['resource_min_to_add'].get((t_index, n_index, r_index, g_index), 0) <= 
                                    pulp.lpSum(
                                        self.variables['resources_added'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (min_add_expr, f"resources_added_min_{t_index}_{n_index}_{r_index}_{g_index}")
                                
                                max_add_expr = (
                                    self.parameters['resource_max_to_add'].get(
                                        (t_index, n_index, r_index, g_index),
                                        self.big_m
                                    ) >= pulp.lpSum(
                                        self.variables['resources_added'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (max_add_expr, f"resource_added_max_{t_index}_{n_index}_{r_index}_{g_index}")

                                # Resource removal min/max constraints
                                min_remove_expr = (
                                    self.parameters['resource_min_to_remove'].get((t_index, n_index, r_index, g_index), 0) <= 
                                    pulp.lpSum(
                                        self.variables['resources_removed'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (min_remove_expr, f"resources_removed_min_{t_index}_{n_index}_{r_index}_{g_index}")
                                
                                max_remove_expr = (
                                    self.parameters['resource_max_to_remove'].get(
                                        (t_index, n_index, r_index, g_index),
                                        self.big_m
                                    ) >= pulp.lpSum(
                                        self.variables['resources_removed'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (max_remove_expr, f"resource_removed_max_{t_index}_{n_index}_{r_index}_{g_index}")

                                # Total resource count min/max constraints
                                min_total_expr = (
                                    self.parameters['resource_node_min_count'].get((t_index, n_index, r_index, g_index), 0) <= 
                                    pulp.lpSum(
                                        self.variables['resources_assigned'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (min_total_expr, f"resources_total_min_{t_index}_{n_index}_{r_index}_{g_index}")
                                
                                max_total_expr = (
                                    self.parameters['resource_node_max_count'].get(
                                        (t_index, n_index, r_index, g_index),
                                        self.big_m
                                    ) >= pulp.lpSum(
                                        self.variables['resources_assigned'][r,n,t]
                                        for n in nodes_list
                                        for r in resources_list
                                        for t in periods_list
                                    )
                                )
                                model += (max_total_expr, f"resources_total_max_{t_index}_{n_index}_{r_index}_{g_index}")

                                # Resource attribute min/max constraints
                                for a_index in resourceattributes:
                                    resource_attributes_list = (
                                        self.network_sets['RESOURCE_ATTRIBUTES'] 
                                        if a_index == '@' else [a_index]
                                    )
                                    
                                    min_attr_expr = (
                                        self.parameters['resource_attribute_min'].get(
                                            (t_index, n_index, r_index, g_index, a_index), 0
                                        ) <= pulp.lpSum(
                                            self.variables['resources_assigned'][r,n,t] * 
                                            self.parameters['resource_attribute_consumption_per'].get((t,r,a), 0)
                                            for n in nodes_list
                                            for r in resources_list
                                            for t in periods_list
                                            for a in resource_attributes_list
                                        )
                                    )
                                    model += (min_attr_expr, f"resource_attribute_min_constraint_{t_index}_{n_index}_{a_index}_{r_index}_{g_index}")
                                    
                                    max_attr_expr = (
                                        self.parameters['resource_attribute_max'].get(
                                            (t_index, n_index, r_index, g_index, a_index),
                                            self.big_m
                                        ) >= pulp.lpSum(
                                            self.variables['resources_assigned'][r,n,t] * 
                                            self.parameters['resource_attribute_consumption_per'].get((t,r,a), 0)
                                            for n in nodes_list
                                            for r in resources_list
                                            for t in periods_list
                                            for a in resource_attributes_list
                                        )
                                    )
                                    model += (max_attr_expr, f"resource_attribute_max_constraint_{t_index}_{n_index}_{a_index}_{r_index}_{g_index}")

    def _build_resource_utilization_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for resource utilization tracking"""
        if self.parameters.get('resource_capacity_consumption'):
            for r, n, t, c, g in product(
                self.network_sets['RESOURCES'],
                self.network_sets['NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES'],
                self.network_sets['NODEGROUPS']
            ):
                if (self.parameters['node_in_nodegroup'].get((n,g),0) == 1 and 
                    self.parameters['resource_capacity_by_type'].get((t,n,r,c,g)) is not None):
                    
                    initial_capacity = (
                        self.parameters['resource_capacity_by_type'].get((t,n,r,c,g), 1) * 
                        self.parameters['resource_node_initial_count'].get((n,r,g), 0)
                    )
                    
                    # Child capacity types
                    if c in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']:
                        if initial_capacity > 0:
                            expr = (
                                self.variables['node_utilization'][n,t,c] <= (
                                    pulp.lpSum(
                                        self.variables['processed_product'][n,p,t] * 
                                        self.parameters['resource_capacity_consumption'].get((p,t,g,n,c), 0) 
                                        for p in self.network_sets['PRODUCTS']
                                    ) +
                                    pulp.lpSum(
                                        self.variables['processed_product'][n,p,t2] * 
                                        self.parameters['resource_capacity_consumption'].get((p,t2,g,n,c), 0)
                                        for t2, p in product(
                                            self.network_sets['PERIODS'],
                                            self.network_sets['PRODUCTS']
                                        )
                                        if int(t2) >= int(t) - int(self.parameters['capacity_consumption_periods'].get((t2,n,p,g), 0))
                                        and int(t2) < int(t)
                                    )
                                ) / initial_capacity
                            )
                        else:
                            expr = (self.variables['node_utilization'][n,t,c] == 0)
                        model += (expr, f"Utilization_constraint_{r}_{n}_{t}_{c}_{g}")

                    # Parent capacity types
                    if c in self.network_sets['RESOURCE_PARENT_CAPACITY_TYPES']:
                        if initial_capacity > 0:
                            expr = (
                                self.variables['node_utilization'][n,t,c] <= (
                                    pulp.lpSum(
                                        self.variables['processed_product'][n,p,t] * 
                                        self.parameters['resource_capacity_consumption'].get((p,t,g,n,c2), 0) * 
                                        self.parameters['capacity_type_hierarchy'].get((c2,c), 0)
                                        for p in self.network_sets['PRODUCTS']
                                        for c2 in self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                                    ) +
                                    pulp.lpSum(
                                        self.variables['processed_product'][n,p,t2] * 
                                        self.parameters['resource_capacity_consumption'].get((p,t2,g,n,c2), 0) * 
                                        self.parameters['capacity_type_hierarchy'].get((c2,c), 0)
                                        for t2, p, c2 in product(
                                            self.network_sets['PERIODS'],
                                            self.network_sets['PRODUCTS'],
                                            self.network_sets['RESOURCE_CHILD_CAPACITY_TYPES']
                                        )
                                        if int(t2) >= int(t) - int(self.parameters['capacity_consumption_periods'].get((t2,n,p,g), 0))
                                        and int(t2) < int(t)
                                    )
                                ) / initial_capacity
                            )
                        else:
                            expr = (self.variables['node_utilization'][n,t,c] == 0)
                        model += (expr, f"Utilization_constraint_{r}_{n}_{t}_{c}_{g}")