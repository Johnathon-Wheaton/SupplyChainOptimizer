from itertools import product
import pulp
from .base_constraint import BaseConstraint

class AgeConstraints(BaseConstraint):
    """Handles age-related constraints in the network"""

    def build(self, model: pulp.LpProblem) -> None:
        """Build age constraints"""
        self._build_age_receiving_constraints(model)
        self._build_age_volume_constraints(model)
        self._build_age_processing_constraints(model)
        self._build_age_departure_constraints(model)
        self._build_age_limit_constraints(model)
        self._build_age_violation_constraints(model)
        self._build_max_age_constraints(model)
        self._build_age_limit_constraints(model)

    def _build_age_receiving_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for receiving volumes by age"""
        for n_r, p, t, a in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES']
        ):
            expr = (
                self.variables['vol_arrived_by_age'][n_r, p, t, a] == 
                pulp.lpSum(
                    self.variables['vol_departed_by_age'][n_d, n_r, p, t2, a, m]
                    for n_d in self.network_sets['DEPARTING_NODES']
                    for m in self.network_sets['MODES']
                    for t2 in self.network_sets['PERIODS']
                    if int(t2) == int(t) - int(self.parameters['transport_periods'].get((n_d, n_r, m), 0))
                )
            )
            model += (expr, f"Age_receiving_departure_equality_constraint_{n_r}_{p}_{t}_{a}")

        for n_r, p, t in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['vol_arrived_by_age'][n_r, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['arrived_product'][n_r, p, t]
            )
            model += (expr, f"Age_receiving_equals_arrived_volume_constraint_{n_r}_{p}_{t}")

    def _build_age_volume_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for volume tracking by age"""
        # Process volume constraints
        for n, p, t in product(
            self.network_sets['NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['vol_processed_by_age'][n, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['processed_product'][n, p, t]
            )
            model += (expr, f"Age_processed_equals_processed_volume_constraint_{n}_{p}_{t}")

        # Dropped volume constraints
        for n, p, t in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['vol_dropped_by_age'][n, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['dropped_demand'][n, p, t]
            )
            model += (expr, f"Age_dropped_equals_dropped_volume_constraint_{n}_{p}_{t}")

    def _build_age_demand_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for age-related demand volumes"""
        # Demand equals completed product constraint
        for n, p, t in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['demand_by_age'][n, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['arrived_and_completed_product'][t, p, n]
            )
            model += (expr, f"Age_demand_equals_demand_volume_constraint_{n}_{p}_{t}")

        # Departed volume by mode constraint
        for n_d, n_r, p, t, m in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['MODES']
        ):
            expr = (
                pulp.lpSum(self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m] 
                          for a in self.network_sets['AGES']) == 
                self.variables['departed_product_by_mode'][n_d, n_r, p, t, m]
            )
            model += (expr, f"Age_departing_equals_departed_volume_constraint_{n_d}_{n_r}_{p}_{t}")

        # Inbound carried over volume constraint
        for n_r, p, t in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['ib_vol_carried_over_by_age'][n_r, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['ib_carried_over_demand'][n_r, p, t]
            )
            model += (expr, f"Age_ib_carried_over_equals_ib_carried_over_constraint_{n_r}_{p}_{t}")

        # Outbound carried over volume constraint
        for n_d, p, t in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS']
        ):
            expr = (
                pulp.lpSum(self.variables['ob_vol_carried_over_by_age'][n_d, p, t, a] 
                          for a in self.network_sets['AGES']) == 
                self.variables['ob_carried_over_demand'][n_d, p, t]
            )
            model += (expr, f"Age_ob_carried_over_equals_ob_carried_over_constraint_{n_d}_{p}_{t}")
                
    def _build_age_processing_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for processing volumes by age"""
        for n, p, t, a, g in product(
            self.network_sets['RECEIVING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n, g), 0) == 1:
                if n not in self.network_sets['ORIGINS']:
                    if int(t) > 1 and int(a) > 0:
                        expr = (
                            self.variables['vol_processed_by_age'][n, p, t, a] <= 
                            self.variables['vol_arrived_by_age'][n, p, t, a] +
                            self.variables['ib_vol_carried_over_by_age'][n, p, str(int(t)-1), str(int(a)-1)] -
                            self.variables['vol_dropped_by_age'][n, p, t, a] -
                            self.variables['demand_by_age'][n, p, t, a] -
                            self.variables['ib_vol_carried_over_by_age'][n, p, t, a]
                        )
                    else:
                        expr = (
                            self.variables['vol_processed_by_age'][n, p, t, a] <=
                            self.variables['vol_arrived_by_age'][n, p, t, a] -
                            self.variables['vol_dropped_by_age'][n, p, t, a] -
                            self.variables['demand_by_age'][n, p, t, a] -
                            self.variables['ib_vol_carried_over_by_age'][n, p, t, a]
                        )
                else:
                    expr = (
                        pulp.lpSum(
                            self.variables['vol_processed_by_age'][n, p, t, a]
                            for t2 in self.network_sets['PERIODS']
                            if int(t2) == int(t) - int(self.parameters['delay_periods'].get((t2, n, p, g), 0)) -
                               int(self.parameters['capacity_consumption_periods'].get((t2, n, p, g), 0))
                        ) >= (
                            self.variables['demand_by_age'][n, p, t, a] -
                            self.variables['vol_dropped_by_age'][n, p, t, a]
                        )
                    )
                model += (expr, f"processed_by_age_less_than_arrived_carried_over_constraint_{n}_{p}_{t}_{a}_{g}")

    def _build_age_departure_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for departing volumes by age"""
        for n_d, p, t, a, g in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES'],
            self.network_sets['NODEGROUPS']
        ):
            if self.parameters['node_in_nodegroup'].get((n_d, g), 0) == 1:
                if n_d not in self.network_sets['ORIGINS']:
                    if int(t) > 1 and int(a) > 0:
                        expr = (
                            pulp.lpSum(
                                self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m]
                                for n_r in self.network_sets['RECEIVING_NODES']
                                for m in self.network_sets['MODES']
                            ) + self.variables['ob_vol_carried_over_by_age'][n_d, p, t, a] <=
                            self.variables['ob_vol_carried_over_by_age'][n_d, p, str(int(t)-1), str(int(a)-1)] +
                            pulp.lpSum(
                                self.variables['vol_processed_by_age'][n_d, p, t2, a]
                                for t2 in self.network_sets['PERIODS']
                                if int(t2) == int(t) - int(self.parameters['delay_periods'].get((t2, n_d, p, g), 0)) -
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            )
                        )
                    else:
                        expr = (
                            pulp.lpSum(
                                self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m]
                                for n_r in self.network_sets['RECEIVING_NODES']
                                for m in self.network_sets['MODES']
                            ) + self.variables['ob_vol_carried_over_by_age'][n_d, p, t, a] <=
                            pulp.lpSum(
                                self.variables['vol_processed_by_age'][n_d, p, t2, a]
                                for t2 in self.network_sets['PERIODS']
                                if int(t2) == int(t) - int(self.parameters['delay_periods'].get((t2, n_d, p, g), 0)) -
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            )
                        )
                else:
                    if int(t) > 1 and int(a) > 0:
                        expr = (
                            pulp.lpSum(
                                self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m]
                                for n_r in self.network_sets['RECEIVING_NODES']
                                for m in self.network_sets['MODES']
                            ) + self.variables['ob_vol_carried_over_by_age'][n_d, p, t, a] <=
                            self.variables['ob_vol_carried_over_by_age'][n_d, p, str(int(t)-1), str(int(a)-1)] +
                            pulp.lpSum(
                                self.variables['vol_processed_by_age'][n_d, p, t2, a]
                                for t2 in self.network_sets['PERIODS']
                                if int(t2) == int(t) - int(self.parameters['delay_periods'].get((t2, n_d, p, g), 0)) -
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            ) - self.variables['demand_by_age'][n_d, p, t, a]
                        )
                    else:
                        expr = (
                            pulp.lpSum(
                                self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m]
                                for n_r in self.network_sets['RECEIVING_NODES']
                                for m in self.network_sets['MODES']
                            ) + self.variables['ob_vol_carried_over_by_age'][n_d, p, t, a] <=
                            pulp.lpSum(
                                self.variables['vol_processed_by_age'][n_d, p, t2, a]
                                for t2 in self.network_sets['PERIODS']
                                if int(t2) == int(t) - int(self.parameters['delay_periods'].get((t2, n_d, p, g), 0)) -
                                   int(self.parameters['capacity_consumption_periods'].get((t2, n_d, p, g), 0))
                            ) - self.variables['demand_by_age'][n_d, p, t, a]
                        )
                model += (expr, f"departed_by_age_less_than_processed_carried_over_constraint_{n_d}_{p}_{t}_{a}_{g}")

    def _build_age_limit_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for age limits and FIFO rules"""
        # FIFO constraints for processing
        for n, p, t, a in product(
            self.network_sets['NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES']
        ):
            expr = (
                self.variables['vol_processed_by_age'][n, p, t, a] <=
                self.variables['processed_product'][n, p, t] -
                pulp.lpSum(
                    self.variables['vol_processed_by_age'][n, p, t, a2]
                    for a2 in self.network_sets['AGES']
                    if int(a2) > int(a)
                )
            )
            model += (expr, f"processed_by_age_fifo_constraint_{n}_{p}_{t}_{a}")

        # FIFO constraints for dropping
        for n, p, t, a in product(
            self.network_sets['NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES']
        ):
            expr = (
                self.variables['vol_dropped_by_age'][n, p, t, a] <=
                self.variables['dropped_demand'][n, p, t] -
                pulp.lpSum(
                    self.variables['vol_dropped_by_age'][n, p, t, a2]
                    for a2 in self.network_sets['AGES']
                    if int(a2) > int(a)
                )
            )
            model += (expr, f"dropped_by_age_fifo_constraint_{n}_{p}_{t}_{a}")

    def _build_age_violation_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for age limit violations and associated costs"""
        if self.parameters.get('max_vol_by_age'):
            for d, p, t, a, g in product(
                self.network_sets['DESTINATIONS'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS'],
                self.network_sets['AGES'],
                self.network_sets['NODEGROUPS']
            ):
                if self.parameters['node_in_nodegroup'].get((d, g), 0) == 1:
                    expr = (
                        self.variables['demand_by_age'][d, p, t, a] <=
                        self.parameters['max_vol_by_age'].get((t, p, d, a, g), self.big_m)
                    )
                    model += (expr, f"max_volume_by_age_constraint_{d}_{p}_{t}_{a}_{g}")

                    if self.parameters.get('age_constraint_violation_cost'):
                        expr = (
                            (self.variables['demand_by_age'][d, p, t, a] -
                             self.parameters['max_vol_by_age'].get((t, p, d, a, g), self.big_m)) *
                            self.parameters['age_constraint_violation_cost'].get((t, p, d, a, g), self.big_m) <=
                            self.variables['age_violation_cost'][d, p, t, a]
                        )
                        model += (expr, f"max_volume_by_age_violation_cost_constraint_{d}_{p}_{t}_{a}_{g}")

        # Total age violation cost constraint
        expr = (
            self.variables['grand_total_age_violation_cost'] ==
            pulp.lpSum(
                self.variables['age_violation_cost'][d, p, t, a]
                for d in self.network_sets['DESTINATIONS']
                for p in self.network_sets['PRODUCTS']
                for t in self.network_sets['PERIODS']
                for a in self.network_sets['AGES']
            )
        )
        model += (expr, f"grand_total_age_violation_cost_constraint")

    def _build_max_age_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for maximum age tracking"""

        # Maximum age constraints
        for a in self.network_sets['AGES']:
            expr = (
                self.variables['max_age'] >= 
                self.variables['is_age_received'][a] * int(a)
            )
            model += (expr, f"max_age_constraint_{a}")

            # Is age received constraint
            expr = (
                pulp.lpSum(
                    self.variables['demand_by_age'][d, p, t, a]
                    for d in self.network_sets['DESTINATIONS']
                    for p in self.network_sets['PRODUCTS']
                    for t in self.network_sets['PERIODS']
                ) <= self.variables['is_age_received'][a] * self.big_m
            )
            model += (expr, f"binary_is_age_received_constraint_{a}")
    
    def _build_fifo_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for maximum age tracking"""

        # Maximum age constraints
        for a in self.network_sets['AGES']:
            expr = (
                self.variables['max_age'] >= 
                self.variables['is_age_received'][a] * int(a)
            )
            model += (expr, f"max_age_constraint_{a}")

            # Is age received constraint
            expr = (
                pulp.lpSum(
                    self.variables['demand_by_age'][d, p, t, a]
                    for d in self.network_sets['DESTINATIONS']
                    for p in self.network_sets['PRODUCTS']
                    for t in self.network_sets['PERIODS']
                ) <= self.variables['is_age_received'][a] * self.big_m
            )
            model += (expr, f"binary_is_age_received_constraint_{a}")
    
    def _build_age_limit_constraints(self, model: pulp.LpProblem) -> None:
        """Build constraints for age limits and FIFO rules"""
        # FIFO constraints for departed volumes
        for n_d, p, t, a, m in product(
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['PRODUCTS'],
            self.network_sets['PERIODS'],
            self.network_sets['AGES'],
            self.network_sets['MODES']
        ):
            expr = (
                pulp.lpSum(
                    self.variables['vol_departed_by_age'][n_d, n_r, p, t, a, m] 
                    for n_r in self.network_sets['RECEIVING_NODES']
                ) <= 
                pulp.lpSum(
                    self.variables['departed_product_by_mode'][n_d, n_r, p, t, m] 
                    for n_r in self.network_sets['RECEIVING_NODES']
                ) - 
                pulp.lpSum(
                    self.variables['vol_departed_by_age'][n_d, n_r, p, t, a2, m] 
                    for n_r in self.network_sets['RECEIVING_NODES'] 
                    for a2 in self.network_sets['AGES'] 
                    if int(a2) > int(a)
                )
            )
            model += (expr, f"departed_by_age_fifo_constraint_{n_d}_{p}_{t}_{a}_{m}")

            