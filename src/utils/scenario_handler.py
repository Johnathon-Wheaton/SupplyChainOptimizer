import pandas as pd
from typing import Dict, list
import logging

class ScenarioHandler:
    """Handles scenario-related operations."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def split_scenarios(self, input_data: Dict[str, pd.DataFrame], 
                       scenarios: list[str]) -> Dict[str, pd.DataFrame]:
        """
        Splits data by scenarios and handles wildcard (*) scenarios.
        
        Args:
            input_data: Dictionary of input DataFrames
            scenarios: list of scenario names
            
        Returns:
            Dictionary of processed DataFrames
        """
        try:
            processed_data = {}
            
            for df_name, df in input_data.items():
                if 'Scenario' in df.columns:
                    # Handle wildcard scenarios
                    base_df = df[df['Scenario'] == '*'].copy()
                    scenario_dfs = []
                    
                    for scenario in scenarios:
                        scenario_df = df[df['Scenario'] == scenario].copy()
                        if not scenario_df.empty:
                            scenario_dfs.append(scenario_df)
                        elif not base_df.empty:
                            scenario_base = base_df.copy()
                            scenario_base['Scenario'] = scenario
                            scenario_dfs.append(scenario_base)
                            
                    processed_data[df_name] = pd.concat(scenario_dfs, ignore_index=True)
                else:
                    processed_data[df_name] = df
                    
            return processed_data
            
        except Exception as e:
            self.logger.error(f"Error splitting scenarios: {str(e)}")
            raise

    def merge_scenario_results(self, base_results: Dict[str, pd.DataFrame],
                             new_results: Dict[str, pd.DataFrame],
                             scenario: str) -> Dict[str, pd.DataFrame]:
        """
        Merges results from different scenarios.
        
        Args:
            base_results: Existing results dictionary
            new_results: New scenario results to merge
            scenario: Scenario name
            
        Returns:
            Merged results dictionary
        """
        try:
            merged_results = {}
            
            for key in base_results.keys():
                if key in new_results:
                    df1 = base_results[key]
                    df2 = new_results[key]
                    
                    # Add scenario column if not present
                    if 'Scenario' not in df1.columns:
                        df1.insert(0, 'Scenario', scenario)
                    if 'Scenario' not in df2.columns:
                        df2.insert(0, 'Scenario', scenario)
                    
                    # Merge DataFrames
                    merged_results[key] = pd.concat([df1, df2], ignore_index=True)
                else:
                    merged_results[key] = base_results[key]
                    
            return merged_results
            
        except Exception as e:
            self.logger.error(f"Error merging scenario results: {str(e)}")
            raise