from itertools import product
import pulp
from .base_constraint import BaseConstraint

class FlowConstraints(BaseConstraint):
    """Handles flow-related constraints in the network"""
    
    def build(self, model: pulp.LpProblem) -> None:
        """Build flow constraints"""
        self._build_mode_aggregation_constraints(model)
        self._build_arrival_constraints(model)
        self._build_processing_constraints(model)
        self._build_departure_constraints(model)
        self._build_destination_demand_constraints(model)
        self._build_origin_demand_constraints(model)
        self._build_node_type_constraints(model)
        self._build_demand_completion_constraints(model)
        self._build_flow_limit_constraints(model)
        self._build_destination_assignment_constraints(model)

    def _build_node_type_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for valid flows between node types"""
        for n, n2, p, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            max_value = 0
            if n == n2:
                max_value += self.big_m
            if (n in self.network_sets['ORIGINS'] and 
                n in self.network_sets['SEND_TO_DESTINATIONS_NODES'] and 
                n2 in self.network_sets['DESTINATIONS'] and 
                n2 in self.network_sets['RECEIVE_FROM_ORIGIN_NODES']):
                max_value += self.big_m
            if (n in self.network_sets['ORIGINS'] and 
                n in self.network_sets['SEND_TO_INTERMEDIATES_NODES'] and 
                n2 in self.network_sets['INTERMEDIATES'] and 
                n2 in self.network_sets['RECEIVE_FROM_ORIGIN_NODES']):
                max_value += self.big_m
            if (n in self.network_sets['INTERMEDIATES'] and 
                n in self.network_sets['SEND_TO_DESTINATIONS_NODES'] and 
                n2 in self.network_sets['DESTINATIONS'] and 
                n2 in self.network_sets['RECEIVE_FROM_INTERMEDIATES_NODES']):
                max_value += self.big_m
            if (n in self.network_sets['INTERMEDIATES'] and 
                n in self.network_sets['SEND_TO_INTERMEDIATES_NODES'] and 
                n2 in self.network_sets['INTERMEDIATES'] and 
                n2 in self.network_sets['RECEIVE_FROM_INTERMEDIATES_NODES']):
                max_value += self.big_m
            
            expr = (self.variables['departed_product'][n,n2,p,t] <= max_value)
            model += (expr, f"node_type_constraints_{n}_{n2}_{p}_{t}")
    
    def _build_demand_completion_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for demand completion"""
        # Individual node demand completion
        for n_r, t, p in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS']
        ):
            expr1 = (
                self.variables['arrived_and_completed_product'][t, p, n_r] == 
                self.parameters['demand'].get((t, p, n_r), 0)
            )
            model += (expr1, f"arrived_and_completed_product_equals_demand_{n_r}_{t}_{p}")
            
            expr2 = (
                self.variables['arrived_and_completed_product'][t, p, n_r] >= 
                self.parameters['demand'].get((t, p, n_r), 0)
            )
            model += (expr2, f"arrived_and_completed_product_at_least_demand_{n_r}_{t}_{p}")

        # Total demand completion
        expr = (
            pulp.lpSum(
                self.variables['arrived_and_completed_product'][t, p, n_r] 
                for t in self.network_sets['PERIODS'] 
                for p in self.network_sets['PRODUCTS'] 
                for n_r in self.network_sets['RECEIVING_NODES']
            ) == self.variables['total_arrived_and_completed_product']
        )
        model += (expr, f"total_arrived_and_completed_product_equals_demand")

    def _build_flow_limit_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for flow limits"""
        # Add '@' to the sets for aggregation
        periods = list(self.network_sets['PERIODS']) + ['@']
        departing_nodes = list(self.network_sets['DEPARTING_NODES']) + ['@']
        receiving_nodes = list(self.network_sets['RECEIVING_NODES']) + ['@']
        modes = list(self.network_sets['MODES']) + ['@']
        measures = list(self.network_sets['MEASURES'])
        products = list(self.network_sets['PRODUCTS']) + ['@']
        nodegroups = list(self.network_sets['NODEGROUPS']) + ['@']

        if (self.parameters.get('flow_constraints_max') or 
            self.parameters.get('flow_constraints_min')):
            
            for o_index in departing_nodes:
                for g_index in nodegroups:
                    if (o_index == '@' or 
                        self.parameters['node_in_nodegroup'].get((o_index, g_index), 0) == 1):
                        
                        departing_nodes_list = (
                            self.network_sets['DEPARTING_NODES'] 
                            if o_index == '@' else [o_index]
                        )
                        
                        for d_index in receiving_nodes:
                            for g2_index in nodegroups:
                                if (d_index == '@' or 
                                    self.parameters['node_in_nodegroup'].get((d_index, g2_index), 0) == 1):
                                    
                                    receiving_nodes_list = (
                                        self.network_sets['RECEIVING_NODES'] 
                                        if d_index == '@' else [d_index]
                                    )
                                    
                                    for t_index in periods:
                                        periods_list = (
                                            self.network_sets['PERIODS'] 
                                            if t_index == '@' else [t_index]
                                        )
                                        
                                        for m_index in modes:
                                            modes_list = (
                                                self.network_sets['MODES'] 
                                                if m_index == '@' else [m_index]
                                            )
                                            
                                            # Minimum load constraints
                                            min_left_expr = self.parameters['transportation_constraints_min'].get(
                                                (t_index, o_index, d_index, m_index, 'load', 'count', g_index, g2_index), 0
                                            )
                                            min_right_expr = pulp.lpSum(
                                                self.variables['num_loads'][o,d,t,m]
                                                for o in departing_nodes_list
                                                for d in receiving_nodes_list
                                                for t in periods_list
                                                for m in modes_list
                                            )
                                            model += (
                                                min_left_expr <= min_right_expr,
                                                f"load_constraints_min_{t_index}_{o_index}_{d_index}_{m_index}_{g_index}_{g2_index}"
                                            )
                                            
                                            # Maximum load constraints with capacity expansion
                                            max_left_expr = (
                                                self.parameters['transportation_constraints_max'].get(
                                                    (t_index, o_index, d_index, m_index, 'load', 'count', g_index, g2_index),
                                                    self.big_m
                                                ) + 
                                                pulp.lpSum(
                                                    self.variables['use_transportation_capacity_option'][o,d,e,t] * 
                                                    self.parameters['transportation_expansion_capacity'].get(
                                                        (e, m_index, 'load', 'count'), 0
                                                    )
                                                    for o in (self.network_sets['DEPARTING_NODES'] if o_index=='@' else [o_index])
                                                    for d in (self.network_sets['RECEIVING_NODES'] if d_index=='@' else [d_index])
                                                    for t in (self.network_sets['PERIODS'] if t_index=='@' else [t_index])
                                                    for m in (self.network_sets['MODES'] if m_index=='@' else [m_index])
                                                    for p in self.network_sets['PRODUCTS']
                                                    for e in self.network_sets['T_CAPACITY_EXPANSIONS']
                                                )
                                            )
                                            model += (
                                                max_left_expr >= min_right_expr,
                                                f"load_constraints_max_{t_index}_{o_index}_{d_index}_{m_index}_{g_index}_{g2_index}"
                                            )

                                            # Add measure-specific constraints
                                            for u_index in measures:
                                                measures_list = (
                                                    self.network_sets['MEASURES'] 
                                                    if u_index == '@' else [u_index]
                                                )
                                                
                                                if (self.parameters.get('transportation_constraints_min') or 
                                                    self.parameters.get('transportation_constraints_max')):
                                                    
                                                    # Minimum transportation constraints
                                                    min_trans_left_expr = (
                                                        self.parameters['transportation_constraints_min'].get(
                                                            (t_index, o_index, d_index, m_index, 'unit', u_index, g_index, g2_index), 0
                                                        )
                                                    )
                                                    min_trans_right_expr = pulp.lpSum(
                                                        self.variables['departed_measures'][o,d,p,t,m,u]
                                                        for o in departing_nodes_list
                                                        for d in receiving_nodes_list
                                                        for t in periods_list
                                                        for m in modes_list
                                                        for p in self.network_sets['PRODUCTS']
                                                        for u in measures_list
                                                    )
                                                    model += (
                                                        min_trans_left_expr <= min_trans_right_expr,
                                                        f"transportation_constraints_min_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{g_index}_{g2_index}"
                                                    )
                                                    
                                                    # Maximum transportation constraints with capacity expansion
                                                    max_trans_left_expr = (
                                                        self.parameters['transportation_constraints_max'].get(
                                                            (t_index, o_index, d_index, m_index, 'unit', u_index, g_index, g2_index),
                                                            self.big_m
                                                        ) +
                                                        pulp.lpSum(
                                                            self.variables['use_transportation_capacity_option'][o,d,e,t] * 
                                                            self.parameters['transportation_expansion_capacity'].get(
                                                                (e, m_index, 'unit', u_index), 0
                                                            )
                                                            for o in (self.network_sets['DEPARTING_NODES'] if o_index=='@' else [o_index])
                                                            for d in (self.network_sets['RECEIVING_NODES'] if d_index=='@' else [d_index])
                                                            for t in (self.network_sets['PERIODS'] if t_index=='@' else [t_index])
                                                            for m in (self.network_sets['MODES'] if m_index=='@' else [m_index])
                                                            for p in self.network_sets['PRODUCTS']
                                                            for u in (self.network_sets['MEASURES'] if u_index=='@' else [u_index])
                                                            for e in self.network_sets['T_CAPACITY_EXPANSIONS']
                                                        )
                                                    )
                                                    model += (
                                                        max_trans_left_expr >= min_trans_right_expr,
                                                        f"transportation_constraints_max_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{g_index}_{g2_index}"
                                                    )

                                                # Add product-specific flow constraints
                                                for p_index in products:
                                                    if self.parameters['products_measures'].get((p_index, u_index), 'NA') != 'NA':
                                                        products_list = (
                                                            self.network_sets['PRODUCTS'] 
                                                            if p_index == '@' else [p_index]
                                                        )
                                                        
                                                        # Minimum flow constraints
                                                        min_flow_left_expr = (
                                                            self.parameters['flow_constraints_min'].get(
                                                                (o_index, d_index, p_index, t_index, m_index, 'unit', u_index, g_index, g2_index), 0
                                                            ) -
                                                            (self.big_m * (1 - self.variables['is_launched'][o_index, t_index])
                                                             if o_index != '@' and t_index != '@' else 0) -
                                                            (self.big_m * (1 - self.variables['is_launched'][d_index, t_index])
                                                             if d_index != '@' and t_index != '@' else 0)
                                                        )
                                                        min_flow_right_expr = pulp.lpSum(
                                                            self.variables['departed_product_by_mode'][o,d,p,t,m] *
                                                            self.parameters['products_measures'].get((p,u), self.big_m)
                                                            for o in departing_nodes_list
                                                            for d in receiving_nodes_list
                                                            for t in periods_list
                                                            for m in modes_list
                                                            for p in products_list
                                                            for u in measures_list
                                                        )
                                                        model += (
                                                            min_flow_left_expr <= min_flow_right_expr,
                                                            f"flow_constraints_min_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                        )
                                                        
                                                        # Maximum flow constraints
                                                        max_flow_left_expr = self.parameters['flow_constraints_max'].get(
                                                                (o_index, d_index, p_index, t_index, m_index, 'unit', u_index, g_index, g2_index),
                                                                self.big_m
                                                            )
                                                        max_flow_right_expr = pulp.lpSum(
                                                            self.variables['departed_product_by_mode'][o,d,p,t,m] *
                                                            self.parameters['products_measures'].get((p,u), 0)
                                                            for o in departing_nodes_list
                                                            for d in receiving_nodes_list
                                                            for t in periods_list
                                                            for m in modes_list
                                                            for p in products_list
                                                            for u in measures_list
                                                        )
                                                        model += (
                                                            max_flow_left_expr >= max_flow_right_expr,
                                                            f"flow_constraints_max_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                        )

        # Add connection constraints if specified
        if (self.parameters.get('flow_constraints_min_connections') or 
            self.parameters.get('flow_constraints_max_connections')):
            
            for o_index in departing_nodes:
                for g_index in nodegroups:
                    if o_index == '@' or self.parameters['node_in_nodegroup'].get((o_index, g_index), 0) == 1:
                        
                        if o_index == '@' and g_index != '@':
                            from_nodes = [
                                n for n in self.network_sets['DEPARTING_NODES'] 
                                if self.parameters['node_in_nodegroup'].get((n, g_index), 0) == 1
                            ]
                        else:
                            from_nodes = self.network_sets['DEPARTING_NODES']
                        
                        departing_nodes_list = from_nodes if o_index == '@' else [o_index]
                        
                        for d_index in receiving_nodes:
                            for g2_index in nodegroups:
                                if d_index == '@' or self.parameters['node_in_nodegroup'].get((d_index, g2_index), 0) == 1:
                                    
                                    if d_index == '@' and g2_index != '@':
                                        to_nodes = [
                                            n for n in self.network_sets['RECEIVING_NODES']
                                            if self.parameters['node_in_nodegroup'].get((n, g2_index), 0) == 1
                                        ]
                                    else:
                                        to_nodes = self.network_sets['RECEIVING_NODES']
                                    
                                    receiving_nodes_list = to_nodes if d_index == '@' else [d_index]
                                    
                                    for t_index in periods:
                                        periods_list = (
                                            self.network_sets['PERIODS'] 
                                            if t_index == '@' else [t_index]
                                        )
                                        
                                        for m_index in modes:
                                            for u_index in measures:
                                                for p_index in products:
                                                    # Minimum connections constraints
                                                    min_conn_left_expr = (
                                                        self.parameters['flow_constraints_min_connections'].get(
                                                            (o_index, d_index, p_index, t_index, m_index, 'unit', u_index, g_index, g2_index),
                                                            0
                                                        )
                                                    )
                                                    min_conn_right_expr = (
                                                        pulp.lpSum(
                                                            self.variables['is_destination_assigned_to_origin'][o,d,t]
                                                            for o in departing_nodes_list
                                                            for d in receiving_nodes_list
                                                            for t in periods_list
                                                        ) +
                                                        (self.big_m * (1 - self.variables['is_launched'][o_index, t_index])
                                                         if o_index != '@' and t_index != '@' else 0) +
                                                        (self.big_m * (1 - self.variables['is_launched'][d_index, t_index])
                                                         if d_index != '@' and t_index != '@' else 0)
                                                    )
                                                    model += (
                                                        min_conn_left_expr <= min_conn_right_expr,
                                                        f"flow_constraints_min_connections_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                    )
                                                    
                                                    # Maximum connections constraints
                                                    max_conn_left_expr = (
                                                        self.parameters['flow_constraints_max_connections'].get(
                                                            (o_index, d_index, p_index, t_index, m_index, 'unit', u_index, g_index, g2_index),
                                                            self.big_m
                                                        )
                                                    )
                                                    max_conn_right_expr = pulp.lpSum(
                                                        self.variables['is_destination_assigned_to_origin'][o,d,t]
                                                        for o in departing_nodes_list
                                                        for d in receiving_nodes_list
                                                        for t in periods_list
                                                    )
                                                    model += (
                                                        max_conn_left_expr >= max_conn_right_expr,
                                                        f"flow_constraints_max_connections_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                    )

    def _build_destination_assignment_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for destination assignments"""
        for o, d, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS']
        ):
            # Upper bound constraint
            expr1 = (
                self.variables['is_destination_assigned_to_origin'][o,d,t] <= 
                pulp.lpSum(
                    self.variables['departed_product'][o,d,p,t] * 9999 
                    for p in self.network_sets['PRODUCTS']
                )
            )
            model += (expr1, f"is_destination_assigned_{o}_{d}_{t}_1")
            
            # Lower bound constraint
            expr2 = (
                self.variables['is_destination_assigned_to_origin'][o,d,t] * 
                self.big_m >= 
                pulp.lpSum(
                    self.variables['departed_product'][o,d,p,t] 
                    for p in self.network_sets['PRODUCTS']
                )
            )
            model += (expr2, f"is_destination_assigned_{o}_{d}_{t}_2")
    
    def _build_mode_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints that aggregate flows across modes"""
        for n_d, n_r, t, p in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS']
        ):
            constraint_expr = pulp.lpSum(
                self.variables['departed_product_by_mode'][n_d, n_r, p, t, m] 
                for m in self.network_sets['MODES']
            )
            model += (
                self.variables['departed_product'][n_d, n_r, p, t] == constraint_expr,
                f"departed_product_mode_sum_{n_d}_{n_r}_{t}_{p}"
            )

    def _build_arrival_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to product arrivals"""
        for n_r, t, p in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS']
        ):
            expr = (
                self.variables['arrived_product'][n_r, p, t] == 
                pulp.lpSum(
                    self.variables['departed_product_by_mode'][n_d, n_r, p, t2, m] 
                    for n_d in self.network_sets['DEPARTING_NODES'] 
                    for m in self.network_sets['MODES'] 
                    for t2 in self.network_sets['PERIODS'] 
                    if int(t2) == int(t) - int(self.parameters['transport_periods'].get((n_d, n_r, m), 0))
                )
            )
            model += (expr, f"Arrived_Equals_Departed_Constraint_{n_r}_{t}_{p}")

    def _build_processing_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to product processing"""
        for n_r, t, p, g in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n_r, g), 0) == 1:
                if n_r not in self.network_sets['ORIGINS']:
                    if int(t) > 1:
                        expr = (
                            self.variables['processed_product'][n_r, p, t] + 
                            self.variables['ib_carried_over_demand'][n_r, p, t] <= 
                            self.variables['arrived_product'][n_r, p, t] + 
                            self.variables['ib_carried_over_demand'][n_r, p, str(int(t)-1)] - 
                            self.variables['dropped_demand'][n_r, p, t] - 
                            self.variables['arrived_and_completed_product'][t, p, n_r]
                        )
                    else:
                        expr = (
                            self.variables['processed_product'][n_r, p, t] + 
                            self.variables['ib_carried_over_demand'][n_r, p, t] <= 
                            self.variables['arrived_product'][n_r, p, t] - 
                            self.variables['dropped_demand'][n_r, p, t] - 
                            self.variables['arrived_and_completed_product'][t, p, n_r]
                        )
                else:
                    expr = (
                        pulp.lpSum(
                            self.variables['processed_product'][n_r, p, t2] 
                            for t2 in self.network_sets['PERIODS'] 
                            if int(t2) == int(t) - 
                               int(self.parameters['delay_periods'].get((t2, n_r, p, g), 0)) - 
                               int(self.parameters['capacity_consumption_periods'].get((t2, n_r, p, g), 0))
                        ) >= 
                        self.variables['arrived_and_completed_product'][t, p, n_r] - 
                        self.variables['dropped_demand'][n_r, p, t]
                    )
                model += (expr, f"Processed_Less_Than_Arrived_Constraint_{n_r}_{t}_{g}")

    def _build_departure_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to product departures"""
        for n_d, t, p, g in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n_d, g), 0) == 1:
                if n_d not in self.network_sets['ORIGINS']:
                    if int(t) > 1:
                        expr = (
                            pulp.lpSum(
                                self.variables['departed_product'][n_d, n_r, p, t] 
                                for n_r in self.network_sets['RECEIVING_NODES']
                            ) + 
                            self.variables['ob_carried_over_demand'][n_d, p, t] <= 
                            pulp.lpSum(
                                self.variables['processed_product'][n_d, p, t2] 
                                for t2 in self.network_sets['PERIODS'] 
                                if int(t2) == int(t) - 
                                   int(self.parameters['delay_periods'].get((t2, n_d, p), 0)) - 
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            ) + 
                            self.variables['ob_carried_over_demand'][n_d, p, str(int(t)-1)]
                        )
                    else:
                        expr = (
                            pulp.lpSum(
                                self.variables['departed_product'][n_d, n_r, p, t] 
                                for n_r in self.network_sets['RECEIVING_NODES']
                            ) + 
                            self.variables['ob_carried_over_demand'][n_d, p, t] <= 
                            pulp.lpSum(
                                self.variables['processed_product'][n_d, p, t2] 
                                for t2 in self.network_sets['PERIODS'] 
                                if int(t2) == int(t) - 
                                   int(self.parameters['delay_periods'].get((t2, n_d, p), 0)) - 
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            )
                        )
                model += (expr, f"Depart_Less_Than_Processed_Constraint_{n_d}_{t}_{p}_{g}")

    def _build_destination_demand_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to destination demand"""
        for t, p, d, g in product(
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['DESTINATIONS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((d, g), 0) == 1:
                if d not in self.network_sets['ORIGINS']:
                    if int(t) > 1:
                        expr = (
                            self.variables['arrived_and_completed_product'][t, p, d] <= 
                            self.variables['arrived_product'][d, p, t] - 
                            self.variables['dropped_demand'][d, p, t] - 
                            self.variables['ib_carried_over_demand'][d, p, t] - 
                            self.variables['processed_product'][d, p, t] + 
                            self.variables['ib_carried_over_demand'][d, p, str(int(t)-1)]
                        )
                    else:
                        expr = (
                            self.variables['arrived_and_completed_product'][t, p, d] <= 
                            self.variables['arrived_product'][d, p, t] - 
                            self.variables['dropped_demand'][d, p, t] - 
                            self.variables['ib_carried_over_demand'][d, p, t] - 
                            self.variables['processed_product'][d, p, t]
                        )
                else:
                    if int(t) > 1:
                        expr = (
                            self.variables['arrived_and_completed_product'][t, p, d] + 
                            self.variables['ob_carried_over_demand'][d, p, t] + 
                            pulp.lpSum(
                                self.variables['departed_product'][d, n_r, p, t] 
                                for n_r in self.network_sets['RECEIVING_NODES']
                            ) <= 
                            pulp.lpSum(
                                self.variables['processed_product'][d, p, t2] 
                                for t2 in self.network_sets['PERIODS'] 
                                if int(t2) == int(t) - 
                                   int(self.parameters['delay_periods'].get((t2, d, p, g), 0)) - 
                                   int(self.parameters['capacity_consumption_periods'].get((t2, d, p, g), 0))
                            ) + 
                            self.variables['ob_carried_over_demand'][d, p, str(int(t)-1)]
                        )
                    else:
                        expr = (
                            self.variables['arrived_and_completed_product'][t, p, d] + 
                            self.variables['ob_carried_over_demand'][d, p, t] + 
                            pulp.lpSum(
                                self.variables['departed_product'][d, n_r, p, t] 
                                for n_r in self.network_sets['RECEIVING_NODES']
                            ) <= 
                            pulp.lpSum(
                                self.variables['processed_product'][d, p, t2] 
                                for t2 in self.network_sets['PERIODS'] 
                                if int(t2) == int(t) - 
                                   int(self.parameters['delay_periods'].get((t2, d, p, g), 0)) - 
                                   int(self.parameters['capacity_consumption_periods'].get((t2, d, p, g), 0))
                            )
                        )
                model += (expr, f"minimum_destination_demand_processed_{t}_{p}_{d}_{g}")

    def _build_origin_demand_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to origin demand"""
        for t, p in product(
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS']
        ):
            expr = (
                pulp.lpSum(
                    self.variables['arrived_and_completed_product'][t, p, d] 
                    for d in self.network_sets['DESTINATIONS']
                ) <= 
                pulp.lpSum(
                    self.variables['processed_product'][o, p, t2] 
                    for o, t2 in product(
                        self.network_sets['ORIGINS'],
                        self.network_sets['PERIODS']
                    ) 
                    if int(t2) <= int(t)
                )
            )
            model += (expr, f"minimum_origin_demand_processed_{t}_{p}")