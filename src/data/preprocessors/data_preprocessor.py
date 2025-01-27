from typing import Dict, Any, List
import pandas as pd
import logging
from datetime import datetime
from itertools import product

class DataPreprocessor:
    """Handles data preprocessing operations for network optimization"""
    
    @staticmethod
    def preprocess_data(input_data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Main method to handle all preprocessing operations
        
        Args:
            input_data: Dictionary containing all input DataFrames
            list_of_sets: Dictionary containing all network sets
            
        Returns:
            Processed dictionary of DataFrames
        """
        preprocessed_data = input_data.copy()
        
        # Process node groups and binary assignments
        preprocessed_data['node_groups_input']['assigned'] = 1
        preprocessed_data['node_groups_input'] = DataPreprocessor._process_node_groups(
            preprocessed_data['node_groups_input'], 
            list_of_sets
        )
        
        # Process node constraints
        preprocessed_data = DataPreprocessor._process_node_constraints(preprocessed_data, list_of_sets)
        
        # Process demand related data
        preprocessed_data = DataPreprocessor._process_demand_data(preprocessed_data, list_of_sets)
        
        # Process resource related data
        preprocessed_data = DataPreprocessor._process_resource_data(preprocessed_data, list_of_sets)
        
        # Process transportation related data
        preprocessed_data = DataPreprocessor._process_transportation_data(preprocessed_data, list_of_sets)
        
        # Process cost related data
        preprocessed_data = DataPreprocessor._process_cost_data(preprocessed_data, list_of_sets)
        
        # Process capacity related data
        preprocessed_data = DataPreprocessor._process_capacity_data(preprocessed_data, list_of_sets)
        
        # Process flow and assembly data
        preprocessed_data = DataPreprocessor._process_flow_assembly_data(preprocessed_data, list_of_sets)
        
        return preprocessed_data

    @staticmethod
    def _process_node_groups(node_groups_df: pd.DataFrame, list_of_sets: Dict[str, List]) -> pd.DataFrame:
        """Process node groups data"""
        df = node_groups_df.copy()
        df = DataPreprocessor.split_asterisk_values(df, 'Group', list_of_sets['NODEGROUPS'])
        df = DataPreprocessor.split_asterisk_values(df, 'Node', list_of_sets['NODES'])
        return df

    @staticmethod
    def _process_node_constraints(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process node related constraints"""
        df = data.copy()
        
        # Process launch/shutdown constraints
        launch_shutdown_df = df['node_shut_down_launch_hard_constraints_input']
        launch_shutdown_df.loc[
            (launch_shutdown_df['Launch'].notna()) & (launch_shutdown_df['Launch'] != 0),
            'Launch'
        ] = 1
        launch_shutdown_df.loc[
            (launch_shutdown_df['Launch'].isna()) | (launch_shutdown_df['Launch'] == 0),
            'Launch'
        ] = 0
        
        launch_shutdown_df.loc[
            (launch_shutdown_df['Shutdown'].notna()) & (launch_shutdown_df['Shutdown'] != 0),
            'Shutdown'
        ] = 1
        launch_shutdown_df.loc[
            (launch_shutdown_df['Shutdown'].isna()) | (launch_shutdown_df['Shutdown'] == 0),
            'Shutdown'
        ] = 0
        
        df['node_shut_down_launch_hard_constraints_input'] = launch_shutdown_df
        
        # Process node types
        if 'node_types_input' in df:
            df['node_types_input'] = DataPreprocessor.split_asterisk_values(
                df['node_types_input'], 'Period', list_of_sets['PERIODS']
            )
            
        # Create node type assignment data
        if 'nodes_input' in df:
            node_type_input = df['nodes_input'][['Name', 'Node Type']].copy()
            node_type_input['value'] = 1
            node_type_input = DataPreprocessor.fill_missing_values(
                node_type_input,
                value_fields=['value'],
                sets={
                    "NODES": list_of_sets['NODES'],
                    "NODETYPES": list_of_sets['NODETYPES']
                },
                target_columns=['Name', 'Node Type'],
                fill_with={'value': 0}
            )
            df['node_type_input'] = node_type_input
        return df

    @staticmethod
    def _process_demand_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process demand related data"""
        df = data.copy()
        
        # Process demand input
        df['demand_input'] = DataPreprocessor.split_asterisk_values(
            df['demand_input'], 'Period', list_of_sets['PERIODS']
        )
        df['demand_input'] = DataPreprocessor.split_asterisk_values(
            df['demand_input'], 'Product', list_of_sets['PRODUCTS']
        )
        df['demand_input'] = DataPreprocessor.split_asterisk_values(
            df['demand_input'], 'Destination', list_of_sets['RECEIVING_NODES']
        )
        
        # Process age constraints
        if 'age_constraints_input' in df:
            for column, set_name in {
                'Period': 'PERIODS',
                'Product': 'PRODUCTS',
                'Destination': 'NODES',
                'Age': 'AGES',
                'Destination Node Group': 'NODEGROUPS'
            }.items():
                df['age_constraints_input'] = DataPreprocessor.split_asterisk_values(
                    df['age_constraints_input'], column, list_of_sets[set_name]
                )
        
        return df

    @staticmethod
    def _process_resource_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process resource related data"""
        df = data.copy()
        
        # Process resource capacity consumption
        for resource_df in ['resource_capacity_consumption_input', 'resource_costs_input', 
                          'resource_capacities_input', 'resource_initial_counts_input',
                          'node_resource_constraints_input']:
            if resource_df in df:
                df[resource_df] = DataPreprocessor._process_resource_dataframe(
                    df[resource_df], list_of_sets
                )
        
        # Process resource attributes
        if 'resource_attributes_input' in df:
            df['resource_attributes_input'] = DataPreprocessor.split_asterisk_values(
                df['resource_attributes_input'], 'Resource Attribute', list_of_sets['RESOURCE_ATTRIBUTES']
            )
            df['resource_attributes_input'] = DataPreprocessor.split_asterisk_values(
                df['resource_attributes_input'], 'Period', list_of_sets['PERIODS']
            )
            
        # Process resource attribute constraints
        if 'resource_attribute_constraints_input' in df:
            for column in ['Node Group', 'Period', 'Resource', 'Node', 'Resource Attribute']:
                set_name = column.upper().replace(' ', '_') + 'S'
                if set_name in list_of_sets:
                    df['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(
                        df['resource_attribute_constraints_input'], column, list_of_sets[set_name]
                    )
        
        return df

    @staticmethod
    def _process_resource_dataframe(df: pd.DataFrame, list_of_sets: Dict[str, List]) -> pd.DataFrame:
        """Process individual resource related DataFrame"""
        processed_df = df.copy()
        
        # Common columns to process
        columns_to_process = {
            'Period': 'PERIODS',
            'Resource': 'RESOURCES',
            'Node': 'NODES',
            'Node Group': 'NODEGROUPS',
            'Capacity Type': 'RESOURCE_CAPACITY_TYPES',
            'Product': 'PRODUCTS'
        }
        
        for column, set_name in columns_to_process.items():
            if column in processed_df.columns and set_name in list_of_sets:
                processed_df = DataPreprocessor.split_asterisk_values(
                    processed_df, column, list_of_sets[set_name]
                )
                
        return processed_df

    @staticmethod
    def _process_transportation_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process transportation related data"""
        df = data.copy()
        
        # Common columns to process for transportation related DataFrames
        transport_columns = {
            'Period': 'PERIODS',
            'Origin': 'DEPARTING_NODES',
            'Destination': 'RECEIVING_NODES',
            'Origin Node Group': 'NODEGROUPS',
            'Destination Node Group': 'NODEGROUPS',
            'Mode': 'MODES',
            'Container': 'CONTAINERS',
            'Measure': 'MEASURES'
        }
        
        # Process each transportation related DataFrame
        transport_dfs = [
            'transportation_costs_input',
            'load_capacity_input',
            'transportation_constraints_input',
            'transportation_expansions_input',
            'transportation_expansion_capacities_input'
        ]
        
        for transport_df in transport_dfs:
            if transport_df in df:
                for column, set_name in transport_columns.items():
                    if column in df[transport_df].columns:
                        df[transport_df] = DataPreprocessor.split_asterisk_values(
                            df[transport_df], column, list_of_sets[set_name]
                        )
        
        # Process product transportation groups
        if 'product_transportation_groups_input' in df:
            df['product_transportation_groups_input']['value'] = 1
            df['product_transportation_groups_input'] = DataPreprocessor.split_asterisk_values(
                df['product_transportation_groups_input'], 'Product', list_of_sets['PRODUCTS']
            )
        
        return df

    @staticmethod
    def _process_cost_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process cost related data"""
        df = data.copy()
        
        # Process operating costs
        for cost_df in ['fixed_operating_costs_input', 'variable_operating_costs_input']:
            if cost_df in df:
                df[cost_df] = DataPreprocessor.split_asterisk_values(
                    df[cost_df], 'Period', list_of_sets['PERIODS']
                )
                df[cost_df] = DataPreprocessor.split_asterisk_values(
                    df[cost_df], 'Name', list_of_sets['NODES']
                )
                df[cost_df] = DataPreprocessor.split_asterisk_values(
                    df[cost_df], 'Node Group', list_of_sets['NODEGROUPS']
                )
                
                if 'Product' in df[cost_df].columns:
                    df[cost_df] = DataPreprocessor.split_asterisk_values(
                        df[cost_df], 'Product', list_of_sets['PRODUCTS']
                    )
        
        return df

    @staticmethod
    def _process_capacity_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process capacity related data"""
        df = data.copy()
        
        # Process carrying capacity data
        if 'carrying_capacity_input' in df:
            for column in ['Period', 'Node', 'Node Group', 'Measure']:
                set_name = column.upper().replace(' ', '_') + 'S'
                if set_name in list_of_sets:
                    df['carrying_capacity_input'] = DataPreprocessor.split_asterisk_values(
                        df['carrying_capacity_input'], column, list_of_sets[set_name]
                    )
        
        # Process carrying expansions
        if 'carrying_expansions_input' in df:
            df['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(
                df['carrying_expansions_input'], 'Location', list_of_sets['NODES']
            )
            df['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(
                df['carrying_expansions_input'], 'Node Group', list_of_sets['NODEGROUPS']
            )
            df['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(
                df['carrying_expansions_input'], 'Period', list_of_sets['PERIODS']
            )
            df['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(
                df['carrying_expansions_input'], 'Incremental Capacity Label', 
                list_of_sets['C_CAPACITY_EXPANSIONS']
            )
            
        return df

    @staticmethod
    def _process_flow_assembly_data(data: Dict[str, pd.DataFrame], list_of_sets: Dict[str, List]) -> Dict[str, pd.DataFrame]:
        """Process flow and assembly related data"""
        df = data.copy()
        
        # Process flow data
        if 'flow_input' in df:
            flow_columns = {
                'Period': 'PERIODS',
                'Node': 'DEPARTING_NODES',
                'Node Group': 'NODEGROUPS',
                'Downstream Node': 'RECEIVING_NODES',
                'Downstream Node Group': 'NODEGROUPS',
                'Product': 'PRODUCTS',
                'Mode': 'MODES',
                'Container': 'CONTAINERS',
                'Measure': 'MEASURES'
            }
            
            for column, set_name in flow_columns.items():
                df['flow_input'] = DataPreprocessor.split_asterisk_values(
                    df['flow_input'], column, list_of_sets[set_name]
                )
        
        # Process assembly constraints
        assembly_dfs = ['processing_assembly_constraints_input', 'shipping_assembly_constraints_input']
        for assembly_df in assembly_dfs:
            if assembly_df in df:
                df[assembly_df] = DataPreprocessor._process_assembly_constraints(
                    df[assembly_df], list_of_sets
                )
        
        return df

    @staticmethod
    def _process_assembly_constraints(df: pd.DataFrame, list_of_sets: Dict[str, List]) -> pd.DataFrame:
        """Process assembly constraints DataFrame"""
        processed_df = df.copy()
        
        # Common columns to process
        columns_to_process = {
            'Period': 'PERIODS',
            'Product 1': 'PRODUCTS',
            'Product 2': 'PRODUCTS',
            'Node': 'NODES',
            'Node Group': 'NODEGROUPS',
            'Origin': 'DEPARTING_NODES',
            'Destination': 'RECEIVING_NODES',
            'Origin Node Group': 'NODEGROUPS',
            'Destination Node Group': 'NODEGROUPS'
        }
        
        for column, set_name in columns_to_process.items():
            if column in processed_df.columns:
                processed_df = DataPreprocessor.split_asterisk_values(
                    processed_df, column, list_of_sets[set_name]
                )
                
        return processed_df

    @staticmethod
    def split_asterisk_values(df: pd.DataFrame, ref_column: str, full_set: List[Any]) -> pd.DataFrame:
        """Split rows with asterisk values into multiple rows with explicit values
        
        Args:
            df: DataFrame to process
            ref_column: Column containing potential asterisk values
            full_set: Complete set of values to expand asterisks into
            
        Returns:
            Processed DataFrame with asterisks expanded
        """
        split_start_time = datetime.now()
        logging.info(f"Splitting data for column {ref_column}")
        df = pd.DataFrame(df)
        
        # Split into static and change dataframes
        df_static = df[df[ref_column] != '*']
        df_change = df[df[ref_column] == '*']

        if df_change.shape[0] > 0:
            # Merge with full_set
            df = df_static.copy()
            for s in full_set:
                new_df = df_change.copy()
                new_df[ref_column] = s
                df = pd.concat([df, new_df], ignore_index=True)
        
        logging.info(f"Done splitting data for column {ref_column}. {round((datetime.now() - split_start_time).seconds, 0)} seconds.")
        return df

    @staticmethod
    def fill_missing_values(df: pd.DataFrame, value_fields: List[str], 
                          sets: Dict[str, List], target_columns: List[str], 
                          fill_with: Dict[str, Any]) -> pd.DataFrame:
        """Fill missing values in DataFrame based on all possible combinations
        
        Args:
            df: DataFrame to process
            value_fields: Columns containing values to be filled
            sets: Dictionary of sets containing all possible values
            target_columns: Columns to generate combinations for
            fill_with: Dictionary mapping columns to fill values
            
        Returns:
            Processed DataFrame with missing values filled
        """
        fill_missing_data_start_time = datetime.now()
        logging.info("Filling missing values.")

        # Generate all possible combinations
        all_combinations = pd.DataFrame(
            list(product(*(values for values in sets.values()))), 
            columns=target_columns
        )
        logging.info(f"Done generating all combinations. {round((datetime.now() - fill_missing_data_start_time).seconds, 0)} seconds.")
        
        # Prepare for merge
        sets_columns = [col for col in df.columns if col in all_combinations.columns]
        value_columns = [col for col in df.columns if col not in all_combinations.columns]
        
        all_combinations[value_columns] = None
        merged = all_combinations.merge(df, on=sets_columns, how='left', indicator=True)

        # Filter and combine
        all_combinations = merged[merged['_merge'] == 'left_only'].drop(columns='_merge')
        return_df = pd.concat([df, all_combinations], ignore_index=True)
        
        logging.info(f"Done merging all combinations. {round((datetime.now() - fill_missing_data_start_time).seconds, 0)} seconds.")
        
        # Fill missing values
        for x in value_fields:
            return_df[x].fillna(fill_with[x], inplace=True)
        
        logging.info(f"Done filling missing data. {round((datetime.now() - fill_missing_data_start_time).seconds, 0)} seconds.")
        return return_df

    @staticmethod
    def split_scenarios(input_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Split scenario data for all relevant DataFrames
        
        Args:
            input_data: Dictionary of input DataFrames
            
        Returns:
            Processed dictionary of DataFrames with scenarios split
        """
        # Get unique scenarios
        SCENARIOS = input_data['objectives_input']['Scenario'].unique()
        
        # Process each DataFrame
        for x in input_data:
            if 'Scenario' in input_data[x].columns:
                input_data[x] = DataPreprocessor.split_asterisk_values(
                    input_data[x], 'Scenario', SCENARIOS
                )
        
        return input_data