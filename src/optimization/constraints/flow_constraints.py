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