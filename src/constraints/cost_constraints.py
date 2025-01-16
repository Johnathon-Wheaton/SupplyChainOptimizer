from itertools import product
from typing import Dict, Any
import pulp
import logging

class CostConstraintGenerator:
    """Handles generation of cost-related constraints."""
    
    def __init__(self, model: pulp.LpProblem, sets: Dict[str, Any], 
                 params: Dict[str, Any], vars: Dict[str, Any]):
        self.model = model
        self.sets = sets
        self.params = params
        self.vars = vars
        self.logger = logging.getLogger(__name__)

    def add_transportation_cost_constraints(self):
        """Adds transportation cost calculation constraints."""
        for orig, dest, mode, period in product(
            self.sets['DEPARTING_NODES'],
            self.sets['RECEIVING_NODES'],
            self.sets['MODES'],
            self.sets['PERIODS']
        ):
            fixed_cost = self.params['fixed_transport_cost'][orig, dest, mode]
            distance = self.params['distance'][orig, dest]
            variable_cost = self.params['variable_transport_cost'][orig, dest, mode]
            
            total_cost = (
                self.vars['transport_fixed_cost'][orig, dest, mode, period] +
                pulp.lpSum(
                    self.vars['departed_product_by_mode'][orig, dest, product, period, mode] *
                    variable_cost * distance
                    for product in self.sets['PRODUCTS']
                )
            )
            
            self.model += (
                self.vars['transport_cost'][orig, dest, mode, period] == total_cost,
                f"transport_cost_{orig}_{dest}_{mode}_{period}"
            )

    def add_operating_cost_constraints(self):
        """Adds operating cost calculation constraints."""
        for node, period in product(self.sets['NODES'], self.sets['PERIODS']):
            fixed_cost = self.params['fixed_operating_cost'][node]
            
            variable_cost = pulp.lpSum(
                self.vars['processed_product'][node, product, period] *
                self.params['variable_operating_cost'][node, product]
                for product in self.sets['PRODUCTS']
            )
            
            self.model += (
                self.vars['operating_cost'][node, period] == 
                fixed_cost * self.vars['node_active'][node, period] + variable_cost,
                f"operating_cost_{node}_{period}"
            )