import json
import pandas as pd
from typing import Dict, Any
from .base_reader import BaseReader

class JSONReader(BaseReader):
    """JSON file reader implementation"""
    
    def read(self) -> Dict[str, pd.DataFrame]:
        """Read data from JSON file
        
        Returns:
            Dict containing all input values as DataFrames
        """
        # Read JSON file
        with open(self.file_path, 'r') as f:
            json_data = json.load(f)
            
        input_values = {}
        sheet_translation = {
            'Parameters': 'parameters_input',
            'Scenarios': 'scenarios_input',
            'Objectives': 'objectives_input',
            'Periods': 'periods_input',
            'Products': 'products_input',
            'Product Transportation Groups': 'product_transportation_groups_input',
            'Nodes': 'nodes_input',
            'Launch, Shutdown Hard Const': 'node_shut_down_launch_hard_constraints_input',
            'Node Types': 'node_types_input',
            'Node Groups': 'node_groups_input',
            'Flow': 'flow_input',
            'Processing Assembly Constraints': 'processing_assembly_constraints_input',
            'Shipping Assembly Constraints': 'shipping_assembly_constraints_input',
            'Fixed Operating Costs': 'fixed_operating_costs_input',
            'Variable Operating Costs': 'variable_operating_costs_input',
            'Transportation Costs': 'transportation_costs_input',
            'Transportation Constraints': 'transportation_constraints_input',
            'Transportation Expansions': 'transportation_expansions_input',
            'Trans Expansion Capacities': 'transportation_expansion_capacities_input',
            'Load Capacity': 'load_capacity_input',
            'PoP Demand Change Const': 'pop_demand_change_const_input',
            'Resource Capacities': 'resource_capacities_input',
            'Resource Capacity Types': 'resource_capacity_types_input',
            'Node-Resource Constraints': 'node_resource_constraints_input',
            'Resource Attribute Constraints': 'resource_attribute_constraints_input',
            'Resource Attributes': 'resource_attributes_input',
            'Resource Initial Counts': 'resource_initial_counts_input',
            'Resource Costs': 'resource_costs_input',
            'Carrying or Missed Demand Cost': 'carrying_or_missed_demand_cost_input',
            'Carrying or Missed Constraints': 'carrying_or_missed_demand_constraints_input',
            'Carrying Capacity': 'carrying_capacity_input',
            'Demand': 'demand_input',
            'Resource Capacity Consumption': 'resource_capacity_consumption_input',
            'Carrying Expansions': 'carrying_expansions_input',
            'OD Distances and Transit Times': 'od_distances_and_transit_times_input',
            'Max Transit Time,Distance': 'max_transit_time_distance_input',
            'Age Constraints': 'age_constraints_input'
            }
        # Convert each JSON section to DataFrame
        for sheet_name, sheet_data in json_data.items():
            # Handle Parameters sheet differently due to its transposed nature
            if sheet_name == 'Parameters':
                df = pd.DataFrame(sheet_data['data'], columns=sheet_data['columns'])
                df = df.set_index(df.columns[0]).T
                input_values['parameters_input'] = df
            else:
                # Convert to DataFrame and rename with standard suffix
                df = pd.DataFrame(sheet_data['data'], columns=sheet_data['columns'])
                sheet_key = sheet_translation[sheet_name]
                input_values[sheet_key] = df
                
                # Special handling for Demand sheet's Period column
                if sheet_name == 'Demand':
                    input_values[sheet_key]['Period'] = input_values[sheet_key]['Period'].map(str)
                
                # Convert numeric columns from strings to appropriate types
                self._convert_numeric_columns(input_values[sheet_key])
        
        return input_values

    def _convert_numeric_columns(self, df: pd.DataFrame) -> None:
        """Convert numeric columns to appropriate types
        
        Args:
            df: DataFrame to process
        """
        for column in df.columns:
            # Skip certain columns that should remain as strings
            if column in ['Scenario', 'Period', 'Product', 'Name', 'Node', 'Node Type', 
                         'Mode', 'Container', 'Measure', 'Group', 'Age']:
                continue
                
            # Try to convert to numeric, ignore if fails
            try:
                df[column] = pd.to_numeric(df[column], errors='ignore')
            except:
                continue

    def validate(self) -> bool:
        """Validate JSON file structure
        
        Returns:
            True if valid, raises exception if invalid
            
        Raises:
            ValueError: If JSON structure is invalid
        """
        try:
            with open(self.file_path, 'r') as f:
                data = json.load(f)
                
     
            required_sheets ={
                'Parameters': 'parameters_input',
                'Scenarios': 'scenarios_input',
                'Objectives': 'objectives_input',
                'Periods': 'periods_input',
                'Products': 'products_input',
                'Product Transportation Groups': 'product_transportation_groups_input',
                'Nodes': 'nodes_input',
                'Launch, Shutdown Hard Const': 'node_shut_down_launch_hard_constraints_input',
                'Node Types': 'node_types_input',
                'Node Groups': 'node_groups_input',
                'Flow': 'flow_input',
                'Processing Assembly Constraints': 'processing_assembly_constraints_input',
                'Shipping Assembly Constraints': 'shipping_assembly_constraints_input',
                'Fixed Operating Costs': 'fixed_operating_costs_input',
                'Variable Operating Costs': 'variable_operating_costs_input',
                'Transportation Costs': 'transportation_costs_input',
                'Transportation Constraints': 'transportation_constraints_input',
                'Transportation Expansions': 'transportation_expansions_input',
                'Trans Expansion Capacities': 'transportation_expansion_capacities_input',
                'Load Capacity': 'load_capacity_input',
                'PoP Demand Change Const': 'pop_demand_change_const_input',
                'Resource Capacities': 'resource_capacities_input',
                'Resource Capacity Types': 'resource_capacity_types_input',
                'Node-Resource Constraints': 'node_resource_constraints_input',
                'Resource Attribute Constraints': 'resource_attribute_constraints_input',
                'Resource Attributes': 'resource_attributes_input',
                'Resource Initial Counts': 'resource_initial_counts_input',
                'Resource Costs': 'resource_costs_input',
                'Carrying or Missed Demand Cost': 'carrying_or_missed_demand_cost_input',
                'Carrying or Missed Constraints': 'carrying_or_missed_demand_constraints_input',
                'Carrying Capacity': 'carrying_capacity_input',
                'Demand': 'demand_input',
                'Resource Capacity Consumption': 'resource_capacity_consumption_input',
                'Carrying Expansions': 'carrying_expansions_input',
                'OD Distances and Transit Times': 'od_distances_and_transit_times_input',
                'Max Transit Time,Distance': 'max_transit_time_distance_input',
                'Age Constraints': 'age_constraints_input'
            }
            
            # Check for required sheets
            missing_sheets = required_sheets.keys() - set(data.keys())
            if missing_sheets:
                raise ValueError(f"Missing required sheets: {missing_sheets}")
            
            # Validate structure of each sheet
            for sheet_name, sheet_data in data.items():
                if not isinstance(sheet_data, dict):
                    raise ValueError(f"Sheet {sheet_name} must be a dictionary")
                    
                if 'columns' not in sheet_data:
                    raise ValueError(f"Sheet {sheet_name} missing 'columns' key")
                    
                if 'data' not in sheet_data:
                    raise ValueError(f"Sheet {sheet_name} missing 'data' key")
                    
                if not isinstance(sheet_data['columns'], list):
                    raise ValueError(f"Sheet {sheet_name} columns must be a list")
                    
                if not isinstance(sheet_data['data'], list):
                    raise ValueError(f"Sheet {sheet_name} data must be a list")
                    
                # Check that data rows match column count
                col_count = len(sheet_data['columns'])
                for i, row in enumerate(sheet_data['data']):
                    if not isinstance(row, list):
                        raise ValueError(f"Sheet {sheet_name}, row {i} must be a list")
                        
                    if len(row) != col_count:
                        raise ValueError(
                            f"Sheet {sheet_name}, row {i} has {len(row)} columns, "
                            f"expected {col_count}"
                        )
            
            return True
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error validating JSON structure: {str(e)}")