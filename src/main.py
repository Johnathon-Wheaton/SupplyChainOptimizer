import pandas as pd
import numpy as np
import pulp
from datetime import datetime
from itertools import product
import os.path
import logging
from logging.handlers import RotatingFileHandler
import re
from typing import Dict, Any, List, Set, Tuple
from data.writers import ExcelWriter
from models.network import Network
from optimization.constraints import FlowConstraints, AgeConstraints, TransportationConstraints,  ResourceConstraints, CapacityConstraints, CostConstraints
from optimization.objectives.objective_handler import ObjectiveHandler
from optimization.solvers import MILPSolver
from data.preprocessors import DataPreprocessor
from data.processors import ResultsProcessor
from data.processors import ScenarioProcessor
from data.processors import ParameterProcessor
from optimization.variables import VariableCreator
from config import Settings
from utils import NetworkOptimizerLogger, log_execution_time, TimedOperation, SolverProgressLogger
import argparse
from pathlib import Path
from data.readers import create_reader

def read_input_file(file):
    reader = create_reader(file)
    return reader.read()

def export_results(results, output_file_name):
    writer = ExcelWriter(output_file_name)
    writer.write(results)

def get_solver_results(model, objectives_input, parameters_input, list_of_sets, list_of_parameters, variables, settings):
    objectives_input_ordered = objectives_input.sort_values(by='Priority')
    priority_list = objectives_input_ordered['Priority'].unique()
    base_model = model
    
    # Create objective handler
    objective_handler = ObjectiveHandler(variables, list_of_sets, list_of_parameters)
    
    # Create solver
    solver = pulp.HiGHS_CMD(path = settings.solver.solver_file_path,
        timeLimit=settings.solver.max_run_time,
        gapRel=settings.solver.gap_limit
    )
    
    for x in priority_list:
        logging.info(f"Solving for objective {x} of {len(priority_list)}")
        logging.info(f"Objective: {objectives_input_ordered[objectives_input_ordered['Priority'] == x]['Objective'].iloc[0]}")
        
        is_multi_objective = len(objectives_input_ordered[objectives_input_ordered['Priority'] == x]) > 1
        if x < max(priority_list):
            model_w_objective = base_model.copy()
            for m in objectives_input_ordered[objectives_input_ordered['Priority']==x]['Objective']:
                objective_handler.set_single_objective(model_w_objective, m)
                    
            base_model = objective_handler.solve_and_set_constraint(
                model_w_objective,
                objectives_input_ordered[objectives_input_ordered['Priority']==x]['Objective'],
                objectives_input_ordered[objectives_input_ordered['Priority']==x]['Relaxation'],
                solver
            )
        else:
            model_w_objective = base_model.copy()
            for m in objectives_input_ordered[objectives_input_ordered['Priority']==x]['Objective']:
                objective_handler.set_single_objective(model_w_objective, m)
                    
            result = model_w_objective.solve(solver)
            
    return result

def run_solver(input_values, settings):
    start_time = datetime.now()
    
    # Split all * scenarios
    input_values = DataPreprocessor.split_scenarios(input_values)
    
    # Inputs independent of scenario
    parameters_input = input_values['parameters_input']
    settings.solver.max_run_time = parameters_input['Max Run Time'][0]
    settings.solver.gap_limit = parameters_input['Gap Limit'][0]

    objectives_input = input_values['objectives_input']
    periods_input = input_values['periods_input']
    products_input = input_values['products_input']
    od_distances_and_transit_times_input = input_values['od_distances_and_transit_times_input']
    resource_capacity_types_input = input_values['resource_capacity_types_input']
    
    SCENARIOS = objectives_input['Scenario'].unique()
    for s in SCENARIOS:

        # Filter dataframes for current scenario
        filtered_dataframes = {
            # Include scenario-independent dataframes
            'parameters_input': parameters_input,
            'periods_input': periods_input,
            'products_input': products_input,
            'od_distances_and_transit_times_input': od_distances_and_transit_times_input,
            'resource_capacity_types_input': resource_capacity_types_input,
        }
        
        # Filter scenario-dependent dataframes
        scenario_dependent_dfs = [
            "scenarios_input", "objectives_input", "nodes_input", 
            "node_shut_down_launch_hard_constraints_input", "node_types_input",
            "flow_input", "fixed_operating_costs_input", "node_groups_input",
            "variable_operating_costs_input", "transportation_costs_input",
            "load_capacity_input", "transportation_constraints_input", 
            "transportation_expansions_input", "transportation_expansion_capacities_input",
            "carrying_or_missed_demand_cost_input", "demand_input",  
            "resource_capacity_consumption_input", "carrying_expansions_input",  
            "pop_demand_change_const_input", "resource_capacities_input",
            "node_resource_constraints_input", "resource_attribute_constraints_input",
            "resource_attributes_input", "resource_costs_input",
            "resource_initial_counts_input", "max_transit_time_distance_input", 
            "carrying_or_missed_demand_constraints_input", "carrying_capacity_input",
            "product_transportation_groups_input", "age_constraints_input",
            "processing_assembly_constraints_input", "shipping_assembly_constraints_input"
        ]
        
        for df_name in scenario_dependent_dfs:
            df = input_values[df_name]
            filtered_df = df[(df['Scenario'] == s) | (df['Scenario'] == "*")]
            filtered_dataframes[df_name] = filtered_df

        # Assign filtered dataframes to variables for easier access
        objectives_input = filtered_dataframes['objectives_input']

        # Create network model and get sets
        network = Network(filtered_dataframes)
        list_of_sets = network.get_all_sets()

        filtered_dataframes = DataPreprocessor.preprocess_data(filtered_dataframes, list_of_sets)

        # Create parameters
        parameter_processor = ParameterProcessor()
        list_of_parameters = parameter_processor.create_all_parameters(filtered_dataframes)

        model = pulp.LpProblem(name="My_Model", sense=pulp.LpMinimize)

        # Create variables
        variable_creator = VariableCreator(list_of_sets)
        variables, dimensions = variable_creator.create_all_variables()

        # Create constraint handlers
        flow_constraints = FlowConstraints(variables, list_of_sets, list_of_parameters)
        age_constraints = AgeConstraints(variables, list_of_sets, list_of_parameters)
        transportation_constraints = TransportationConstraints(variables, list_of_sets, list_of_parameters)
        resource_constraints = ResourceConstraints(variables, list_of_sets, list_of_parameters)
        capacity_constraints = CapacityConstraints(variables, list_of_sets, list_of_parameters)
        cost_constraints = CostConstraints(variables, list_of_sets, list_of_parameters)

        # Add constraints to model
        flow_constraints.build(model)
        age_constraints.build(model)
        transportation_constraints.build(model)
        resource_constraints.build(model)
        capacity_constraints.build(model)
        cost_constraints.build(model)

        solve_start =datetime.now()
        result = get_solver_results(model,objectives_input,parameters_input,list_of_sets,list_of_parameters,variables, settings)
        logging.info(f"Solver time: {round((datetime.now() - solve_start).seconds, 0)} seconds.")

        output_results = {}
        output_results['variables'] = variables
        output_results['model']=result
        output_results['sets']=list_of_sets
        output_results['dimensions']=dimensions
        
        if s == SCENARIOS[0]:
            if result != -1:
                results = ResultsProcessor.get_results_dictionary(output_results)
                results = ScenarioProcessor.add_scenario_column_to_results(results, s)
            else:
                results = {'no_solution': pd.DataFrame({'scenario':[s]})}
        else:
            if result !=-1:
                scenario_results = ResultsProcessor.get_results_dictionary(output_results)
                scenario_results = ScenarioProcessor.add_scenario_column_to_results(scenario_results, s)
                results = ScenarioProcessor.append_scenario_results(results,scenario_results)
                results = ResultsProcessor.add_merged_tables(results)
            else:
                if 'no_solution' in results:
                    results['no_solution'] = pd.concat([results['no_solution'], pd.DataFrame({'scenario':[s]})])
                else:
                    results.update({'no_solution': pd.DataFrame({'scenario':[s]})})
        print(f"Total run time: {round((datetime.now() - start_time).seconds, 0)} seconds.")
    return(results)

def optimize_network(file: str, settings: Settings = None) -> Dict[str, Any]:
    """Run network optimization
    
    Args:
        file: Input file path
        settings: Optional Settings object for configuration
    
    Returns:
        Dictionary containing optimization results
    """
    #Use default settings if none provided
    if settings is None:
        settings = Settings()
    
    # Configure logging
    app_log = logging.getLogger('root')
    app_log.setLevel(settings.logging.log_level)
    handler = RotatingFileHandler(
        settings.logging.log_file,
        maxBytes=settings.logging.max_file_size,
        backupCount=settings.logging.backup_count
    )
    app_log.addHandler(handler)

    # Read input data
    input_values = read_input_file(file)

    results = run_solver(input_values, settings)
    return(results)

def main():
    parser = argparse.ArgumentParser(description='Optimize network')
    parser.add_argument('input', help='Path to input Excel or json file')
    parser.add_argument('--output', '-o', help='Path to output excel file')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Set the logging level')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"File not found: {input_path}")
    output_path = Path(args.output)
    if not output_path.exists():
        raise FileNotFoundError(f"File not found: {output_path}")
    
    # script_dir = os.path.dirname(__file__) 
    # input_file_path = os.path.join(script_dir,"examples/demo_inputs_transportation_facility_location.json")
    results = optimize_network(input_path)
    # output_file_path = os.path.join(script_dir,"examples/demo_inputs_transportation_facility_location_results.xlsx")
    export_results(results, output_path)

if __name__ == "__main__":
    main()