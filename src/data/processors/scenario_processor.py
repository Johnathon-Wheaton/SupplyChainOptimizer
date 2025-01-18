from typing import Dict
import pandas as pd

class ScenarioProcessor:
    """Handles scenario-related processing of results"""
    
    @staticmethod
    def add_scenario_column_to_results(results: Dict[str, pd.DataFrame], scenario: str) -> Dict[str, pd.DataFrame]:
        """Add scenario column to all result DataFrames
        
        Args:
            results: Dictionary of result DataFrames
            scenario: Scenario identifier
            
        Returns:
            Updated results dictionary with scenario column added
        """
        new_dict = {}
        
        for key, df in results.items():
            # Create a new column with scenario identifier for all rows
            df.insert(0, 'Scenario', scenario)
            new_dict[key] = df
        
        return new_dict

    @staticmethod
    def append_scenario_results(results: Dict[str, pd.DataFrame], 
                              scenario_results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Append new scenario results to existing results
        
        Args:
            results: Existing results dictionary
            scenario_results: New scenario results to append
            
        Returns:
            Combined results dictionary
        """
        result_dict = {}
        
        for key in results.keys():
            if key in scenario_results:
                df1 = results[key]
                df2 = scenario_results[key]
                
                # Check if the number of columns matches
                if len(df1.columns) != len(df2.columns):
                    raise ValueError(f"DataFrames for key '{key}' have different numbers of columns.")
                
                # Append the dataframes vertically
                combined_df = pd.concat([df1, df2], axis=0, ignore_index=True)
                
                result_dict[key] = combined_df
            else:
                raise KeyError(f"Key '{key}' not found in the second dictionary.")
        
        return result_dict