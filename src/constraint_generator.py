# src/constraint_generator.py
from itertools import product
import pulp
from typing import Dict, Any, List, Tuple
import logging
from datetime import datetime

class ConstraintGenerator:
    """Handles generation of optimization model constraints."""
    
    def __init__(self, model: pulp.LpProblem, sets: Dict[str, List], 
                 parameters: Dict[str, Any], variables: Dict[str, Any]):
        self.model = model
        self.sets = sets
        self.parameters = parameters
        self.variables = variables
        self.logger = logging.getLogger(__name__)
        self.BIG_M = 999999999

    def add_all_constraints(self):
        """Adds all constraint types to the model."""
        try:
            start_time = datetime.now()
            
            self.add_flow_constraints()
            self.add_capacity_constraints()
            self.add_demand_constraints()
            self.add_transportation_constraints()
            self.add_inventory_constraints()
            self.add_age_constraints()
            self.add_cost_calculation_constraints()
            self.add_service_level_constraints()
            self.add_node_activation_constraints()
            
            self.logger.info(f"All constraints added in {(datetime.now() - start_time).seconds} seconds")
            
        except Exception as e:
            self.logger.error(f"Error adding constraints: {str(e)}")
            raise

    def add_flow_constraints(self):
        """Adds flow-related constraints."""
        try:
            # Flow conservation at nodes
            for n, p, t in product(self.sets['NODES'], 
                                 self.sets['PRODUCTS'], 
                                 self.sets['PERIODS']):
                # Inflow equals outflow plus processing and inventory
                inflow = pulp.lpSum(
                    self.variables['departed_product'][n_d, n, p, t]
                    for n_d in self.sets['DEPARTING_NODES']
                    if n_d != n
                )
                
                outflow = pulp.lpSum(
                    self.variables['departed_product'][n, n_r, p, t]
                    for n_r in self.sets['RECEIVING_NODES']
                    if n_r != n
                )
                
                inv_change = (
                    self.variables['inventory'][n, p, t] -
                    self.variables['inventory'][n, p, str(int(t)-1)]
                    if int(t) > 1
                    else self.variables['inventory'][n, p, t]
                )
                
                self.model += (
                    inflow == outflow + 
                    self.variables['processed_product'][n, p, t] +
                    inv_change,
                    f"flow_conservation_{n}_{p}_{t}"
                )
                
            # Mode-specific flow constraints
            for n_d, n_r, p, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                self.model += (
                    self.variables['departed_product'][n_d, n_r, p, t] ==
                    pulp.lpSum(
                        self.variables['departed_product_by_mode'][n_d, n_r, p, t, m]
                        for m in self.sets['MODES']
                    ),
                    f"mode_aggregation_{n_d}_{n_r}_{p}_{t}"
                )
                
            # Flow balance at origins
            for o, p, t in product(
                self.sets['ORIGINS'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                self.model += (
                    self.variables['processed_product'][o, p, t] >=
                    pulp.lpSum(
                        self.variables['departed_product'][o, n_r, p, t]
                        for n_r in self.sets['RECEIVING_NODES']
                    ),
                    f"origin_flow_balance_{o}_{p}_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding flow constraints: {str(e)}")
            raise

    def add_capacity_constraints(self):
        """Adds capacity-related constraints."""
        try:
            # Processing capacity
            for n, t, c in product(
                self.sets['NODES'],
                self.sets['PERIODS'],
                self.sets['NODE_CHILD_CAPACITY_TYPES']
            ):
                capacity_usage = pulp.lpSum(
                    self.variables['processed_product'][n, p, t] *
                    self.parameters['product_capacity_consumption'][p, t, n, c]
                    for p in self.sets['PRODUCTS']
                )
                
                base_capacity = self.parameters['node_capacity'][t, n, c]
                expanded_capacity = pulp.lpSum(
                    self.variables['use_processing_capacity_option'][n, e, t] *
                    self.parameters['processing_expansion_capacity'][t, n, e, c]
                    for e in self.sets['P_CAPACITY_EXPANSIONS']
                )
                
                self.model += (
                    capacity_usage <= base_capacity + expanded_capacity,
                    f"processing_capacity_{n}_{t}_{c}"
                )
                
            # Storage capacity
            for n, t, m in product(
                self.sets['NODES'],
                self.sets['PERIODS'],
                self.sets['MEASURES']
            ):
                # Inbound storage
                inbound_storage = pulp.lpSum(
                    self.variables['inventory'][n, p, t] *
                    self.parameters['products_measures'][p, m]
                    for p in self.sets['PRODUCTS']
                )
                
                inbound_capacity = (
                    self.parameters['ib_carrying_capacity'][t, n, m] +
                    pulp.lpSum(
                        self.variables['use_carrying_capacity_option'][n, e, t] *
                        self.parameters['ib_carrying_expansion_capacity'][t, n, e]
                        for e in self.sets['C_CAPACITY_EXPANSIONS']
                    )
                )
                
                self.model += (
                    inbound_storage <= inbound_capacity,
                    f"inbound_storage_capacity_{n}_{t}_{m}"
                )
                
                # Outbound storage
                outbound_storage = pulp.lpSum(
                    self.variables['ob_carried_over_demand'][n, p, t] *
                    self.parameters['products_measures'][p, m]
                    for p in self.sets['PRODUCTS']
                )
                
                outbound_capacity = (
                    self.parameters['ob_carrying_capacity'][t, n, m] +
                    pulp.lpSum(
                        self.variables['use_carrying_capacity_option'][n, e, t] *
                        self.parameters['ob_carrying_expansion_capacity'][t, n, e]
                        for e in self.sets['C_CAPACITY_EXPANSIONS']
                    )
                )
                
                self.model += (
                    outbound_storage <= outbound_capacity,
                    f"outbound_storage_capacity_{n}_{t}_{m}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding capacity constraints: {str(e)}")
            raise

    def add_demand_constraints(self):
        """Adds demand satisfaction constraints."""
        try:
            for n_r, p, t in product(
                self.sets['RECEIVING_NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                # Arrived and completed product equals demand minus dropped demand
                self.model += (
                    self.variables['arrived_and_completed_product'][t, p, n_r] ==
                    self.parameters['demand'][t, p, n_r] -
                    self.variables['dropped_demand'][n_r, p, t],
                    f"demand_satisfaction_{n_r}_{p}_{t}"
                )
                
            # Total arrived and completed product
            self.model += (
                self.variables['total_arrived_and_completed_product'] ==
                pulp.lpSum(
                    self.variables['arrived_and_completed_product'][t, p, n_r]
                    for t, p, n_r in product(
                        self.sets['PERIODS'],
                        self.sets['PRODUCTS'],
                        self.sets['RECEIVING_NODES']
                    )
                ),
                "total_arrived_and_completed_product"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding demand constraints: {str(e)}")
            raise

    def add_transportation_constraints(self):
        """Adds transportation-related constraints."""
        try:
            # Load capacity constraints
            for t, n_d, n_r, m, u in product(
                self.sets['PERIODS'],
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['MEASURES']
            ):
                # Total load must not exceed capacity
                load = pulp.lpSum(
                    self.variables['departed_measures'][n_d, n_r, p, t, m, u]
                    for p in self.sets['PRODUCTS']
                )
                
                capacity = self.parameters['load_capacity'][t, n_d, n_r, m, u]
                
                self.model += (
                    load <= capacity,
                    f"load_capacity_{t}_{n_d}_{n_r}_{m}_{u}"
                )
                
            # Transportation group constraints
            for n_d, n_r, t, m, g in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['PERIODS'],
                self.sets['MODES'],
                self.sets['TRANSPORTATION_GROUPS']
            ):
                # Number of loads by group
                self.model += (
                    self.variables['num_loads_by_group'][n_d, n_r, t, m, g] >=
                    pulp.lpSum(
                        self.variables['departed_measures'][n_d, n_r, p, t, m, u] *
                        self.parameters['transportation_group'][p, g]
                        for p, u in product(
                            self.sets['PRODUCTS'],
                            self.sets['MEASURES']
                        )
                    ) / self.parameters['load_capacity'][t, n_d, n_r, m, u],
                    f"loads_by_group_{n_d}_{n_r}_{t}_{m}_{g}"
                )
                
            # Distance and transit time constraints
            for n_d, t, m in product(
                self.sets['DEPARTING_NODES'],
                self.sets['PERIODS'],
                self.sets['MODES']
            ):
                # Maximum distance
                self.model += (
                    pulp.lpSum(
                        self.variables['binary_product_destination_assignment'][n_d, t, p, n_r] *
                        self.parameters['distance'][n_d, n_r, m]
                        for p, n_r in product(
                            self.sets['PRODUCTS'],
                            self.sets['RECEIVING_NODES']
                        )
                    ) <= self.parameters['max_distance'][n_d, t, m],
                    f"max_distance_{n_d}_{t}_{m}"
                )
                
                # Maximum transit time
                self.model += (
                    pulp.lpSum(
                        self.variables['binary_product_destination_assignment'][n_d, t, p, n_r] *
                        self.parameters['transit_time'][n_d, n_r, m]
                        for p, n_r in product(
                            self.sets['PRODUCTS'],
                            self.sets['RECEIVING_NODES']
                        )
                    ) <= self.parameters['max_transit_time'][n_d, t, m],
                    f"max_transit_time_{n_d}_{t}_{m}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding transportation constraints: {str(e)}")
            raise

    def add_inventory_constraints(self):
        """Adds inventory-related constraints."""
        try:
            # Inbound carried over demand
            for n_r, p, t in product(
                self.sets['RECEIVING_NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                self.model += (
                    self.variables['ib_carried_over_demand'][n_r, p, t] <=
                    self.parameters['ib_max_carried'][t, p, n_r],
                    f"max_inbound_carried_{n_r}_{p}_{t}"
                )
                
            # Outbound carried over demand
            for n_d, p, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                self.model += (
                    self.variables['ob_carried_over_demand'][n_d, p, t] <=
                    self.parameters['ob_max_carried'][t, p, n_d],
                    f"max_outbound_carried_{n_d}_{p}_{t}"
                )
                
            # Maximum dropped demand
            for n, p, t in product(
                self.sets['NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                self.model += (
                    self.variables['dropped_demand'][n, p, t] <=
                    self.parameters['max_dropped'][t, p, n],
                    f"max_dropped_{n}_{p}_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding inventory constraints: {str(e)}")
            raise

    def add_age_constraints(self):
        """Adds age tracking and constraints."""
        try:
            # Age tracking for each product
            for n_r, p, t, a in product(
                self.sets['RECEIVING_NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS'],
                self.sets['AGES']
            ):
                # Maximum volume by age
                self.model += (
                    self.variables['demand_by_age'][n_r, p, t, a] <=
                    self.parameters['max_vol_by_age'][t, p, n_r, a],
                    f"max_volume_by_age_{n_r}_{p}_{t}_{a}"
                )
                
                # Age violation cost calculation
                self.model += (
                    (self.variables['demand_by_age'][n_r, p, t, a] -
                     self.parameters['max_vol_by_age'][t, p, n_r, a]) *
                    self.parameters['age_constraint_violation_cost'][t, p, n_r, a] <=
                    self.variables['age_violation_cost'][n_r, p, t, a],
                    f"age_violation_cost_{n_r}_{p}_{t}_{a}"
                )
                
            # Total age violation cost
            self.model += (
                self.variables['grand_total_age_violation_cost'] ==
                pulp.lpSum(
                    self.variables['age_violation_cost'][n_r, p, t, a]
                    for n_r, p, t, a in product(
                        self.sets['RECEIVING_NODES'],
                        self.sets['PRODUCTS'],
                        self.sets['PERIODS'],
                        self.sets['AGES']
                    )
                ),
                "total_age_violation_cost"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding age constraints: {str(e)}")
            raise

    def add_cost_calculation_constraints(self):
        """Adds cost calculation constraints."""
        try:
            # Transportation costs
            total_transport_cost = pulp.lpSum(
                self.variables['transport_cost'][n_d, n_r, m, t]
                for n_d, n_r, m, t in product(
                    self.sets['DEPARTING_NODES'],
                    self.sets['RECEIVING_NODES'],
                    self.sets['MODES'],
                    self.sets['PERIODS']
                )
            )
            
            # Operating costs
            total_operating_cost = pulp.lpSum(
                self.variables['operating_cost'][n, t]
                for n, t in product(
                    self.sets['NODES'],
                    self.sets['PERIODS']
                )
            )
            
            # Capacity expansion costs
            total_capacity_cost = (
                pulp.lpSum(
                    self.variables['c_capacity_option_cost'][t, n, e]
                    for t, n, e in product(
                        self.sets['PERIODS'],
                        self.sets['NODES'],
                        self.sets['C_CAPACITY_EXPANSIONS']
                    )
                ) +
                pulp.lpSum(
                    self.variables['p_capacity_option_cost'][t, n, e]
                    for t, n, e in product(
                        self.sets['PERIODS'],
                        self.sets['NODES'],
                        self.sets['P_CAPACITY_EXPANSIONS']
                    )
                )
            )
            
            # Carried and dropped volume costs
            total_volume_cost = (
                pulp.lpSum(
                    self.variables['dropped_volume_cost'][n, p, t]
                    for n, p, t in product(
                        self.sets['NODES'],
                        self.sets['PRODUCTS'],
                        self.sets['PERIODS']
                    )
                ) +
                pulp.lpSum(
                    self.variables['ib_carried_volume_cost'][n, p, t]
                    for n, p, t in product(
                        self.sets['RECEIVING_NODES'],
                        self.sets['PRODUCTS'],
                        self.sets['PERIODS']
                    )
                ) +
                pulp.lpSum(
                    self.variables['ob_carried_volume_cost'][n, p, t]
                    for n, p, t in product(
                        self.sets['DEPARTING_NODES'],
                        self.sets['PRODUCTS'],
                        self.sets['PERIODS']
                    )
                )
            )
            
            # Launch costs
            total_launch_cost = pulp.lpSum(
                self.variables['total_launch_cost'][o, t]
                for o, t in product(
                    self.sets['NODES'],
                    self.sets['PERIODS']
                )
            )
            
            # Plan-over-plan costs
            total_pop_cost = pulp.lpSum(
                self.variables['pop_cost'][t1, t2, p, o, d]
                for t1, t2, p, o, d in product(
                    self.sets['PERIODS'],
                    self.sets['PERIODS'],
                    self.sets['PRODUCTS'],
                    self.sets['DEPARTING_NODES'],
                    self.sets['RECEIVING_NODES']
                )
                if int(t2) > int(t1)
            )
            
            # Grand total cost constraint
            self.model += (
                self.variables['grand_total_transportation_costs'] == total_transport_cost,
                "total_transport_cost_calculation"
            )
            self.model += (
                self.variables['grand_total_operating_costs'] == total_operating_cost,
                "total_operating_cost_calculation"
            )
            self.model += (
                self.variables['grand_total_capacity_option'] == total_capacity_cost,
                "total_capacity_cost_calculation"
            )
            self.model += (
                self.variables['grand_total_carried_and_dropped_volume_cost'] == total_volume_cost,
                "total_volume_cost_calculation"
            )
            self.model += (
                self.variables['grand_total_launch_cost'] == total_launch_cost,
                "total_launch_cost_calculation"
            )
            self.model += (
                self.variables['grand_total_pop_cost'] == total_pop_cost,
                "total_pop_cost_calculation"
            )
            
        except Exception as e:
            self.logger.error(f"Error adding cost calculation constraints: {str(e)}")
            raise

    def add_service_level_constraints(self):
        """Adds service level calculation constraints."""
        try:
            for t in self.sets['PERIODS']:
                # Calculate service level as (demand - dropped) / demand
                total_demand = pulp.lpSum(
                    self.parameters['demand'][t, p, d]
                    for p, d in product(
                        self.sets['PRODUCTS'],
                        self.sets['DESTINATIONS']
                    )
                )
                
                total_dropped = pulp.lpSum(
                    self.variables['dropped_demand'][d, p, t]
                    for p, d in product(
                        self.sets['PRODUCTS'],
                        self.sets['DESTINATIONS']
                    )
                )
                
                self.model += (
                    self.variables['service_level'][t] == 
                    (total_demand - total_dropped) / total_demand,
                    f"service_level_calculation_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding service level constraints: {str(e)}")
            raise

    def add_node_activation_constraints(self):
        """Adds node activation and launch constraints."""
        try:
            # Node activation based on processing
            for n, t in product(self.sets['NODES'], self.sets['PERIODS']):
                self.model += (
                    pulp.lpSum(
                        self.variables['processed_product'][n, p, t]
                        for p in self.sets['PRODUCTS']
                    ) <= self.BIG_M * self.variables['node_active'][n, t],
                    f"node_activation_{n}_{t}"
                )
                
            # Node launch constraints
            for n in self.sets['NODES']:
                # Can only launch once
                self.model += (
                    pulp.lpSum(
                        self.variables['is_launched'][n, t]
                        for t in self.sets['PERIODS']
                    ) <= 1,
                    f"single_launch_{n}"
                )
                
                # Must launch to process
                for t in self.sets['PERIODS']:
                    self.model += (
                        self.variables['node_active'][n, t] <= 
                        pulp.lpSum(
                            self.variables['is_launched'][n, t2]
                            for t2 in self.sets['PERIODS']
                            if int(t2) <= int(t)
                        ),
                        f"launch_before_active_{n}_{t}"
                    )
                    
            # Node type constraints
            for nt, t in product(self.sets['NODETYPES'], self.sets['PERIODS']):
                # Minimum number of nodes per type
                self.model += (
                    pulp.lpSum(
                        self.variables['node_active'][n, t] *
                        self.parameters['node_type'][n, nt]
                        for n in self.sets['NODES']
                    ) >= self.parameters['node_types_min'][t, nt],
                    f"min_nodes_type_{nt}_{t}"
                )
                
                # Maximum number of nodes per type
                self.model += (
                    pulp.lpSum(
                        self.variables['node_active'][n, t] *
                        self.parameters['node_type'][n, nt]
                        for n in self.sets['NODES']
                    ) <= self.parameters['node_types_max'][t, nt],
                    f"max_nodes_type_{nt}_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding node activation constraints: {str(e)}")
            raise
