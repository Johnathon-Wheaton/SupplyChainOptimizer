# src/model_builder.py
from typing import Dict, Any, List, Tuple
import pulp
import logging
from datetime import datetime
from itertools import product

class ModelBuilder:
    """Handles construction of the complete optimization model."""
    
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.sets = data['sets']
        self.parameters = data['parameters']
        self.model = pulp.LpProblem(name="Supply_Chain_Optimization", sense=pulp.LpMinimize)
        self.variables = {}
        self.logger = logging.getLogger(__name__)
        self.BIG_M = 999999999

    def build_model(self) -> Dict[str, Any]:
        """
        Builds the complete optimization model.
        
        Returns:
            Dict containing model, variables, and other relevant information
        """
        try:
            start_time = datetime.now()
            self.logger.info("Starting model construction")

            # Create all variables
            self._create_flow_variables()
            self._create_capacity_variables()
            self._create_cost_variables()
            self._create_binary_variables()
            self._create_tracking_variables()
            
            # Add all constraints
            self._add_flow_constraints()
            self._add_capacity_constraints()
            self._add_demand_constraints()
            self._add_transportation_constraints()
            self._add_cost_constraints()
            self._add_age_constraints()
            
            # Set objective
            self._set_objective()

            build_time = (datetime.now() - start_time).seconds
            self.logger.info(f"Model construction completed in {build_time} seconds")
            
            return {
                'model': self.model,
                'variables': self.variables,
                'sets': self.sets,
                'parameters': self.parameters
            }
            
        except Exception as e:
            self.logger.error(f"Error building model: {str(e)}")
            raise

    def _create_flow_variables(self):
        """Creates all flow-related variables."""
        # Product flows
        self.variables['departed_product'] = pulp.LpVariable.dicts(
            "departed_product",
            ((n_d, n_r, p, t) 
             for n_d, n_r, p, t in product(
                 self.sets['DEPARTING_NODES'],
                 self.sets['RECEIVING_NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        # Mode-specific flows
        self.variables['departed_product_by_mode'] = pulp.LpVariable.dicts(
            "departed_product_by_mode",
            ((n_d, n_r, p, t, m) 
             for n_d, n_r, p, t, m in product(
                 self.sets['DEPARTING_NODES'],
                 self.sets['RECEIVING_NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS'],
                 self.sets['MODES']
             )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        # Processing quantities
        self.variables['processed_product'] = pulp.LpVariable.dicts(
            "processed_product",
            ((n, p, t) 
             for n, p, t in product(
                 self.sets['NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        # Inventory variables
        self.variables['inventory'] = pulp.LpVariable.dicts(
            "inventory",
            ((n, p, t) 
             for n, p, t in product(
                 self.sets['NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpInteger
        )

    def _create_capacity_variables(self):
        """Creates all capacity-related variables."""
        # Processing capacity
        self.variables['processing_capacity'] = pulp.LpVariable.dicts(
            "processing_capacity",
            ((n, c, t) 
             for n, c, t in product(
                 self.sets['NODES'],
                 self.sets['NODE_CAPACITY_TYPES'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Capacity expansions
        self.variables['capacity_expansion'] = pulp.LpVariable.dicts(
            "capacity_expansion",
            ((n, e, t) 
             for n, e, t in product(
                 self.sets['NODES'],
                 self.sets['P_CAPACITY_EXPANSIONS'],
                 self.sets['PERIODS']
             )),
            cat=pulp.LpBinary
        )

        # Carrying capacity
        self.variables['carrying_capacity'] = pulp.LpVariable.dicts(
            "carrying_capacity",
            ((n, e, t) 
             for n, e, t in product(
                 self.sets['NODES'],
                 self.sets['C_CAPACITY_EXPANSIONS'],
                 self.sets['PERIODS']
             )),
            cat=pulp.LpBinary
        )

    def _create_cost_variables(self):
        """Creates all cost-related variables."""
        # Transportation costs
        self.variables['transport_cost'] = pulp.LpVariable.dicts(
            "transport_cost",
            ((n_d, n_r, m, t) 
             for n_d, n_r, m, t in product(
                 self.sets['DEPARTING_NODES'],
                 self.sets['RECEIVING_NODES'],
                 self.sets['MODES'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Operating costs
        self.variables['operating_cost'] = pulp.LpVariable.dicts(
            "operating_cost",
            ((n, t) 
             for n, t in product(
                 self.sets['NODES'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Expansion costs
        self.variables['expansion_cost'] = pulp.LpVariable.dicts(
            "expansion_cost",
            ((n, t) 
             for n, t in product(
                 self.sets['NODES'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Total costs
        self.variables['total_cost'] = pulp.LpVariable(
            "total_cost",
            lowBound=0,
            cat=pulp.LpContinuous
        )

    def _create_binary_variables(self):
        """Creates all binary decision variables."""
        # Node activation
        self.variables['node_active'] = pulp.LpVariable.dicts(
            "node_active",
            ((n, t) 
             for n, t in product(
                 self.sets['NODES'],
                 self.sets['PERIODS']
             )),
            cat=pulp.LpBinary
        )

        # Route activation
        self.variables['route_active'] = pulp.LpVariable.dicts(
            "route_active",
            ((n_d, n_r, m, t) 
             for n_d, n_r, m, t in product(
                 self.sets['DEPARTING_NODES'],
                 self.sets['RECEIVING_NODES'],
                 self.sets['MODES'],
                 self.sets['PERIODS']
             )),
            cat=pulp.LpBinary
        )

    def _create_tracking_variables(self):
        """Creates variables for tracking metrics."""
        # Age tracking
        self.variables['product_age'] = pulp.LpVariable.dicts(
            "product_age",
            ((n, p, t, a) 
             for n, p, t, a in product(
                 self.sets['NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS'],
                 self.sets['AGES']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # KPI tracking
        self.variables['service_level'] = pulp.LpVariable.dicts(
            "service_level",
            self.sets['PERIODS'],
            lowBound=0,
            upBound=1,
            cat=pulp.LpContinuous
        )

    def _add_flow_constraints(self):
        """Adds all flow-related constraints."""
        try:
            # Flow conservation at nodes
            for n in self.sets['NODES']:
                for p in self.sets['PRODUCTS']:
                    for t in self.sets['PERIODS']:
                        # Inflow equals outflow plus inventory change
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
                        
                        # Previous period inventory
                        prev_inv = (
                            self.variables['inventory'][n, p, str(int(t)-1)]
                            if int(t) > 1
                            else 0
                        )
                        
                        self.model += (
                            inflow + prev_inv == 
                            outflow + 
                            self.variables['inventory'][n, p, t] +
                            self.variables['processed_product'][n, p, t],
                            f"flow_conservation_{n}_{p}_{t}"
                        )

            # Mode aggregation constraints
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
                
        except Exception as e:
            self.logger.error(f"Error adding flow constraints: {str(e)}")
            raise

    def _add_capacity_constraints(self):
        """Adds all capacity-related constraints."""
        try:
            # Processing capacity constraints
            for n, t, c in product(
                self.sets['NODES'],
                self.sets['PERIODS'],
                self.sets['NODE_CAPACITY_TYPES']
            ):
                total_usage = pulp.lpSum(
                    self.variables['processed_product'][n, p, t] *
                    self.parameters['product_capacity_consumption'][p, t, n, c]
                    for p in self.sets['PRODUCTS']
                )
                
                base_capacity = self.parameters['node_capacity'][t, n, c]
                expansion_capacity = pulp.lpSum(
                    self.variables['capacity_expansion'][n, e, t] *
                    self.parameters['expansion_capacity'][e, c]
                    for e in self.sets['P_CAPACITY_EXPANSIONS']
                )
                
                self.model += (
                    total_usage <= base_capacity + expansion_capacity,
                    f"processing_capacity_{n}_{t}_{c}"
                )

            # Storage capacity constraints
            for n, t in product(self.sets['NODES'], self.sets['PERIODS']):
                total_storage = pulp.lpSum(
                    self.variables['inventory'][n, p, t] *
                    self.parameters['storage_factor'][p]
                    for p in self.sets['PRODUCTS']
                )
                
                storage_capacity = (
                    self.parameters['base_storage_capacity'][n] +
                    pulp.lpSum(
                        self.variables['carrying_capacity'][n, e, t] *
                        self.parameters['storage_expansion'][e]
                        for e in self.sets['C_CAPACITY_EXPANSIONS']
                    )
                )
                
                self.model += (
                    total_storage <= storage_capacity,
                    f"storage_capacity_{n}_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding capacity constraints: {str(e)}")
            raise

    def _add_demand_constraints(self):
        """Adds demand satisfaction constraints."""
        try:
            for d, p, t in product(
                self.sets['DESTINATIONS'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                # Total arrivals must meet demand
                total_received = pulp.lpSum(
                    self.variables['departed_product'][n, d, p, t]
                    for n in self.sets['DEPARTING_NODES']
                )
                
                demand = self.parameters['demand'][t, p, d]
                
                self.model += (
                    total_received >= demand,
                    f"demand_satisfaction_{d}_{p}_{t}"
                )
                
        except Exception as e:
            self.logger.error(f"Error adding demand constraints: {str(e)}")
            raise

    def _add_transportation_constraints(self):
        """Adds transportation-related constraints."""
        try:
            # Mode capacity constraints
            for n_d, n_r, m, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['PERIODS']
            ):
                total_flow = pulp.lpSum(
                    self.variables['departed_product_by_mode'][n_d, n_r, p, t, m]
                    for p in self.sets['PRODUCTS']
                )
                
                mode_capacity = (
                    self.parameters['mode_capacity'][m] *
                    self.variables['route_active'][n_d, n_r, m, t]
                )
                
                self.model += (
                    total_flow <= mode_capacity,
                    f"mode_capacity_{n_d}_{n_r}_{m}_{t}"
                )

            # Distance constraints
            for n_d, n_r, m, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['PERIODS']
            ):
                if self.variables['route_active'][n_d, n_r, m, t].varValue > 0:
                    self.model += (
                        self.parameters['distance'][n_d, n_r] <=
                        self.parameters['max_distance'][m],
                        f"distance_limit_{n_d}_{n_r}_{m}_{t}"
                    )

            # Transit time constraints
            for n_d, n_r, m, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['PERIODS']
            ):
                if self.variables['route_active'][n_d, n_r, m, t].varValue > 0:
                    self.model += (
                        self.parameters['transit_time'][n_d, n_r, m] <=
                        self.parameters['max_transit_time'][t, m],
                        f"transit_time_limit_{n_d}_{n_r}_{m}_{t}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error adding transportation constraints: {str(e)}")
            raise

    def _add_cost_constraints(self):
        """Adds cost calculation constraints."""
        try:
            # Transportation costs
            for n_d, n_r, m, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['PERIODS']
            ):
                # Fixed costs
                fixed_cost = (
                    self.parameters['transport_cost_fixed'][n_d, n_r, m] *
                    self.variables['route_active'][n_d, n_r, m, t]
                )
                
                # Variable costs based on distance and volume
                distance = self.parameters['distance'][n_d, n_r]
                variable_cost = pulp.lpSum(
                    self.variables['departed_product_by_mode'][n_d, n_r, p, t, m] *
                    self.parameters['transport_cost_variable'][n_d, n_r, m, p] *
                    distance
                    for p in self.sets['PRODUCTS']
                )
                
                self.model += (
                    self.variables['transport_cost'][n_d, n_r, m, t] ==
                    fixed_cost + variable_cost,
                    f"transport_cost_{n_d}_{n_r}_{m}_{t}"
                )

            # Operating costs
            for n, t in product(self.sets['NODES'], self.sets['PERIODS']):
                # Fixed operating costs
                fixed_cost = (
                    self.parameters['operating_cost_fixed'][n] *
                    self.variables['node_active'][n, t]
                )
                
                # Variable operating costs
                variable_cost = pulp.lpSum(
                    self.variables['processed_product'][n, p, t] *
                    self.parameters['operating_cost_variable'][n, p]
                    for p in self.sets['PRODUCTS']
                )
                
                self.model += (
                    self.variables['operating_cost'][n, t] ==
                    fixed_cost + variable_cost,
                    f"operating_cost_{n}_{t}"
                )

            # Expansion costs
            for n, t in product(self.sets['NODES'], self.sets['PERIODS']):
                processing_expansion_cost = pulp.lpSum(
                    self.variables['capacity_expansion'][n, e, t] *
                    self.parameters['expansion_cost_p'][e]
                    for e in self.sets['P_CAPACITY_EXPANSIONS']
                )
                
                carrying_expansion_cost = pulp.lpSum(
                    self.variables['carrying_capacity'][n, e, t] *
                    self.parameters['expansion_cost_c'][e]
                    for e in self.sets['C_CAPACITY_EXPANSIONS']
                )
                
                self.model += (
                    self.variables['expansion_cost'][n, t] ==
                    processing_expansion_cost + carrying_expansion_cost,
                    f"expansion_cost_{n}_{t}"
                )

            # Total cost
            self.model += (
                self.variables['total_cost'] ==
                pulp.lpSum(self.variables['transport_cost'][n_d, n_r, m, t]
                          for n_d, n_r, m, t in product(
                              self.sets['DEPARTING_NODES'],
                              self.sets['RECEIVING_NODES'],
                              self.sets['MODES'],
                              self.sets['PERIODS']
                          )) +
                pulp.lpSum(self.variables['operating_cost'][n, t]
                          for n, t in product(
                              self.sets['NODES'],
                              self.sets['PERIODS']
                          )) +
                pulp.lpSum(self.variables['expansion_cost'][n, t]
                          for n, t in product(
                              self.sets['NODES'],
                              self.sets['PERIODS']
                          )),
                "total_cost_calculation"
            )
                
        except Exception as e:
            self.logger.error(f"Error adding cost constraints: {str(e)}")
            raise

    def _add_age_constraints(self):
        """Adds product age tracking and constraints."""
        try:
            # Age tracking constraints
            for n, p, t, a in product(
                self.sets['NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS'],
                self.sets['AGES']
            ):
                if int(t) > 1 and int(a) > 0:
                    # Previous period inventory aging
                    prev_age = str(int(a) - 1)
                    prev_period = str(int(t) - 1)
                    
                    self.model += (
                        self.variables['product_age'][n, p, t, a] ==
                        self.variables['product_age'][n, p, prev_period, prev_age] -
                        pulp.lpSum(
                            self.variables['departed_product'][n, n_r, p, t]
                            for n_r in self.sets['RECEIVING_NODES']
                        ),
                        f"age_tracking_{n}_{p}_{t}_{a}"
                    )

            # Age limits
            for n, p, t in product(
                self.sets['NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            ):
                if p in self.parameters['perishable_products']:
                    max_age = self.parameters['max_age'][p]
                    
                    self.model += (
                        pulp.lpSum(
                            self.variables['product_age'][n, p, t, a]
                            for a in self.sets['AGES']
                            if int(a) > max_age
                        ) == 0,
                        f"max_age_limit_{n}_{p}_{t}"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error adding age constraints: {str(e)}")
            raise

    def _set_objective(self):
        """Sets the optimization objective based on priorities."""
        try:
            objectives = self.parameters['objectives']
            
            if objectives['primary'] == 'MINIMIZE_COST':
                self.model += self.variables['total_cost'], "Primary_Objective"
                
            elif objectives['primary'] == 'MAXIMIZE_SERVICE_LEVEL':
                self.model += (
                    -1 * pulp.lpSum(
                        self.variables['service_level'][t]
                        for t in self.sets['PERIODS']
                    ),
                    "Primary_Objective"
                )
                
            # Add constraints for secondary objectives
            if 'secondary' in objectives:
                if objectives['secondary'] == 'MINIMIZE_TRANSIT_TIME':
                    max_transit = pulp.LpVariable(
                        "max_transit_time",
                        lowBound=0,
                        cat=pulp.LpContinuous
                    )
                    
                    # Constraint max transit time
                    for n_d, n_r, m, t in product(
                        self.sets['DEPARTING_NODES'],
                        self.sets['RECEIVING_NODES'],
                        self.sets['MODES'],
                        self.sets['PERIODS']
                    ):
                        if self.variables['route_active'][n_d, n_r, m, t].varValue > 0:
                            self.model += (
                                max_transit >= 
                                self.parameters['transit_time'][n_d, n_r, m],
                                f"max_transit_constraint_{n_d}_{n_r}_{m}_{t}"
                            )
                    
                    # Add to objective with weight
                    self.model += (
                        0.1 * max_transit,
                        "Secondary_Objective"
                    )
                    
        except Exception as e:
            self.logger.error(f"Error setting objective: {str(e)}")
            raise

    def solve_model(self, time_limit: int = 3600, gap: float = 0.01) -> Dict[str, Any]:
        """
        Solves the optimization model.
        
        Args:
            time_limit: Maximum solution time in seconds
            gap: Optimality gap tolerance
            
        Returns:
            Dictionary containing solution status and results
        """
        try:
            solver = pulp.PULP_CBC_CMD(
                timeLimit=time_limit,
                gapRel=gap,
                msg=True
            )
            
            status = self.model.solve(solver)
            
            results = {
                'status': pulp.LpStatus[status],
                'objective_value': pulp.value(self.model.objective),
                'solution_time': solver.solution_time,
                'variables': {
                    name: var.varValue
                    for name, var in self.model.variables().items()
                }
            }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error solving model: {str(e)}")
            raise
