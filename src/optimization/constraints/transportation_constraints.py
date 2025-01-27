from itertools import product
import pulp
from .base_constraint import BaseConstraint

class TransportationConstraints(BaseConstraint):
    def build(self, model: pulp.LpProblem) -> None:
        self._build_total_cost_constraints(model)
        self._build_max_transit_distance_constraints(model)
        self._build_num_loads_constraints(model)
        self._build_cost_calculation_constraints(model)
        self._build_shipping_assembly_constraints(model)
        self._build_departed_measures_constraints(model)
        self._build_transportation_capacity_option_constraints(model)
        self._build_distance_time_constraints(model)
    
    def _build_max_transit_distance_constraints(self, model: pulp.LpProblem) -> None:
        for o, t, d, p, m in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['MODES']
        ):
            expr = (
                self.variables['max_transit_distance'] >= 
                self.variables['binary_product_destination_assignment'][o, t, p, d] * 
                self.parameters['distance'].get((o, d, m), self.big_m)
            )
            model += (expr, f"max_transit_distance_constraint_{o}_{t}_{d}_{p}_{m}")
    
    def _build_num_loads_constraints(self, model: pulp.LpProblem) -> None:
        # Number of loads by group constraint
        for o, d, t, m, u, tg, g, g2 in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['MODES'],
            self.network_sets['MEASURES'],
            self.network_sets['TRANSPORTATION_GROUPS'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((o,g),0)==1 and self.parameters['node_in_nodegroup'].get((d,g2),0)==1:
                expr = (self.variables['num_loads_by_group'][o,d,t,m,tg] >= 
                    (pulp.lpSum(self.variables['departed_measures'][o,d,p,t,m,u] * 
                    self.parameters['transportation_group'].get((p,tg),0) for p in self.network_sets['PRODUCTS']) / 
                    self.parameters['load_capacity'].get((t,o,d,m,u,g,g2), self.big_m)))
                model += (expr, f"num_loads_by_group_{o}_{d}_{t}_{m}_{u}_{tg}_{g}_{g2}")

        # Total number of loads constraints
        for o, d, t, m in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['MODES']
        ):
            expr = (self.variables['num_loads'][o,d,t,m] == 
                   pulp.lpSum(self.variables['num_loads_by_group'][o,d,t,m,g] 
                            for g in self.network_sets['TRANSPORTATION_GROUPS']))
            model += (expr, f"od_num_loads_{o}_{d}_{t}_{m}")

        # OD number of loads constraints
        for o, d, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['od_num_loads'][o,d,t] == 
                   pulp.lpSum(self.parameters['period_weight'].get(int(t),1) * 
                            self.variables['num_loads'][o,d,t,m] 
                            for m in self.network_sets['MODES']))
            model += (expr, f"od_num_loads_{o}_{d}_{t}")

        # Mode number of loads constraints
        for m, t in product(self.network_sets['MODES'], self.network_sets['PERIODS']):
            expr = (self.variables['mode_num_loads'][m,t] == 
                   pulp.lpSum(self.parameters['period_weight'].get(int(t),1) * 
                            self.variables['num_loads'][o,d,t,m] 
                            for o, d in product(self.network_sets['DEPARTING_NODES'], 
                                              self.network_sets['RECEIVING_NODES'])))
            model += (expr, f"mode_num_loads_{m}_{t}")

        # Total OD number of loads
        for o, d in product(self.network_sets['DEPARTING_NODES'], self.network_sets['RECEIVING_NODES']):
            expr = (self.variables['total_od_num_loads'][o,d] == 
                   pulp.lpSum(self.variables['od_num_loads'][o,d,t] 
                            for t in self.network_sets['PERIODS']))
            model += (expr, f"total_od_num_loads_{o}_{d}")

        # Total mode number of loads
        for m in self.network_sets['MODES']:
            expr = (self.variables['total_mode_num_loads'][m] == 
                   pulp.lpSum(self.variables['mode_num_loads'][m,t] 
                            for t in self.network_sets['PERIODS']))
            model += (expr, f"total_mode_num_loads_{m}")

        # Total number of loads per period
        for t in self.network_sets['PERIODS']:
            expr = (self.variables['total_num_loads'][t] == 
                   pulp.lpSum(self.variables['mode_num_loads'][m,t] 
                            for m in self.network_sets['MODES']))
            model += (expr, f"total_num_loads_{t}")

    def _build_cost_calculation_constraints(self, model: pulp.LpProblem) -> None:
        has_distance_cost = (self.parameters['distance'] and 
                           self.parameters['transportation_cost_variable_distance'])
        has_time_cost = (self.parameters['transportation_cost_variable_time'] and 
                        self.parameters['transit_time'])
        
        if has_distance_cost or has_time_cost:
            for o, d, t, m, u, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['MEASURES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if self.parameters['node_in_nodegroup'].get((o,g),0)==1 and self.parameters['node_in_nodegroup'].get((d,g2),0)==1:
                    expr = (self.variables['variable_transportation_costs'][o,d,t,m,u] >= 
                           pulp.lpSum(self.parameters['period_weight'].get(int(t),1) * 
                                    self.variables['departed_measures'][o,d,p,t,m,u] * 
                                    (self.parameters['transportation_cost_variable_distance'].get((o,d,m,'unit',u,t,g,g2),
                                                                                               self.big_m) * 
                                     self.parameters['distance'].get((o,d,m),self.big_m) + 
                                     self.parameters['transportation_cost_variable_time'].get((o,d,m,'unit',u,t,g,g2),
                                                                                           self.big_m) * 
                                     self.parameters['transit_time'].get((o,d,m),self.big_m)) 
                                    for p in self.network_sets['PRODUCTS']))
                    model += (expr, f"variable_transportation_costs_{o}_{d}_{t}_{m}_{u}_{g}_{g2}")

        if self.parameters['transportation_cost_fixed']:
            for o, d, t, m, u, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['MEASURES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if self.parameters['node_in_nodegroup'].get((o,g),0)==1 and self.parameters['node_in_nodegroup'].get((d,g2),0)==1:
                    expr = (self.variables['fixed_transportation_costs'][o,d,t,m,u] >= 
                           pulp.lpSum(self.parameters['period_weight'].get(int(t),1) *
                                    self.variables['departed_measures'][o,d,p,t,m,u] * 
                                    self.parameters['transportation_cost_fixed'].get((o,d,m,'unit',u,t,g,g2),
                                                                                  self.big_m) 
                                    for p in self.network_sets['PRODUCTS']))
                    model += (expr, f"fixed_transportation_costs_{o}_{d}_{t}_{m}_{u}_{g}_{g2}")

        if has_distance_cost or has_time_cost or self.parameters['transportation_cost_fixed']:
            for o, d, t, m, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if self.parameters['node_in_nodegroup'].get((o,g),0)==1 and self.parameters['node_in_nodegroup'].get((d,g2),0)==1:
                    expr = (self.variables['transportation_costs'][o,d,t,m] >= 
                           (self.parameters['period_weight'].get(int(t),1) * 
                            self.variables['num_loads'][o,d,t,m] * 
                            (self.parameters['transportation_cost_variable_distance'].get((o,d,m,'load','count',t,g,g2),
                                                                                       self.big_m) * 
                             self.parameters['distance'].get((o,d,m),self.big_m) +
                             self.parameters['transportation_cost_variable_time'].get((o,d,m,'load','count',t,g,g2),
                                                                                   self.big_m) * 
                             self.parameters['transit_time'].get((o,d,m),self.big_m) +
                             self.parameters['transportation_cost_fixed'].get((o,d,m,'load','count',t,g,g2),
                                                                           self.big_m))) +
                           pulp.lpSum(self.variables['variable_transportation_costs'][o,d,t,m,u] + 
                                    self.variables['fixed_transportation_costs'][o,d,t,m,u] 
                                    for u in self.network_sets['MEASURES']))
                    model += (expr, f"transportation_costs_{o}_{d}_{t}_{m}_{g}_{g2}")

        if self.parameters['transportation_cost_minimum']:
            for o, d, t, m, p, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if self.parameters['node_in_nodegroup'].get((o,g),0)==1 and self.parameters['node_in_nodegroup'].get((d,g2),0)==1:
                    expr = (self.variables['transportation_costs'][o,d,t,m] >= 
                           pulp.lpSum(self.parameters['transportation_cost_minimum'].get((o,d,m,'unit',u,t,g,g2),
                                                                                      self.big_m) 
                                    for u in self.network_sets['MEASURES']) *
                           self.variables['binary_product_destination_assignment'][o,t,p,d] + 
                           self.parameters['transportation_cost_minimum'].get((o,d,m,'load','count',t,g,g2),
                                                                           self.big_m) *
                           self.variables['binary_product_destination_assignment'][o,t,p,d])
                    model += (expr, f"transportation_costs_minimum_{o}_{d}_{t}_{m}_{p}_{g}_{g2}")

    def _build_total_cost_constraints(self, model: pulp.LpProblem) -> None:
        # OD transportation costs
        for o, d, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['od_transportation_costs'][o,d,t] >= 
                   pulp.lpSum(self.variables['variable_transportation_costs'][o,d,t,m,u] + 
                            self.variables['fixed_transportation_costs'][o,d,t,m,u] 
                            for m, u in product(self.network_sets['MODES'], 
                                              self.network_sets['MEASURES'])))
            model += (expr, f"od_transportation_costs_{o}_{d}_{t}")
        
        # Mode transportation costs
        for m, t in product(self.network_sets['MODES'], self.network_sets['PERIODS']):
            expr = (self.variables['mode_transportation_costs'][t,m] >= 
                   pulp.lpSum(self.variables['variable_transportation_costs'][o,d,t,m,u] + 
                            self.variables['fixed_transportation_costs'][o,d,t,m,u] 
                            for o, d, u in product(self.network_sets['DEPARTING_NODES'],
                                                 self.network_sets['RECEIVING_NODES'],
                                                 self.network_sets['MEASURES'])))
            model += (expr, f"mode_transportation_costs_{t}_{m}")

        # Total OD transportation costs
        for o, d in product(self.network_sets['DEPARTING_NODES'], self.network_sets['RECEIVING_NODES']):
            expr = (self.variables['total_od_transportation_costs'][o,d] >= 
                   pulp.lpSum(self.variables['transportation_costs'][o,d,t,m] 
                            for t, m in product(self.network_sets['PERIODS'],
                                              self.network_sets['MODES'])))
            model += (expr, f"total_od_transportation_costs_{o}_{d}")

        # Total mode transportation costs
        for m in self.network_sets['MODES']:
            expr = (self.variables['total_mode_transportation_costs'][m] >= 
                   pulp.lpSum(self.variables['transportation_costs'][o,d,t,m] 
                            for o, d, t in product(self.network_sets['DEPARTING_NODES'],
                                                 self.network_sets['RECEIVING_NODES'],
                                                 self.network_sets['PERIODS'])))
            model += (expr, f"total_mode_transportation_costs_{m}")

        # Total time transportation costs
        for t in self.network_sets['PERIODS']:
            expr = (self.variables['total_time_transportation_costs'][t] >= 
                   pulp.lpSum(self.variables['transportation_costs'][o,d,t,m] 
                            for o, d, m in product(self.network_sets['DEPARTING_NODES'],
                                                 self.network_sets['RECEIVING_NODES'],
                                                 self.network_sets['MODES'])))
            model += (expr, f"total_time_transportation_costs_{t}")

        # Grand total transportation costs
        expr = (self.variables['grand_total_transportation_costs'] >= 
               pulp.lpSum(self.variables['total_time_transportation_costs'][t] 
                        for t in self.network_sets['PERIODS']))
        model += (expr, "grand_total_transportation_costs")
    
    def _build_shipping_assembly_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for assembly requirements in shipping"""
        for t, p1, p2, n_d, n_r, g_d, g_r, m in product(
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['MODES']
        ):
            if (self.parameters['node_in_nodegroup'].get((n_d,g_d),0)==1 and 
                self.parameters['node_in_nodegroup'].get((n_r,g_r),0)==1):
                if (self.parameters['shipping_assembly_p1_required'].get((n_d,n_r,g_d,g_r,p1,p2)) is not None and 
                    self.parameters['shipping_assembly_p2_required'].get((n_d,n_r,g_d,g_r,p1,p2)) is not None):
                    expr = (
                        self.variables['departed_product_by_mode'][n_d,n_r,p1,t,m] * 
                        self.parameters['shipping_assembly_p1_required'][n_d,n_r,g_d,g_r,p1,p2] == 
                        self.variables['departed_product_by_mode'][n_d,n_r,p2,t,m] * 
                        self.parameters['shipping_assembly_p2_required'][n_d,n_r,g_d,g_r,p1,p2]
                    )
                    model += (expr, f"shipping_volume_assembly_constraints_{n_d}_{n_r}_{t}_{p1}_{p2}_{g_d}_{g_r}_{m}")

    def _build_departed_measures_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for departed measures calculations"""
        for o, d, p, t, m, u in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['MODES'],
            self.network_sets['MEASURES']
        ):
            expr = (
                self.variables['departed_measures'][o, d, p, t, m, u] == 
                pulp.lpSum(
                    self.variables['departed_product_by_mode'][o,d,p,t,m] * 
                    self.parameters['products_measures'].get((p,u),0) 
                    for p in self.network_sets['PRODUCTS']
                )
            )
            model += (expr, f"DepartedMeasures_{o}_{d}_{p}_{t}_{m}_{u}")

    def _build_transportation_capacity_option_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for transportation capacity options"""
        # Minimum count constraints
        for t, o, d, e_t in product(
            self.network_sets['PERIODS'],
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['T_CAPACITY_EXPANSIONS']
        ):
            expr = (
                self.variables['use_transportation_capacity_option'][o,d,e_t,t] >= 
                self.parameters['transportation_expansion_min_count'].get((t,o,d,e_t),0)
            )
            model += (expr, f"TransportationCapacityOptionMinCount_{t}_{o}_{d}_{e_t}")

            # Maximum count constraints
            expr = (
                self.variables['use_transportation_capacity_option'][o,d,e_t,t] >= 
                self.parameters['transportation_expansion_max_count'].get((t,o,d,e_t),0)
            )
            model += (expr, f"TransportationCapacityOptionMaxCount_{t}_{o}_{d}_{e_t}")

            # Cost calculation
            expr = (
                self.variables['t_capacity_option_cost'][t,o,d,e_t] ==
                self.parameters['period_weight'].get(int(t),1) * 
                self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) +
                self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                pulp.lpSum(
                    self.parameters['transportation_expansion_persisting_cost'].get((t2,o,d,e_t),0) 
                    for t2 in self.network_sets['PERIODS'] 
                    if int(t2) >= int(t)
                )
            )
            model += (expr, f"TransportationCapacityOptionCost_{t}_{o}_{d}_{e_t}")

        # Cost by location type
        for o, d, e_t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['T_CAPACITY_EXPANSIONS']
        ):
            expr = (
                self.variables['t_capacity_option_cost_by_location_type'][o,d,e_t] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t),1) * 
                    self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                    self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                    for t in self.network_sets['PERIODS']
                )
            )
            model += (expr, f"TransportationCapacityOptionCostByLocationType_{o}_{d}_{e_t}")

        # Cost by period type
        for e_t, t in product(
            self.network_sets['T_CAPACITY_EXPANSIONS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                self.variables['t_capacity_option_cost_by_period_type'][e_t,t] ==
                self.parameters['period_weight'].get(int(t),1) * 
                pulp.lpSum(
                    self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                    self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                    for o, d in product(
                        self.network_sets['DEPARTING_NODES'],
                        self.network_sets['RECEIVING_NODES']
                    )
                )
            )
            model += (expr, f"TransportationCapacityOptionCostByPeriodType_{e_t}_{t}")

        # Cost by location
        for o, d in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES']
        ):
            expr = (
                self.variables['t_capacity_option_cost_by_location'][o,d] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t),1) * 
                    self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                    self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                    for t, e_t in product(
                        self.network_sets['PERIODS'],
                        self.network_sets['T_CAPACITY_EXPANSIONS']
                    )
                )
            )
            model += (expr, f"TransportationCapacityOptionCostByLocation_{o}_{d}")

        # Cost by period
        for t in self.network_sets['PERIODS']:
            expr = (
                self.variables['t_capacity_option_cost_by_period'][t] ==
                self.parameters['period_weight'].get(int(t),1) * 
                pulp.lpSum(
                    self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                    self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                    for o, d, e_t in product(
                        self.network_sets['DEPARTING_NODES'],
                        self.network_sets['RECEIVING_NODES'],
                        self.network_sets['T_CAPACITY_EXPANSIONS']
                    )
                )
            )
            model += (expr, f"TransportationCapacityOptionCostByPeriod_{t}")

        # Cost by type
        for e_t in self.network_sets['T_CAPACITY_EXPANSIONS']:
            expr = (
                self.variables['t_capacity_option_cost_by_type'][e_t] ==
                pulp.lpSum(
                    self.parameters['period_weight'].get(int(t),1) * 
                    self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                    self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                    for o, d, t in product(
                        self.network_sets['DEPARTING_NODES'],
                        self.network_sets['RECEIVING_NODES'],
                        self.network_sets['PERIODS']
                    )
                )
            )
            model += (expr, f"TransportationCapacityOptionCostByType_{e_t}")

        # Grand total capacity option cost
        expr = (
            self.variables['grand_total_t_capacity_option'] ==
            pulp.lpSum(
                self.parameters['period_weight'].get(int(t),1) * 
                self.variables['use_transportation_capacity_option'][o,d,e_t,t] * 
                self.parameters['transportation_expansion_cost'].get((t,o,d,e_t),0) 
                for o, d, t, e_t in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES'],
                    self.network_sets['PERIODS'],
                    self.network_sets['T_CAPACITY_EXPANSIONS']
                )
            )
        )
        model += (expr, "GrandTotalTransportationCapacityOption")

    def _build_distance_time_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for distance and transit time limits"""
        # Distance constraints
        if self.parameters.get('distance') and self.parameters.get('max_distance'):
            for o, d, t, m, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if (self.parameters['node_in_nodegroup'].get((o,g),0)==1 and 
                    self.parameters['node_in_nodegroup'].get((d,g2),0)==1):
                    expr = (
                        self.variables['is_destination_assigned_to_origin'][o,d,t] * 
                        self.parameters['distance'].get((o,d,m), self.big_m) <= 
                        self.parameters['max_distance'].get((o,t,m,g,d,g2), self.big_m)
                    )
                    model += (expr, f"distance_{o}_{d}_{t}_{m}_{g}_{d}_{g2}")

        # Transit time constraints
        if self.parameters.get('transit_time') and self.parameters.get('max_transit_time'):
            for n_d, n_r, t, m, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if (self.parameters['node_in_nodegroup'].get((n_d,g),0)==1 and 
                    self.parameters['node_in_nodegroup'].get((n_r,g2),0)==1):
                    if (self.parameters['transit_time'].get((n_d,n_r,m),0) > 
                        self.parameters['max_transit_time'].get((n_d,t,m,g,n_r,g2), self.big_m)):
                        expr = (
                            pulp.lpSum(
                                self.variables['departed_product_by_mode'][n_d,n_r,p,t,m] 
                                for p in self.network_sets['PRODUCTS']
                            ) == 0
                        )
                        model += (expr, f"transit_time_{n_d}_{n_r}_{t}_{m}_{g}_{n_r}_{g2}")