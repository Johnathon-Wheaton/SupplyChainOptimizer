from itertools import product
import pulp
from .base_constraint import BaseConstraint

class TransportationConstraints(BaseConstraint):
    def build(self, model: pulp.LpProblem) -> None:
        self._build_total_cost_constraints(model)
        self._build_max_transit_distance_constraints(model)
        self._build_num_loads_constraints(model)
        self._build_cost_calculation_constraints(model)
    
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