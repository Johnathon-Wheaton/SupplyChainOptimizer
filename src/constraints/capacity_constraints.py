from itertools import product
from typing import Dict, Any
import pulp
import logging

class CapacityConstraintGenerator:
    """Handles generation of capacity-related constraints."""
    
    def __init__(self, model: pulp.LpProblem, sets: Dict[str, Any], 
                 params: Dict[str, Any], vars: Dict[str, Any]):
        self.model = model
        self.sets = sets
        self.params = params
        self.vars = vars
        self.logger = logging.getLogger(__name__)

    def add_node_capacity_constraints(self):
        """Adds node capacity constraints."""
        for node, period, cap_type in product(
            self.sets['NODES'],
            self.sets['PERIODS'],
            self.sets['NODE_CAPACITY_TYPES']
        ):
            total_usage = pulp.lpSum(
                self.vars['processed_product'][node, product, period] *
                self.params['capacity_consumption'][product, node, cap_type]
                for product in self.sets['PRODUCTS']
            )
            
            base_capacity = self.params['node_capacity'][period, node, cap_type]
            expansion_capacity = pulp.lpSum(
                self.vars['capacity_expansion'][node, exp, period] *
                self.params['expansion_size'][exp, cap_type]
                for exp in self.sets['CAPACITY_EXPANSIONS']
            )
            
            self.model += (
                total_usage <= base_capacity + expansion_capacity,
                f"node_capacity_{node}_{period}_{cap_type}"
            )

    def add_transportation_capacity_constraints(self):
        """Adds transportation capacity constraints."""
        for orig, dest, mode, period in product(
            self.sets['DEPARTING_NODES'],
            self.sets['RECEIVING_NODES'],
            self.sets['MODES'],
            self.sets['PERIODS']
        ):
            total_shipped = pulp.lpSum(
                self.vars['departed_product_by_mode'][orig, dest, product, period, mode]
                for product in self.sets['PRODUCTS']
            )
            
            capacity = self.params['transportation_capacity'][orig, dest, mode, period]
            
            self.model += (
                total_shipped <= capacity,
                f"transportation_capacity_{orig}_{dest}_{mode}_{period}"
            )
