from itertools import product
import pulp
from datetime import datetime
import logging
from .base_constraint import BaseConstraint

class CostConstraints(BaseConstraint):
    """Handles cost-related constraints in the network"""
    
    def build(self, model: pulp.LpProblem) -> None:
        """Build all cost constraints"""
        # self._build_cost_constraints(model)
        self._build_carried_volume_cost_constraints(model)
        self._build_operating_cost_constraints(model)
        self._build_launch_constraints(model)
        self._build_assignment_and_movement_constraints(model)

    def _build_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to resource costs"""
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

    def _build_carried_volume_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to carried volume costs"""
        # Inbound carried volume costs
        for n, t, p, g, a in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['AGES']
        ):
            expr = (self.variables['ib_carried_volume_cost'][n, p, t, a] >= 
                   self.parameters['period_weight'].get(int(t), 1) * 
                   self.variables['ib_vol_carried_over_by_age'][n, p, t, a] * 
                   self.parameters['ib_carrying_cost'].get((t, p, n, g), 0))
            model += (expr, f"ib_carried_volume_cost_{n}_{p}_{t}_{g}_{a}")

        # Outbound carried volume costs
        for n, t, p, g, a in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['AGES']
        ):
            expr = (self.variables['ob_carried_volume_cost'][n, p, t, a] >= 
                   self.parameters['period_weight'].get(int(t), 1) * 
                   self.variables['ob_vol_carried_over_by_age'][n, p, t, a] * 
                   self.parameters['ob_carrying_cost'].get((t, p, n, g), 0))
            model += (expr, f"ob_carried_volume_cost_{n}_{p}_{t}_{g}_{a}")

        # Dropped volume costs
        for n, t, p, g, a in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['NODEGROUPS'],
            self.network_sets['AGES']
        ):
            expr = (self.variables['dropped_volume_cost'][n, p, t, a] >= 
                   self.parameters['period_weight'].get(int(t), 1) * 
                   self.variables['vol_dropped_by_age'][n, p, t, a] * 
                   self.parameters['dropping_cost'].get((t, p, n, g), 0))
            model += (expr, f"dropped_volume_cost_{n}_{p}_{t}_{g}_{a}")

        # Aggregation constraints by period
        self._build_period_aggregation_constraints(model)
        
        # Aggregation constraints by product
        self._build_product_aggregation_constraints(model)
        
        # Aggregation constraints by node
        self._build_node_aggregation_constraints(model)
        
        # Aggregation constraints by node and time
        self._build_node_time_aggregation_constraints(model)
        
        # Aggregation constraints by product and time
        self._build_product_time_aggregation_constraints(model)
        
        # Total cost constraints
        self._build_total_cost_constraints(model)

    def _build_operating_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to operating costs"""
        # Variable operating costs
        for o, p, t, g in product(
            self.network_sets['NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((o, g), 0) == 1:
                expr = (self.variables['variable_operating_costs'][o, p, t] == 
                       self.parameters['period_weight'].get(int(t), 1) * 
                       self.parameters['operating_costs_variable'].get((t, o, p, g), 0) * 
                       self.variables['processed_product'][o, p, t])
                model += (expr, f"variable_operating_costs_{o}_{p}_{t}_{g}")

        # Site operating constraints
        for o, t in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['is_site_operating'][o, t] * self.big_m >= 
                   pulp.lpSum(self.variables['processed_product'][o, p, t] 
                            for p in self.network_sets['PRODUCTS']))
            model += (expr, f"is_site_operating_constraint_{o}_{t}")

        # Fixed operating costs
        for o, t, g in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['NODEGROUPS']
        ):
            expr = (self.variables['fixed_operating_costs'][o, t] == 
                   self.parameters['period_weight'].get(int(t), 1) * 
                   self.parameters['operating_costs_fixed'].get((t, o, g), 0) * 
                   self.variables['is_site_operating'][o, t])
            model += (expr, f"fixed_operating_costs_{o}_{t}_{g}")

        # Total operating costs by node and period
        for o, t in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['operating_costs'][o, t] == 
                   self.variables['fixed_operating_costs'][o, t] + 
                   pulp.lpSum(self.variables['variable_operating_costs'][o, p, t] 
                            for p in self.network_sets['PRODUCTS']))
            model += (expr, f"operating_costs_{o}_{t}")

        # Operating costs by origin
        for o in self.network_sets['NODES']:
            expr = (self.variables['operating_costs_by_origin'][o] == 
                   pulp.lpSum(self.variables['operating_costs'][o, t] 
                            for t in self.network_sets['PERIODS']))
            model += (expr, f"operating_costs_by_origin_{o}")

        # Total operating costs by period
        for t in self.network_sets['PERIODS']:
            expr = (self.variables['total_operating_costs'][t] == 
                   pulp.lpSum(self.variables['operating_costs'][o, t] 
                            for o in self.network_sets['NODES']))
            model += (expr, f"total_operating_costs_{t}")

        # Grand total operating costs
        expr = (self.variables['grand_total_operating_costs'] == 
               pulp.lpSum(self.variables['total_operating_costs'][t] 
                         for t in self.network_sets['PERIODS']))
        model += (expr, "grand_total_operating_costs")

    def _build_period_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build period aggregation constraints"""
        for t in self.network_sets['PERIODS']:
            # Inbound carried volume costs
            expr = (self.variables['ib_carried_volume_cost_by_period'][t] == 
                   pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                            for n, p, a in product(
                                self.network_sets['RECEIVING_NODES'],
                                self.network_sets['PRODUCTS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ib_carried_volume_cost_by_period_{t}")

            # Outbound carried volume costs
            expr = (self.variables['ob_carried_volume_cost_by_period'][t] == 
                   pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                            for n, p, a in product(
                                self.network_sets['DEPARTING_NODES'],
                                self.network_sets['PRODUCTS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ob_carried_volume_cost_by_period_{t}")

            # Dropped volume costs
            expr = (self.variables['dropped_volume_cost_by_period'][t] == 
                   pulp.lpSum(self.variables['dropped_volume_cost'][n, p, t, a]
                            for n, p, a in product(
                                self.network_sets['NODES'],
                                self.network_sets['PRODUCTS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"dropped_volume_cost_by_period_{t}")

    def _build_product_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build product aggregation constraints"""
        for p in self.network_sets['PRODUCTS']:
            # Inbound carried volume costs
            expr = (self.variables['ib_carried_volume_cost_by_product'][p] == 
                   pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                            for n, t, a in product(
                                self.network_sets['RECEIVING_NODES'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ib_carried_volume_cost_by_product_{p}")

            # Outbound carried volume costs
            expr = (self.variables['ob_carried_volume_cost_by_product'][p] == 
                   pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                            for n, t, a in product(
                                self.network_sets['DEPARTING_NODES'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ob_carried_volume_cost_by_product_{p}")

            # Dropped volume costs
            expr = (self.variables['dropped_volume_cost_by_product'][p] == 
                   pulp.lpSum(self.variables['dropped_volume_cost'][n, p, t, a]
                            for n, t, a in product(
                                self.network_sets['NODES'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"dropped_volume_cost_by_product_{p}")

    def _build_node_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build node aggregation constraints"""
        # Receiving nodes
        for n in self.network_sets['RECEIVING_NODES']:
            expr = (self.variables['ib_carried_volume_cost_by_node'][n] == 
                   pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                            for p, t, a in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ib_carried_volume_cost_by_node_{n}")

        # Departing nodes
        for n in self.network_sets['DEPARTING_NODES']:
            expr = (self.variables['ob_carried_volume_cost_by_node'][n] == 
                   pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                            for p, t, a in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ob_carried_volume_cost_by_node_{n}")

        # All nodes
        for n in self.network_sets['NODES']:
            expr = (self.variables['dropped_volume_cost_by_node'][n] == 
                   pulp.lpSum(self.variables['dropped_volume_cost'][n, p, t, a]
                            for p, t, a in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['PERIODS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"dropped_volume_cost_by_node_{n}")

    def _build_node_time_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build node and time aggregation constraints"""
        # Receiving nodes
                # Receiving nodes
        for n, t in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['ib_carried_volume_cost_by_node_time'][n, t] == 
                   pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                            for p, a in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ib_carried_volume_cost_by_node_time_{n}_{t}")

        # Departing nodes
        for n, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['ob_carried_volume_cost_by_node_time'][n, t] == 
                   pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                            for p, a in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ob_carried_volume_cost_by_node_time_{n}_{t}")

        # Commented out constraints for dropped volume costs by node and time
        # for n, t in product(self.network_sets['NODES'], self.network_sets['PERIODS']):
        #     expr = (self.variables['dropped_volume_cost_by_node_time'][n,t] == 
        #            pulp.lpSum(self.variables['dropped_volume_cost'][n,p,t,a]
        #                     for p, a in product(
        #                         self.network_sets['PRODUCTS'],
        #                         self.network_sets['AGES']
        #                     )))
        #     model += (expr, f"dropped_volume_cost_by_node_time_{n}_{t}")

    def _build_product_time_aggregation_constraints(self, model: pulp.LpProblem) -> None:
        """Build product and time aggregation constraints"""
        for p, t in product(
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            # Inbound carried volume costs
            expr = (self.variables['ib_carried_volume_cost_by_product_time'][p, t] == 
                   pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                            for n, a in product(
                                self.network_sets['RECEIVING_NODES'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ib_carried_volume_cost_by_product_time_{p}_{t}")

            # Outbound carried volume costs
            expr = (self.variables['ob_carried_volume_cost_by_product_time'][p, t] == 
                   pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                            for n, a in product(
                                self.network_sets['DEPARTING_NODES'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"ob_carried_volume_cost_by_product_time_{p}_{t}")

            # Dropped volume costs
            expr = (self.variables['dropped_volume_cost_by_product_time'][p, t] == 
                   pulp.lpSum(self.variables['dropped_volume_cost'][n, p, t, a]
                            for n, a in product(
                                self.network_sets['NODES'],
                                self.network_sets['AGES']
                            )))
            model += (expr, f"dropped_volume_cost_by_product_time_{p}_{t}")

    def _build_total_cost_constraints(self, model: pulp.LpProblem) -> None:
        """Build total cost constraints"""
        # Total dropped volume cost
        expr = (self.variables['total_dropped_volume_cost'] == 
               pulp.lpSum(self.variables['dropped_volume_cost'][n, p, t, a]
                        for n, p, t, a in product(
                            self.network_sets['NODES'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['PERIODS'],
                            self.network_sets['AGES']
                        )))
        model += (expr, "total_dropped_volume_cost_constraint")

        # Total inbound carried volume cost
        expr = (self.variables['total_ib_carried_volume_cost'] == 
               pulp.lpSum(self.variables['ib_carried_volume_cost'][n, p, t, a]
                        for n, p, t, a in product(
                            self.network_sets['RECEIVING_NODES'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['PERIODS'],
                            self.network_sets['AGES']
                        )))
        model += (expr, "total_ib_carried_volume_cost_constraint")

        # Total outbound carried volume cost
        expr = (self.variables['total_ob_carried_volume_cost'] == 
               pulp.lpSum(self.variables['ob_carried_volume_cost'][n, p, t, a]
                        for n, p, t, a in product(
                            self.network_sets['DEPARTING_NODES'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['PERIODS'],
                            self.network_sets['AGES']
                        )))
        model += (expr, "total_ob_carried_volume_cost_constraint")

        # Grand total of all carried and dropped volume costs
        expr = (self.variables['grand_total_carried_and_dropped_volume_cost'] == 
               self.variables['total_dropped_volume_cost'] +
               self.variables['total_ib_carried_volume_cost'] +
               self.variables['total_ob_carried_volume_cost'])
        model += (expr, "grand_total_carried_and_dropped_volume_cost_constraint")
    
    def _build_launch_constraints(self, model: pulp.LpProblem) -> None:
        """Build launch and shutdown related constraints"""
        # Maximum launch count constraints
        for o in self.network_sets['NODES']:
            expr = (pulp.lpSum(self.variables['is_launched'][o, t] 
                            for t in self.network_sets['PERIODS']) <= 
                   self.parameters['max_launch_count'].get(o, self.big_m))
            model += (expr, f"is_launched_{o}_max")

        # Minimum launch count constraints
        for o in self.network_sets['NODES']:
            expr = (pulp.lpSum(self.variables['is_launched'][o, t] 
                            for t in self.network_sets['PERIODS']) >= 
                   self.parameters['min_launch_count'].get(o, self.big_m))
            model += (expr, f"is_launched_{o}_min")

        # Hard launch constraints
        for o, t in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS']
        ):
            expr = (self.variables['is_launched'][o, t] >= 
                   self.parameters['launch_hard_constraint'].get((o, t), 0))
            model += (expr, f"launch_hard_constraint_{o}_{t}")

        # Launch cost constraints
        for o, t, g in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['NODEGROUPS']
        ):
            expr = (self.variables['total_launch_cost'][o, t] >= 
                   self.variables['is_launched'][o, t] * 
                   self.parameters['launch_cost'].get((t, o, g), 0))
            model += (expr, f"total_launch_cost_{o}_{t}_{g}")

        # Launch costs by period
        for t in self.network_sets['PERIODS']:
            expr = (self.variables['launch_costs_by_period'][t] == 
                   pulp.lpSum(self.variables['total_launch_cost'][o, t] 
                            for o in self.network_sets['NODES']))
            model += (expr, f"launch_costs_by_period_{t}")

        # Grand total launch cost constraints
        expr = (self.variables['grand_total_launch_cost'] == 
               pulp.lpSum(self.variables['total_launch_cost'][o, t] 
                        for o, t in product(
                            self.network_sets['NODES'],
                            self.network_sets['PERIODS']
                        )))
        model += (expr, "grand_total_launch_cost")

        expr = (self.variables['grand_total_launch_cost'] <= 
               self.parameters['max_launch_cost'])
        model += (expr, "grand_total_launch_cost_2")

        # Launch and volume processing constraints
        for o, t in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS']
        ):
            # If node processes volume, it must have been launched at or before the same period
            expr = ((pulp.lpSum(self.variables['is_launched'][o, t2] 
                              for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) - 
                    pulp.lpSum(self.variables['is_shut_down'][o, t3] 
                              for t3 in self.network_sets['PERIODS'] if int(t3) <= int(t))) * 
                   self.big_m >= 
                   pulp.lpSum(self.variables['processed_product'][o, p, t] 
                            for p in self.network_sets['PRODUCTS']))
            model += (expr, f"launch_volume_{o}_{t}")

            # Cannot launch twice without shutting down
            expr = (pulp.lpSum(self.variables['is_launched'][o, t2] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) - 
                   pulp.lpSum(self.variables['is_shut_down'][o, t3] 
                             for t3 in self.network_sets['PERIODS'] if int(t3) <= int(t)) <= 1)
            model += (expr, f"cannot_launch_twice_constraint_{o}_{t}")

            # Cannot shut down twice constraint
            expr = (pulp.lpSum(self.variables['is_shut_down'][o, t3] 
                             for t3 in self.network_sets['PERIODS'] if int(t3) <= int(t)) <= 
                   pulp.lpSum(self.variables['is_launched'][o, t2] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)))
            model += (expr, f"cannot_shut_down_twice_constraint_{o}_{t}")

            # Minimum operating duration
            expr = (self.variables['is_shut_down'][o, t] <= 
                   1 - pulp.lpSum(self.variables['is_launched'][o, t2] 
                                 for t2 in self.network_sets['PERIODS'] 
                                 if int(t2) > int(t) - self.parameters['min_operating_duration'].get(o, 0) 
                                 if int(t2) <= int(t)))
            model += (expr, f"min_operating_duration_{o}_{t}")

            # Must shut down within max operating window after launch
            if int(t) - self.parameters['max_operating_duration'].get(o, self.big_m) > 0:
                expr = (pulp.lpSum(self.variables['is_shut_down'][o, t3] 
                                 for t3 in self.network_sets['PERIODS'] 
                                 if int(t3) > int(t) - self.parameters['max_shut_down_duration'].get(o, self.big_m) 
                                 if int(t3) <= int(t)) >= 
                       pulp.lpSum(self.variables['is_launched'][o, t2] 
                                 for t2 in self.network_sets['PERIODS'] 
                                 if int(t2) > int(t) - self.parameters['max_operating_duration'].get(o, self.big_m) 
                                 if int(t2) <= int(t)))
                model += (expr, f"max_operating_duration_{o}_{t}")

            # Minimum shutdown duration
            expr = (self.variables['is_launched'][o, t] <= 
                   1 - pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                                 for t2 in self.network_sets['PERIODS'] 
                                 if int(t2) > int(t) - self.parameters['min_shut_down_duration'].get(o, 0) 
                                 if int(t2) <= int(t)))
            model += (expr, f"min_shut_down_duration_{o}_{t}")

            # Maximum shutdown duration
            if int(t) - self.parameters['max_shut_down_duration'].get(o, self.big_m) > 0:
                expr = (pulp.lpSum(self.variables['is_launched'][o, t3] 
                                 for t3 in self.network_sets['PERIODS'] 
                                 if int(t3) > int(t) - self.parameters['max_shut_down_duration'].get(o, self.big_m) 
                                 if int(t3) <= int(t)) >= 
                       pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                                 for t2 in self.network_sets['PERIODS'] 
                                 if int(t2) > int(t) - self.parameters['max_shut_down_duration'].get(o, self.big_m) 
                                 if int(t2) <= int(t)))
                model += (expr, f"max_shut_down_duration_{o}_{t}")

            # Hard shutdown constraints
            expr = (self.variables['is_shut_down'][o, t] >= 
                   self.parameters['shut_down_hard_constraint'].get((o, t), 0))
            model += (expr, f"shut_down_hard_constraint_{o}_{t}")

            # Maximum shutdown count
            expr = (pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                             for t2 in self.network_sets['PERIODS']) <= 
                   self.parameters['max_shut_down_count'].get(o, self.big_m))
            model += (expr, f"is_shut_down_{o}_{t}_max")

            # Minimum shutdown count
            expr = (pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                             for t2 in self.network_sets['PERIODS']) <= 
                   self.parameters['min_shut_down_count'].get(o, self.big_m))
            model += (expr, f"is_shut_down_{o}_{t}_min")

            # Must shut down after launch
            expr = (self.variables['is_shut_down'][o, t] <= 
                   pulp.lpSum(self.variables['is_launched'][o, t2] 
                            for t2 in self.network_sets['PERIODS'] if int(t2) < int(t)))
            model += (expr, f"shut_down_after_launch_constraint_{o}_{t}")

            # Shutdown volume constraints
            expr = ((1 - pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                                  for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t))) * 
                   self.big_m >= 
                   pulp.lpSum(self.variables['processed_product'][o, p, t2] 
                            for p, t2 in product(
                                self.network_sets['PRODUCTS'],
                                self.network_sets['PERIODS']
                            ) if int(t2) >= int(t)))
            model += (expr, f"shut_down_volume_{o}_{t}")

            # Early shutdown constraints
            expr = (self.variables['is_shut_down'][o, t] <= 
                   1 - pulp.lpSum(self.variables['processed_product'][o, p, t2] 
                                for p, t2 in product(
                                    self.network_sets['PRODUCTS'],
                                    self.network_sets['PERIODS']
                                ) if int(t2) >= int(t)) / self.big_m)
            model += (expr, f"early_shut_down_2_{o}_{t}")

            # Site operating with shutdown constraints
            expr = (self.variables['is_site_operating'][o, t] <= 
                   pulp.lpSum(self.variables['is_launched'][o, t2] 
                            for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) - 
                   pulp.lpSum(self.variables['is_shut_down'][o, t2] 
                            for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)))
            model += (expr, f"is_site_operating_shut_down_constraint_{o}_{t}")

        # Node type constraints
        for o, t, nt in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['NODETYPES']
        ):
            # Maximum nodes of type
            expr = (pulp.lpSum(self.variables['is_launched'][o, t2] * 
                             self.parameters['node_type'][o, nt] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) - 
                   pulp.lpSum(self.variables['is_shut_down'][o, t2] * 
                             self.parameters['node_type'][o, nt] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) <= 
                   self.parameters['node_types_max'].get((t, nt), 0))
            model += (expr, f"is_shut_down_type_max_constraint_{o}_{t}_{nt}")

            # Minimum nodes of type
            expr = (pulp.lpSum(self.variables['is_launched'][o, t2] * 
                             self.parameters['node_type'][o, nt] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) - 
                   pulp.lpSum(self.variables['is_shut_down'][o, t2] * 
                             self.parameters['node_type'][o, nt] 
                             for t2 in self.network_sets['PERIODS'] if int(t2) <= int(t)) >= 
                   self.parameters['node_types_min'].get((t, nt), 0))
            model += (expr, f"is_shut_down_type_min_constraint_{o}_{t}_{nt}")

        # Shutdown cost constraints
        for o, t, g in product(
            self.network_sets['NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['NODEGROUPS']
        ):
            expr = (self.variables['total_shut_down_cost'][o, t] >= 
                   self.variables['is_shut_down'][o, t] * 
                   self.parameters['shut_down_cost'].get((t, o, g), 0))
            model += (expr, f"total_shut_down_cost_{o}_{t}_{g}")

        # Shutdown costs by period
        for t in self.network_sets['PERIODS']:
            expr = (self.variables['shut_down_costs_by_period'][t] == 
                   pulp.lpSum(self.variables['total_shut_down_cost'][o, t] 
                            for o in self.network_sets['NODES']))
            model += (expr, f"shut_down_costs_by_period_{t}")

        # Grand total shutdown cost
        expr = (self.variables['grand_total_shut_down_cost'] == 
               pulp.lpSum(self.variables['total_shut_down_cost'][o, t] 
                        for o, t in product(
                            self.network_sets['NODES'],
                            self.network_sets['PERIODS']
                        )))
        model += (expr, "grand_total_shut_down_cost")
    
    def _build_assignment_and_movement_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints related to product destination assignments and movements"""
        # Binary assignment constraints
        for o, t, p, d in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['RECEIVING_NODES']
        ):
            # Lower bound constraint
            expr = (self.variables['binary_product_destination_assignment'][o, t, p, d] * 
                   self.big_m >= 
                   self.variables['departed_product'][o, d, p, t])
            model += (expr, f"binary_assignment_lower_{o}_{t}_{p}_{d}")

            # Upper bound constraint
            expr = (self.variables['binary_product_destination_assignment'][o, t, p, d] <= 
                   self.variables['departed_product'][o, d, p, t])
            model += (expr, f"binary_assignment_upper_{o}_{t}_{p}_{d}")

            # Volume moved and destinations moved constraints for periods after first
            if int(t) > 1:
                # Volume moved constraint
                expr = (self.variables['volume_moved'][str(int(t)-1), t, p, o, d] >= 
                       self.variables['departed_product'][o, d, p, t] +
                       self.big_m * (
                           self.variables['binary_product_destination_assignment'][o, t, p, d] - 
                           self.variables['binary_product_destination_assignment'][o, str(int(t)-1), p, d] - 1
                       ))
                model += (expr, f"volume_moved_{o}_{t}_{p}_{d}")

                # Number of destinations moved constraint
                expr = (self.variables['num_destinations_moved'][str(int(t)-1), t, p, o, d] >= 
                       (self.variables['binary_product_destination_assignment'][o, t, p, d] - 
                        self.variables['binary_product_destination_assignment'][o, str(int(t)-1), p, d]))
                model += (expr, f"num_destinations_moved_{o}_{t}_{p}_{d}")

        # POP cost constraints
        if self.parameters['pop_cost_per_move'] or self.parameters['pop_cost_per_volume_moved']:
            for o, t, p, d, g, g2 in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['PRODUCTS'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['NODEGROUPS'],
                self.network_sets['NODEGROUPS']
            ):
                if int(t) > 1:
                    if (self.parameters['node_in_nodegroup'].get((o, g), 0) == 1 and 
                        self.parameters['node_in_nodegroup'].get((d, g2), 0) == 1):
                        # POP cost constraint
                        expr = (self.variables['pop_cost'][str(int(t)-1), t, p, o, d] == 
                               self.parameters['pop_cost_per_volume_moved'].get((str(int(t)-1), t, p, o, d, g, g2), 0) * 
                               self.variables['volume_moved'][str(int(t)-1), t, p, o, d] +
                               self.parameters['pop_cost_per_move'].get((str(int(t)-1), t, p, o, d, g, g2), 0) * 
                               (self.variables['binary_product_destination_assignment'][o, t, p, d] - 
                                self.variables['binary_product_destination_assignment'][o, str(int(t)-1), p, d]))
                        model += (expr, f"pop_cost_{o}_{t}_{p}_{d}_{g}_{g2}")

                        # Maximum destinations moved constraint
                        expr = (self.parameters['pop_max_destinations_moved'].get((str(int(t)-1), t, p, o, d, g, g2), 
                                                                                self.big_m) >= 
                               (self.variables['binary_product_destination_assignment'][o, t, p, d] - 
                                self.variables['binary_product_destination_assignment'][o, str(int(t)-1), p, d]))
                        model += (expr, f"pop_max_destinations_moved_{o}_{t}_{p}_{d}_{g}_{g2}")

        # Total volume moved constraint
        expr = (self.variables['total_volume_moved'] >= 
               pulp.lpSum(self.variables['volume_moved'][str(int(t)-1), t, p, o, d] 
                        for t, p, o, d in product(
                            self.network_sets['PERIODS'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['DEPARTING_NODES'],
                            self.network_sets['RECEIVING_NODES']
                        ) if int(t) > 1))
        model += (expr, "total_volume_moved_constraint")

        # Total number of destinations moved constraint
        expr = (self.variables['total_num_destinations_moved'] >= 
               pulp.lpSum(self.variables['num_destinations_moved'][str(int(t)-1), t, p, o, d] 
                        for t, p, o, d in product(
                            self.network_sets['PERIODS'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['DEPARTING_NODES'],
                            self.network_sets['RECEIVING_NODES']
                        ) if int(t) > 1))
        model += (expr, "total_num_destinations_moved_constraint")

        # Grand total POP cost constraint
        expr = (self.variables['grand_total_pop_cost'] == 
               pulp.lpSum(self.variables['pop_cost'][t1, t2, p, o, d] 
                        for o, t1, t2, p, d in product(
                            self.network_sets['DEPARTING_NODES'],
                            self.network_sets['PERIODS'],
                            self.network_sets['PERIODS'],
                            self.network_sets['PRODUCTS'],
                            self.network_sets['RECEIVING_NODES']
                        )))
        model += (expr, "grand_total_pop_cost_constraint")