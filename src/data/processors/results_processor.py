from typing import Dict, Any
import pandas as pd

class ResultsProcessor:
    """Handles processing and compilation of optimization results"""
    
    @staticmethod
    def get_results_as_df(target_variable: str, variables: Dict[str, Any], 
                         sets: Dict[str, Any], dimensions: Dict[str, Any]) -> pd.DataFrame:
        """Convert optimization variable results to DataFrame
        
        Args:
            target_variable: Name of variable to process
            variables: Dictionary of optimization variables
            sets: Dictionary of set definitions
            dimensions: Dictionary of variable dimensions
            
        Returns:
            DataFrame containing processed results
        """
        variable = variables[target_variable]
        variable_dimensions = dimensions[target_variable]
        
        if len(variable_dimensions) > 0:
            solution = {}
            if len(variable_dimensions) > 1:
                from itertools import product
                for x in product(*[sets[set_name] for set_name in variable_dimensions]):
                    solution[x] = variable[x].varValue
                df = pd.DataFrame(solution.values(), index=pd.MultiIndex.from_tuples(solution.keys()))
            else:
                for x in sets[variable_dimensions[0]]:
                    solution[x] = variable[x].varValue
                df = pd.DataFrame(solution.values(), index=solution.keys())
            df.reset_index(inplace=True)
            colnames = variable_dimensions.copy()
            colnames.append(target_variable)
            df.columns = colnames
            df = df.loc[(df[target_variable] != 0) & (df[target_variable] != None)]
        else:
            df = pd.DataFrame({target_variable: [variable.varValue]})
        return df

    @staticmethod
    def get_results_dictionary(output_results: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Convert all optimization results to dictionary of DataFrames
        
        Args:
            output_results: Dictionary containing optimization output
            
        Returns:
            Dictionary mapping variable names to result DataFrames
        """
        results = {}
        for target_variable in output_results['variables'].keys():
            results[target_variable] = ResultsProcessor.get_results_as_df(
                target_variable, 
                output_results['variables'], 
                output_results['sets'], 
                output_results['dimensions']
            )
        return results

    @staticmethod
    def add_merged_tables(results: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """Add merged result tables to results dictionary
        
        Args:
            results: Dictionary of result DataFrames
            
        Returns:
            Updated dictionary with merged tables added
        """
        # Transportation costs and measures
        results['m_transportation_costs'] = results['variable_transportation_costs'].merge(
            results['fixed_transportation_costs'], how='outer'
        )
        results['m_transportation_measures'] = results['departed_measures']
        results['m_transportation_volumes'] = results['vol_departed_by_age']
        results['m_loads'] = results['num_loads'].merge(results['transportation_costs'], how='outer')
        
        # Arrived, processed, queued and dropped
        results['m_arrived_processed_queued_dropped'] = results['vol_arrived_by_age'].merge(
            results['age_violation_cost'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['demand_by_age'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['vol_processed_by_age'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['ib_vol_carried_over_by_age'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['ib_carried_volume_cost'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['ob_vol_carried_over_by_age'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['ob_carried_volume_cost'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['vol_dropped_by_age'], how='outer'
        )
        results['m_arrived_processed_queued_dropped'] = results['m_arrived_processed_queued_dropped'].merge(
            results['dropped_volume_cost'], how='outer'
        )
        
        # Rename and merge volume moved
        results['volume_moved'].columns = ['scenario', 'period_1', 'period_2', 'product', 
                                         'departing_node', 'receiving_node', 'volume_moved']
        results['pop_cost'].columns = ['scenario', 'period_1', 'period_2', 'product', 
                                     'departing_node', 'receiving_node', 'plan_over_plan_change_cost']
        results['num_destinations_moved'].columns = ['scenario', 'period_1', 'period_2', 'product',
                                                   'departing_node', 'receiving_node', 'number_of_destinations_moved']
        
        # Plan over plan changes
        results['m_plan_over_plan_changes'] = results['volume_moved'].merge(
            results['num_destinations_moved'], how='outer'
        )
        results['m_plan_over_plan_changes'] = results['m_plan_over_plan_changes'].merge(
            results['pop_cost'], how='outer'
        )
        
        # Node launches and shutdowns
        results['m_node_launches_and_shutdowns'] = results['is_launched'].merge(
            results['total_launch_cost'], how='outer'
        )
        results['m_node_launches_and_shutdowns'] = results['m_node_launches_and_shutdowns'].merge(
            results['is_shut_down'], how='outer'
        )
        results['m_node_launches_and_shutdowns'] = results['m_node_launches_and_shutdowns'].merge(
            results['total_shut_down_cost'], how='outer'
        )
        
        # Capacity expansions
        results['m_capacity_expansions'] = results['use_carrying_capacity_option'].merge(
            results['c_capacity_option_cost'], how='outer'
        )
        results['m_capacity_expansions'] = results['m_capacity_expansions'].merge(
            results['use_transportation_capacity_option'], how='outer'
        )
        results['m_capacity_expansions'] = results['m_capacity_expansions'].merge(
            results['t_capacity_option_cost'], how='outer'
        )
        
        # Resources
        results['m_resources_assigned_added_removed'] = results['resources_assigned'].merge(
            results['resource_time_cost'], how='outer'
        )
        results['m_resources_assigned_added_removed'] = results['m_resources_assigned_added_removed'].merge(
            results['resources_added'], how='outer'
        )
        results['m_resources_assigned_added_removed'] = results['m_resources_assigned_added_removed'].merge(
            results['resource_add_cost'], how='outer'
        )
        results['m_resources_assigned_added_removed'] = results['m_resources_assigned_added_removed'].merge(
            results['resources_removed'], how='outer'
        )
        results['m_resources_assigned_added_removed'] = results['m_resources_assigned_added_removed'].merge(
            results['resource_remove_cost'], how='outer'
        )
        
        # Node utilization
        results['m_node_resource_utilization'] = results['node_utilization']
        
        return results