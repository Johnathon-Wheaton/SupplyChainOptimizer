from typing import Dict, Any, list
import numpy as np
import pandas as pd
import logging

class ParameterCalculator:
    """Calculates derived parameters from input data."""
    
    def __init__(self, input_data: Dict[str, pd.DataFrame], sets: Dict[str, list]):
        self.input_data = input_data
        self.sets = sets
        self.logger = logging.getLogger(__name__)

    def calculate_parameters(self) -> Dict[str, Any]:
        """
        Calculates all derived parameters needed for optimization.
        
        Returns:
            Dictionary of calculated parameters
        """
        try:
            parameters = {}
            
            # Calculate distances and transit times
            parameters.update(self._calculate_distance_parameters())
            
            # Calculate costs
            parameters.update(self._calculate_cost_parameters())
            
            # Calculate capacities
            parameters.update(self._calculate_capacity_parameters())
            
            return parameters
            
        except Exception as e:
            self.logger.error(f"Error calculating parameters: {str(e)}")
            raise

    def _calculate_distance_parameters(self) -> Dict[str, Any]:
        """Calculates distance-related parameters."""
        try:
            od_data = self.input_data['od_distances_and_transit_times_input']
            
            distance_params = {}
            transit_time_params = {}
            
            for _, row in od_data.iterrows():
                key = (row['Origin'], row['Destination'], row['Mode'])
                distance_params[key] = row['Distance']
                transit_time_params[key] = row['Transit Time']
                
            return {
                'distance': distance_params,
                'transit_time': transit_time_params
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating distance parameters: {str(e)}")
            raise

    def _calculate_cost_parameters(self) -> Dict[str, Any]:
        """Calculates cost-related parameters."""
        try:
            cost_data = self.input_data['transportation_costs_input']
            
            fixed_costs = {}
            variable_costs = {}
            
            for _, row in cost_data.iterrows():
                key = (row['Origin'], row['Destination'], row['Mode'],
                      row['Container'], row['Measure'], row['Period'])
                fixed_costs[key] = row['Fixed Cost']
                variable_costs[key] = row['Cost per Unit of Distance']
                
            return {
                'transportation_cost_fixed': fixed_costs,
                'transportation_cost_variable': variable_costs
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating cost parameters: {str(e)}")
            raise

    def _calculate_capacity_parameters(self) -> Dict[str, Any]:
        """Calculates capacity-related parameters."""
        try:
            capacity_data = self.input_data['node_capacity_input']
            
            node_capacity = {}
            
            for _, row in capacity_data.iterrows():
                key = (row['Period'], row['Location Name'], row['Capacity Type'])
                node_capacity[key] = row['Capacity Value']
                
            return {'node_capacity': node_capacity}
            
        except Exception as e:
            self.logger.error(f"Error calculating capacity parameters: {str(e)}")
            raise