import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime
import logging
from pathlib import Path

class DataLoader:
    """Handles loading and preprocessing of input data for the supply chain optimization model."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.logger = logging.getLogger(__name__)

    def load_input_data(self) -> Dict[str, pd.DataFrame]:
        """
        Loads all input sheets from Excel file into a dictionary of DataFrames.
        
        Returns:
            Dict[str, pd.DataFrame]: Dictionary containing all input DataFrames
        """
        try:
            input_values = {}
            sheets = {
                'parameters_input': 'Parameters',
                'scenarios_input': 'Scenarios',
                'objectives_input': 'Objectives',
                'periods_input': 'Periods',
                'products_input': 'Products',
                'product_transportation_groups_input': 'Product Transportation Groups',
                'nodes_input': 'Nodes',
                'node_types_input': 'Node Types',
                'flow_input': 'Flow',
                'fixed_operating_costs_input': 'Fixed Operating Costs',
                'variable_operating_costs_input': 'Variable Operating Costs',
                'transportation_costs_input': 'Transportation Costs',
                'transportation_constraints_input': 'Transportation Constraints',
                'load_capacity_input': 'Load Capacity',
                'pop_demand_change_const_input': 'PoP Demand Change Const',
                'node_capacity_input': 'Node Capacity',
                'node_capacity_types_input': 'Node Capacity Types',
                'carrying_or_missed_demand_cost_input': 'Carrying or Missed Demand Cost',
                'carrying_or_missed_demand_constraints_input': 'Carrying or Missed Constraints',
                'carrying_capacity_input': 'Carrying Capacity',
                'demand_input': 'Demand',
                'product_capacity_consumption_input': 'Product Capacity Consumption',
                'processing_expansions_input': 'Processing Expansions',
                'carrying_expansions_input': 'Carrying Expansions',
                'od_distances_and_transit_times_input': 'OD Distances and Transit Times',
                'max_transit_time_distance_input': 'Max Transit Time,Distance',
                'age_constraints_input': 'Age Constraints'
            }
            
            # Load each sheet
            for key, sheet_name in sheets.items():
                if key == 'parameters_input':
                    df = pd.read_excel(self.file_path, sheet_name=sheet_name, header=None, index_col=None).T
                    df.columns = df.iloc[0]
                    input_values[key] = df[1:]
                else:
                    input_values[key] = pd.read_excel(self.file_path, sheet_name=sheet_name)
            
            # Post-processing specific sheets
            input_values['demand_input']['Period'] = input_values['demand_input']['Period'].map(str)
            
            return input_values
        
        except Exception as e:
            self.logger.error(f"Error loading input data: {str(e)}")
            raise

    def preprocess_data(self, input_values: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Preprocesses loaded data to create derived sets and parameters.
        
        Args:
            input_values: Dictionary of input DataFrames
            
        Returns:
            Dict containing processed data sets and parameters
        """
        try:
            nodes_input = input_values['nodes_input']
            
            # Define core sets
            sets = {
                'NODES': nodes_input['Name'].unique(),
                'ORIGINS': nodes_input[nodes_input['Origin Node']=="X"]['Name'].unique(),
                'DESTINATIONS': nodes_input[nodes_input['Destination Node']=="X"]['Name'].unique(),
                'INTERMEDIATES': nodes_input[nodes_input['Intermediate Node']=="X"]['Name'].unique(),
                'PERIODS': list(map(str, input_values['periods_input']['Period'].unique())),
                'PRODUCTS': input_values['products_input']['Product'].unique(),
                'MEASURES': [m for m in input_values['products_input']['Measure'].unique() if m != "*"],
                'CONTAINERS': [c for c in input_values['transportation_costs_input']['Container'].unique() if c != "*"],
                'MODES': [m for m in input_values['transportation_costs_input']['Mode'].unique() if m != "*"]
            }
            
            # Derived sets
            sets['DEPARTING_NODES'] = np.unique(np.concatenate((sets['INTERMEDIATES'], sets['ORIGINS'])))
            sets['RECEIVING_NODES'] = np.unique(np.concatenate((sets['INTERMEDIATES'], sets['DESTINATIONS'])))
            sets['AGES'] = [str(int(age)-1) for age in sets['PERIODS']]
            
            # Node type related sets
            node_capacity_types = input_values['node_capacity_types_input']
            sets['NODE_CAPACITY_TYPES'] = node_capacity_types['Capacity Type'].unique()
            sets['NODE_PARENT_CAPACITY_TYPES'] = [
                cap_type for cap_type in node_capacity_types['Parent Capacity Type'].unique() 
                if pd.notna(cap_type)
            ]
            sets['NODE_CHILD_CAPACITY_TYPES'] = [
                cap_type for cap_type in sets['NODE_CAPACITY_TYPES'] 
                if cap_type not in sets['NODE_PARENT_CAPACITY_TYPES']
            ]
            
            # Expansion types
            sets['P_CAPACITY_EXPANSIONS'] = (
                input_values['processing_expansions_input']['Incremental Capacity Label'].unique()
                if len(input_values['processing_expansions_input']) > 0 else ["NA"]
            )
            sets['C_CAPACITY_EXPANSIONS'] = (
                input_values['carrying_expansions_input']['Incremental Capacity Label'].unique()
                if len(input_values['carrying_expansions_input']) > 0 else ["NA"]
            )
            
            return {'sets': sets, 'input_values': input_values}
            
        except Exception as e:
            self.logger.error(f"Error preprocessing data: {str(e)}")
            raise