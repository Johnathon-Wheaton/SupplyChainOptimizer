from itertools import product
from typing import Dict, Any
import pulp
import logging

class FlowConstraintGenerator:
    """Handles generation of flow-related constraints."""
    
    def __init__(self, model: pulp.LpProblem, sets: Dict[str, Any], 
                 params: Dict[str, Any], vars: Dict[str, Any]):
        self.model = model
        self.sets = sets
        self.params = params
        self.vars = vars
        self.logger = logging.getLogger(__name__)

    def add_flow_conservation_constraints(self):
        """Adds basic flow conservation constraints."""
        try:
            # Node flow conservation
            for node, period, product in product(
                self.sets['NODES'], 
                self.sets['PERIODS'], 
                self.sets['PRODUCTS']
            ):
                inflow = pulp.lpSum(
                    self.vars['departed_product'][n, node, product, period]
                    for n in self.sets['DEPARTING_NODES']
                )
                outflow = pulp.lpSum(
                    self.vars['departed_product'][node, n, product, period]
                    for n in self.sets['RECEIVING_NODES']
                )
                
                self.model += (
                    inflow == outflow + self.vars['processed_product'][node, product, period],
                    f"flow_conservation_{node}_{period}_{product}"
                )

    def add_demand_satisfaction_constraints(self):
        """Adds constraints ensuring demand satisfaction."""
        for dest, period, product in product(
            self.sets['DESTINATIONS'],
            self.sets['PERIODS'],
            self.sets['PRODUCTS']
        ):
            demand = self.params['demand'][period, product, dest]
            total_received = pulp.lpSum(
                self.vars['departed_product'][n, dest, product, period]
                for n in self.sets['DEPARTING_NODES']
            )
            
            self.model += (
                total_received + self.vars['dropped_demand'][dest, product, period] == demand,
                f"demand_satisfaction_{dest}_{period}_{product}"
            )

    def add_age_tracking_constraints(self):
        """Adds constraints for tracking product age."""
        for node, period, product, age in product(
            self.sets['NODES'],
            self.sets['PERIODS'],
            self.sets['PRODUCTS'],
            self.sets['AGES']
        ):
            if int(period) > 1 and int(age) > 0:
                prev_period = str(int(period) - 1)
                prev_age = str(int(age) - 1)
                
                self.model += (
                    self.vars['age_inventory'][node, product, period, age] == 
                    self.vars['age_inventory'][node, product, prev_period, prev_age] -
                    self.vars['age_shipped'][node, product, period, age],
                    f"age_tracking_{node}_{period}_{product}_{age}"
                )