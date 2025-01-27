import pandas as pd
from typing import Dict, Any
from .base_reader import BaseReader

class ExcelReader(BaseReader):
    """Excel file reader implementation"""
    
    def read(self) -> Dict[str, Any]:
        """Read data from Excel file
        
        Returns:
            Dict containing all input values from the Excel sheets
        """
        input_values = {}

        # Read all required sheets
        input_values['parameters_input'] = pd.read_excel(self.file_path, sheet_name='Parameters', header=None, index_col=None).T
        input_values['parameters_input'].columns = input_values['parameters_input'].iloc[0]
        input_values['parameters_input'] = input_values['parameters_input'][1:]
        input_values['parameters_input'] = input_values['parameters_input'].reset_index(drop=True)

        input_values['scenarios_input'] = pd.read_excel(self.file_path, sheet_name='Scenarios')
        input_values['objectives_input'] = pd.read_excel(self.file_path, sheet_name='Objectives')
        input_values['periods_input'] = pd.read_excel(self.file_path, sheet_name='Periods')
        input_values['products_input'] = pd.read_excel(self.file_path, sheet_name='Products')
        input_values['product_transportation_groups_input'] = pd.read_excel(self.file_path, sheet_name='Product Transportation Groups')
        input_values['nodes_input'] = pd.read_excel(self.file_path, sheet_name='Nodes')
        input_values['node_shut_down_launch_hard_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Launch, Shutdown Hard Const')
        input_values['node_types_input'] = pd.read_excel(self.file_path, sheet_name='Node Types')
        input_values['node_groups_input'] = pd.read_excel(self.file_path, sheet_name='Node Groups')
        input_values['flow_input'] = pd.read_excel(self.file_path, sheet_name='Flow')
        input_values['processing_assembly_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Processing Assembly Constraints')
        input_values['shipping_assembly_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Shipping Assembly Constraints')
        input_values['fixed_operating_costs_input'] = pd.read_excel(self.file_path, sheet_name='Fixed Operating Costs')
        input_values['variable_operating_costs_input'] = pd.read_excel(self.file_path, sheet_name='Variable Operating Costs')
        input_values['transportation_costs_input'] = pd.read_excel(self.file_path, sheet_name='Transportation Costs')
        input_values['transportation_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Transportation Constraints')
        input_values['transportation_expansions_input'] = pd.read_excel(self.file_path, sheet_name='Transportation Expansions')
        input_values['transportation_expansion_capacities_input'] = pd.read_excel(self.file_path, sheet_name='Trans Expansion Capacities')
        input_values['load_capacity_input'] = pd.read_excel(self.file_path, sheet_name='Load Capacity')
        input_values['pop_demand_change_const_input'] = pd.read_excel(self.file_path, sheet_name='PoP Demand Change Const')
        input_values['resource_capacities_input'] = pd.read_excel(self.file_path, sheet_name='Resource Capacities')
        input_values['resource_capacity_types_input'] = pd.read_excel(self.file_path, sheet_name='Resource Capacity Types')
        input_values['node_resource_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Node-Resource Constraints')
        input_values['resource_attribute_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Resource Attribute Constraints')
        input_values['resource_attributes_input'] = pd.read_excel(self.file_path, sheet_name='Resource Attributes')
        input_values['resource_initial_counts_input'] = pd.read_excel(self.file_path, sheet_name='Resource Initial Counts')
        input_values['resource_costs_input'] = pd.read_excel(self.file_path, sheet_name='Resource Costs')
        input_values['carrying_or_missed_demand_cost_input'] = pd.read_excel(self.file_path, sheet_name='Carrying or Missed Demand Cost')
        input_values['carrying_or_missed_demand_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Carrying or Missed Constraints')
        input_values['carrying_capacity_input'] = pd.read_excel(self.file_path, sheet_name='Carrying Capacity')
        input_values['demand_input'] = pd.read_excel(self.file_path, sheet_name='Demand')
        input_values['demand_input']['Period'] = input_values['demand_input']['Period'].map(str)
        input_values['resource_capacity_consumption_input'] = pd.read_excel(self.file_path, sheet_name='Resource Capacity Consumption')
        input_values['carrying_expansions_input'] = pd.read_excel(self.file_path, sheet_name='Carrying Expansions')
        input_values['od_distances_and_transit_times_input'] = pd.read_excel(self.file_path, sheet_name='OD Distances and Transit Times')
        input_values['max_transit_time_distance_input'] = pd.read_excel(self.file_path, sheet_name='Max Transit Time,Distance')
        input_values['age_constraints_input'] = pd.read_excel(self.file_path, sheet_name='Age Constraints')

        return input_values