from typing import Dict, Any, List
import pandas as pd
import logging
from datetime import datetime
from itertools import product

class DataPreprocessor:
    """Handles data preprocessing operations for network optimization"""
    
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
        logging.info("Splitting data.")
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
        
        logging.info(f"Done splitting data. {round((datetime.now() - split_start_time).seconds, 0)} seconds.")
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