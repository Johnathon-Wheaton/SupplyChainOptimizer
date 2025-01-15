from itertools import product
from typing import Dict, Any
import pulp
import logging

class VariableGenerator:
    """Handles creation of all optimization variables."""
    
    def __init__(self, sets: Dict[str, Any]):
        self.sets = sets
        self.logger = logging.getLogger(__name__)
        self.variables = {}

    def create_all_variables(self) -> Dict[str, Any]:
        """Creates all variables needed for the optimization model."""
        try:
            self._create_flow_variables()
            self._create_capacity_variables()
            self._create_cost_variables()
            self._create_binary_variables()
            
            return self.variables
            
        except Exception as e:
            self.logger.error(f"Error creating variables: {str(e)}")
            raise

    def _create_flow_variables(self):
        """Creates flow-related variables."""
        # Basic flow variables
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

        # Mode-specific flow variables
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

        # Processing variables
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

        # Age tracking variables
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

    def _create_capacity_variables(self):
        """Creates capacity-related variables."""
        # Processing capacity variables
        self.variables['processing_capacity'] = pulp.LpVariable.dicts(
            "processing_capacity",
            ((n, t, c) 
             for n, t, c in product(
                 self.sets['NODES'],
                 self.sets['PERIODS'],
                 self.sets['NODE_CAPACITY_TYPES']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Capacity expansion variables
        self.variables['capacity_expansion'] = pulp.LpVariable.dicts(
            "capacity_expansion",
            ((n, e, t) 
             for n, e, t in product(
                 self.sets['NODES'],
                 self.sets['CAPACITY_EXPANSIONS'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        # Utilization tracking
        self.variables['capacity_utilization'] = pulp.LpVariable.dicts(
            "capacity_utilization",
            ((n, t) 
             for n, t in product(
                 self.sets['NODES'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            upBound=1,
            cat=pulp.LpContinuous
        )

    def _create_cost_variables(self):
        """Creates cost-related variables."""
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

        # Inventory costs
        self.variables['inventory_cost'] = pulp.LpVariable.dicts(
            "inventory_cost",
            ((n, p, t) 
             for n, p, t in product(
                 self.sets['NODES'],
                 self.sets['PRODUCTS'],
                 self.sets['PERIODS']
             )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Total cost variables
        self.variables['total_cost'] = pulp.LpVariable(
            "total_cost",
            lowBound=0,
            cat=pulp.LpContinuous
        )

    def _create_binary_variables(self):
        """Creates binary decision variables."""
        # Node activation variables
        self.variables['node_active'] = pulp.LpVariable.dicts(
            "node_active",
            ((n, t) 
             for n, t in product(
                 self.sets['NODES'],
                 self.sets['PERIODS']
             )),
            cat=pulp.LpBinary
        )

        # Route activation variables
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