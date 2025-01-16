from typing import Dict, Any, Tuple, List
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import json

class ConsistencyChecker:
    """Checks consistency of optimization results."""
    
    def __init__(self, results: Dict[str, pd.DataFrame], input_data: Dict[str, pd.DataFrame]):
        self.results = results
        self.input_data = input_data
        self.logger = logging.getLogger(__name__)
        self.tolerance = 1e-6  # Numerical tolerance for comparisons

    def check_solution_consistency(self) -> Tuple[bool, List[str]]:
        """
        Performs comprehensive consistency checks on optimization results.
        
        Returns:
            Tuple of (is_consistent, list_of_violations)
        """
        try:
            violations = []
            
            # Check flow conservation
            flow_violations = self._check_flow_conservation()
            violations.extend(flow_violations)
            
            # Check capacity constraints
            capacity_violations = self._check_capacity_constraints()
            violations.extend(capacity_violations)
            
            # Check demand satisfaction
            demand_violations = self._check_demand_satisfaction()
            violations.extend(demand_violations)
            
            # Check cost calculations
            cost_violations = self._check_cost_consistency()
            violations.extend(cost_violations)
            
            return len(violations) == 0, violations
            
        except Exception as e:
            self.logger.error(f"Error checking solution consistency: {str(e)}")
            raise

    def _check_flow_conservation(self) -> List[str]:
        """Checks flow conservation at each node."""
        violations = []
        
        try:
            if 'departed_product' not in self.results or 'arrived_product' not in self.results:
                return ["Missing flow data"]
                
            departed_df = self.results['departed_product']
            arrived_df = self.results['arrived_product']
            
            # Check for each node and period
            for node in self.input_data['nodes_input']['Name'].unique():
                for period in self.input_data['periods_input']['Period'].unique():
                    # Calculate inbound flow
                    inflow = arrived_df[
                        (arrived_df['Node'] == node) & 
                        (arrived_df['Period'] == period)
                    ]['Value'].sum()
                    
                    # Calculate outbound flow
                    outflow = departed_df[
                        (departed_df['Origin'] == node) & 
                        (departed_df['Period'] == period)
                    ]['Value'].sum()
                    
                    # Check conservation
                    processed = self.results.get('processed_product', pd.DataFrame())
                    if not processed.empty:
                        processing = processed[
                            (processed['Node'] == node) & 
                            (processed['Period'] == period)
                        ]['Value'].sum()
                        
                        if abs(inflow - outflow - processing) > self.tolerance:
                            violations.append(
                                f"Flow conservation violated at node {node} in period {period}"
                            )
        
        except Exception as e:
            violations.append(f"Error checking flow conservation: {str(e)}")
            
        return violations

    def _check_capacity_constraints(self) -> List[str]:
        """Checks if capacity constraints are satisfied."""
        violations = []
        
        try:
            if 'processed_product' not in self.results:
                return ["Missing processing data"]
                
            processed_df = self.results['processed_product']
            capacity_df = self.input_data['capacity_input']
            
            # Check processing capacity
            for node in self.input_data['nodes_input']['Name'].unique():
                for period in self.input_data['periods_input']['Period'].unique():
                    # Calculate total processing
                    total_processing = processed_df[
                        (processed_df['Node'] == node) & 
                        (processed_df['Period'] == period)
                    ]['Value'].sum()
                    
                    # Get capacity
                    capacity = capacity_df[
                        (capacity_df['Node'] == node) & 
                        (capacity_df['Period'] == period)
                    ]['Capacity'].iloc[0]
                    
                    if total_processing > capacity + self.tolerance:
                        violations.append(
                            f"Capacity violated at node {node} in period {period}"
                        )
        
        except Exception as e:
            violations.append(f"Error checking capacity constraints: {str(e)}")
            
        return violations

    def _check_demand_satisfaction(self) -> List[str]:
        """Checks if demand requirements are met."""
        violations = []
        
        try:
            if 'arrived_product' not in self.results:
                return ["Missing delivery data"]
                
            delivered_df = self.results['arrived_product']
            demand_df = self.input_data['demand_input']
            
            # Check for each destination, product, and period
            for _, demand_row in demand_df.iterrows():
                dest = demand_row['Destination']
                product = demand_row['Product']
                period = demand_row['Period']
                required_demand = demand_row['Demand']
                
                # Calculate actual delivery
                delivered = delivered_df[
                    (delivered_df['Node'] == dest) & 
                    (delivered_df['Product'] == product) & 
                    (delivered_df['Period'] == period)
                ]['Value'].sum()
                
                if delivered + self.tolerance < required_demand:
                    violations.append(
                        f"Demand not met for product {product} at {dest} in period {period}"
                    )
        
        except Exception as e:
            violations.append(f"Error checking demand satisfaction: {str(e)}")
            
        return violations

    def _check_cost_consistency(self) -> List[str]:
        """Checks consistency of cost calculations."""
        violations = []
        
        try:
            if 'transport_cost' not in self.results:
                return ["Missing cost data"]
                
            # Check transportation costs
            transport_costs_df = self.results['transport_cost']
            departed_df = self.results['departed_product']
            cost_params = self.input_data['transportation_costs_input']
            
            # Sample check for a few routes
            sample_routes = departed_df.head(10)
            for _, route in sample_routes.iterrows():
                # Calculate expected cost
                params = cost_params[
                    (cost_params['Origin'] == route['Origin']) & 
                    (cost_params['Destination'] == route['Destination'])
                ]
                
                if not params.empty:
                    expected_cost = (
                        params['Fixed Cost'].iloc[0] + 
                        route['Value'] * params['Variable Cost'].iloc[0]
                    )
                    
                    actual_cost = transport_costs_df[
                        (transport_costs_df['Origin'] == route['Origin']) & 
                        (transport_costs_df['Destination'] == route['Destination'])
                    ]['Value'].sum()
                    
                    if abs(expected_cost - actual_cost) > self.tolerance:
                        violations.append(
                            f"Cost calculation inconsistent for route {route['Origin']}-{route['Destination']}"
                        )
        
        except Exception as e:
            violations.append(f"Error checking cost consistency: {str(e)}")
            
        return violations