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
from data.readers import ExcelReader
from data.writers import ExcelWriter
from models.network import Network
from optimization.constraints import FlowConstraints, AgeConstraints, TransportationConstraints,  ResourceConstraints, CapacityConstraints
from optimization.objectives.objective_handler import ObjectiveHandler
from optimization.solvers import MILPSolver
from data.preprocessors import DataPreprocessor
from data.processors import ResultsProcessor
from data.processors import ScenarioProcessor
from data.processors import ParameterProcessor
from optimization.variables import VariableCreator
from config import Settings
from utils import NetworkOptimizerLogger, log_execution_time, TimedOperation, SolverProgressLogger

def read_input_file(file):
    reader = ExcelReader(file)
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
    big_m = settings.network.big_m
    
    # Split all * scenarios
    input_values = DataPreprocessor.split_scenarios(input_values)
    
    # Inputs independent of scenario
    parameters_input = input_values['parameters_input']
    settings.solver.max_run_time = parameters_input['Max Run Time'][1]
    settings.solver.gap_limit = parameters_input['Gap Limit'][1]

    objectives_input = input_values['objectives_input']
    periods_input = input_values['periods_input']
    products_input = input_values['products_input']
    od_distances_and_transit_times_input = input_values['od_distances_and_transit_times_input']
    resource_capacity_types_input = input_values['resource_capacity_types_input']
    
    SCENARIOS = objectives_input['Scenario'].unique()
    for s in SCENARIOS:
        logging.info(f"Starting scenario {s}.")
        format_inputs_start = datetime.now()
        
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
        scenarios_input = filtered_dataframes['scenarios_input']
        objectives_input = filtered_dataframes['objectives_input']

        # Create network model and get sets
        network = Network(filtered_dataframes)
        list_of_sets = network.get_all_sets()

        # Define individual sets (needed for existing code)
        NODES = list_of_sets["NODES"]
        NODETYPES = list_of_sets["NODETYPES"]
        NODEGROUPS = list_of_sets["NODEGROUPS"]
        ORIGINS = list_of_sets["ORIGINS"]
        DESTINATIONS = list_of_sets["DESTINATIONS"]
        RECEIVE_FROM_ORIGIN_NODES = list_of_sets["RECEIVE_FROM_ORIGIN_NODES"]
        RECEIVE_FROM_INTERMEDIATES_NODES = list_of_sets["RECEIVE_FROM_INTERMEDIATES_NODES"]
        SEND_TO_DESTINATIONS_NODES = list_of_sets["SEND_TO_DESTINATIONS_NODES"]
        SEND_TO_INTERMEDIATES_NODES = list_of_sets["SEND_TO_INTERMEDIATES_NODES"]
        INTERMEDIATES = list_of_sets["INTERMEDIATES"]
        DEPARTING_NODES = list_of_sets["DEPARTING_NODES"]
        RECEIVING_NODES = list_of_sets["RECEIVING_NODES"]
        PERIODS = list_of_sets["PERIODS"]
        AGES = list_of_sets["AGES"]
        PRODUCTS = list_of_sets["PRODUCTS"]
        MEASURES = list_of_sets["MEASURES"]
        CONTAINERS = list_of_sets["CONTAINERS"]
        MODES = list_of_sets["MODES"]
        C_CAPACITY_EXPANSIONS = list_of_sets["C_CAPACITY_EXPANSIONS"]
        T_CAPACITY_EXPANSIONS = list_of_sets["T_CAPACITY_EXPANSIONS"]
        TRANSPORTATION_GROUPS = list_of_sets["TRANSPORTATION_GROUPS"]
        RESOURCES = list_of_sets["RESOURCES"]
        RESOURCE_CAPACITY_TYPES = list_of_sets["RESOURCE_CAPACITY_TYPES"]
        RESOURCE_PARENT_CAPACITY_TYPES = list_of_sets["RESOURCE_PARENT_CAPACITY_TYPES"]
        RESOURCE_CHILD_CAPACITY_TYPES = list_of_sets["RESOURCE_CHILD_CAPACITY_TYPES"]
        RESOURCE_ATTRIBUTES = list_of_sets["RESOURCE_ATTRIBUTES"]

        #set binary node to node group assignment
        filtered_dataframes['node_groups_input']['assigned'] = 1
        filtered_dataframes['node_groups_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_groups_input'], 'Group', NODEGROUPS)
        filtered_dataframes['node_groups_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_groups_input'], 'Node', NODES)
        
        filtered_dataframes['node_shut_down_launch_hard_constraints_input'].loc[(filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Launch'].isna()==False )&( filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Launch']!=0),'Launch']=1
        filtered_dataframes['node_shut_down_launch_hard_constraints_input'].loc[(filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Launch'].isna() )|( filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Launch']==0),'Launch']=0
        filtered_dataframes['node_shut_down_launch_hard_constraints_input'].loc[(filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Shutdown'].isna()==False )&( filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Shutdown']!=0),'Shutdown']=1
        filtered_dataframes['node_shut_down_launch_hard_constraints_input'].loc[(filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Shutdown'].isna() )|( filtered_dataframes['node_shut_down_launch_hard_constraints_input']['Shutdown']==0),'Shutdown']=0

        # Demand splits
        filtered_dataframes['demand_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['demand_input'], 'Period', PERIODS)
        filtered_dataframes['demand_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['demand_input'], "Product", PRODUCTS)
        filtered_dataframes['demand_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['demand_input'], "Destination", RECEIVING_NODES)

        # Age constraints splits
        filtered_dataframes['age_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['age_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['age_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['age_constraints_input'], "Product", PRODUCTS)
        filtered_dataframes['age_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['age_constraints_input'], "Destination", NODES)
        filtered_dataframes['age_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['age_constraints_input'], "Age", AGES)
        filtered_dataframes['age_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['age_constraints_input'], "Destination Node Group", NODEGROUPS)

        # Resource capacity consumption splits
        filtered_dataframes['resource_capacity_consumption_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacity_consumption_input'], 'Period', PERIODS)
        filtered_dataframes['resource_capacity_consumption_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacity_consumption_input'], 'Product', PRODUCTS)
        filtered_dataframes['resource_capacity_consumption_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacity_consumption_input'], 'Node', NODES)
        filtered_dataframes['resource_capacity_consumption_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacity_consumption_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['resource_capacity_consumption_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacity_consumption_input'], 'Capacity Type', RESOURCE_CHILD_CAPACITY_TYPES)
        
        # Resource costs splits
        filtered_dataframes['resource_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_costs_input'], 'Period', PERIODS)
        filtered_dataframes['resource_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_costs_input'], 'Resource', RESOURCES)
        filtered_dataframes['resource_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_costs_input'], 'Node', NODES)
        filtered_dataframes['resource_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_costs_input'], 'Node Group', NODEGROUPS)

        # Resource capacities splits
        filtered_dataframes['resource_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacities_input'], 'Period', PERIODS)
        filtered_dataframes['resource_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacities_input'], 'Resource', RESOURCES)
        filtered_dataframes['resource_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacities_input'], 'Node', NODES)
        filtered_dataframes['resource_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacities_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['resource_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_capacities_input'], 'Capacity Type', RESOURCE_CAPACITY_TYPES)
        
        # Resource initial counts splits
        filtered_dataframes['resource_initial_counts_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_initial_counts_input'], 'Resource', RESOURCES)
        filtered_dataframes['resource_initial_counts_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_initial_counts_input'], 'Node', NODES)
        filtered_dataframes['resource_initial_counts_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_initial_counts_input'], 'Node Group', NODEGROUPS)
       
        #fill missing node_resource_constraints_input values with zeros
        filtered_dataframes['node_resource_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_resource_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['node_resource_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_resource_constraints_input'], 'Resource', RESOURCES)
        filtered_dataframes['node_resource_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_resource_constraints_input'], 'Node', NODES)
        filtered_dataframes['node_resource_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_resource_constraints_input'], 'Node Group', NODEGROUPS)
        ####### To be removed ######

        # Splitting and filling node_types_input
        filtered_dataframes['node_types_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['node_types_input'], 'Period', PERIODS)
        #############################

        node_type_input = filtered_dataframes['nodes_input'][['Name','Node Type']].copy()
        node_type_input['value']=1
        node_type_input = DataPreprocessor.fill_missing_values(
            node_type_input,
            value_fields=['value'],
            sets={
                "NODES": NODES,
                "NODETYPES": NODETYPES
            },
            target_columns=['Name','Node Type'],
            fill_with={'value': 0}
        )
        filtered_dataframes['node_type_input'] = node_type_input

        # Splitting and filling for od_distances_and_transit_times_input
        od_distances_and_transit_times_input = DataPreprocessor.split_asterisk_values(od_distances_and_transit_times_input, 'Mode', MODES)

        # Filling missing values for transportation_costs_input
        # Transportation costs splits
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Period', PERIODS)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values( filtered_dataframes['transportation_costs_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Destination Node Group', NODEGROUPS)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Mode', MODES)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Container', CONTAINERS)
        filtered_dataframes['transportation_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_costs_input'], 'Measure', MEASURES)

        # Load capacity splits
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Period', PERIODS)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Destination Node Group', NODEGROUPS)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Mode', MODES)
        filtered_dataframes['load_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['load_capacity_input'], 'Measure', MEASURES)

        # Create capacity hierarchy table
        filtered_dataframes['capacity_type_hierarchy_input'] = resource_capacity_types_input[~resource_capacity_types_input['Parent Capacity Type'].isna()]

        # Filling missing values for transportation_constraints_input
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Destination Node Group', NODEGROUPS)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Mode', MODES)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Measure', MEASURES)
        filtered_dataframes['transportation_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_constraints_input'], 'Container', CONTAINERS)
        
        # Transportation expansions splits
        filtered_dataframes['transportation_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansions_input'], 'Period', PERIODS)
        filtered_dataframes['transportation_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansions_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['transportation_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansions_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['transportation_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansions_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['transportation_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansions_input'], 'Destination Node Group', NODEGROUPS)
        filtered_dataframes['transportation_expansion_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansion_capacities_input'], 'Mode', MODES)
        filtered_dataframes['transportation_expansion_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansion_capacities_input'], 'Measure', MEASURES)
        filtered_dataframes['transportation_expansion_capacities_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['transportation_expansion_capacities_input'], 'Container', CONTAINERS)

        # Carrying expansions splits
        filtered_dataframes['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_expansions_input'], 'Location', NODES)
        filtered_dataframes['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_expansions_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_expansions_input'], 'Period', PERIODS)
        filtered_dataframes['carrying_expansions_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_expansions_input'], 'Incremental Capacity Label', C_CAPACITY_EXPANSIONS)
        
        # PoP demand change splits
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Product', PRODUCTS)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Period 1', PERIODS)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Period 2', PERIODS)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['pop_demand_change_const_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['pop_demand_change_const_input'], 'Destination Node Group', NODEGROUPS)
    
        # Max transit time/distance splits
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Destination Node Group', NODEGROUPS)
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Period', PERIODS)
        filtered_dataframes['max_transit_time_distance_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['max_transit_time_distance_input'], 'Mode', MODES)

        # Carrying/missed demand cost splits
        filtered_dataframes['carrying_or_missed_demand_cost_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_cost_input'], 'Period', PERIODS)
        filtered_dataframes['carrying_or_missed_demand_cost_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_cost_input'], 'Product', PRODUCTS)
        filtered_dataframes['carrying_or_missed_demand_cost_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_cost_input'], 'Node', NODES)
        filtered_dataframes['carrying_or_missed_demand_cost_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_cost_input'], 'Node Group', NODEGROUPS)

        # Carrying/missed demand constraints
        filtered_dataframes['carrying_or_missed_demand_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['carrying_or_missed_demand_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_constraints_input'], 'Product', PRODUCTS)
        filtered_dataframes['carrying_or_missed_demand_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_constraints_input'], 'Node', NODES)
        filtered_dataframes['carrying_or_missed_demand_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_or_missed_demand_constraints_input'], 'Node Group', NODEGROUPS)

        # Carrying capacity
        filtered_dataframes['carrying_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_capacity_input'], 'Period', PERIODS)
        filtered_dataframes['carrying_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_capacity_input'], 'Node', NODES)
        filtered_dataframes['carrying_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_capacity_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['carrying_capacity_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['carrying_capacity_input'], 'Measure', MEASURES)

        # Fixed operating costs splits
        filtered_dataframes['fixed_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['fixed_operating_costs_input'], 'Period', PERIODS)
        filtered_dataframes['fixed_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['fixed_operating_costs_input'], 'Name', NODES)
        filtered_dataframes['fixed_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['fixed_operating_costs_input'], 'Node Group', NODEGROUPS)

        # Variable operating costs
        filtered_dataframes['variable_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['variable_operating_costs_input'], 'Period', PERIODS)
        filtered_dataframes['variable_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['variable_operating_costs_input'], 'Name', NODES)
        filtered_dataframes['variable_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['variable_operating_costs_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['variable_operating_costs_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['variable_operating_costs_input'], 'Product', PRODUCTS)

        # Product transportation groups splits
        filtered_dataframes['product_transportation_groups_input']['value'] = 1
        filtered_dataframes['product_transportation_groups_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['product_transportation_groups_input'], 'Product', PRODUCTS)

        # Filling missing values for flow_input
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Period', PERIODS)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Node', DEPARTING_NODES)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Downstream Node', RECEIVING_NODES)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Downstream Node Group', NODEGROUPS)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Product', PRODUCTS)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Mode', MODES)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Container', CONTAINERS)
        filtered_dataframes['flow_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['flow_input'], 'Measure', MEASURES)

        # Processing assembly constraints splits
        filtered_dataframes['processing_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['processing_assembly_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['processing_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['processing_assembly_constraints_input'], 'Product 1', PRODUCTS)
        filtered_dataframes['processing_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['processing_assembly_constraints_input'], 'Product 2', PRODUCTS)
        filtered_dataframes['processing_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['processing_assembly_constraints_input'], 'Node', NODES)
        filtered_dataframes['processing_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['processing_assembly_constraints_input'], 'Node Group', NODEGROUPS)

        # Shipping assembly constraints
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Product 1', PRODUCTS)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Product 2', PRODUCTS)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Origin', DEPARTING_NODES)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Destination', RECEIVING_NODES)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Origin Node Group', NODEGROUPS)
        filtered_dataframes['shipping_assembly_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['shipping_assembly_constraints_input'], 'Destination Node Group', NODEGROUPS)
    
        # Resource attributes splits
        filtered_dataframes['resource_attributes_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attributes_input'], 'Resource Attribute', RESOURCE_ATTRIBUTES)
        filtered_dataframes['resource_attributes_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attributes_input'], 'Period', PERIODS)

        # Resource attribute constraints
        filtered_dataframes['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attribute_constraints_input'], 'Node Group', NODEGROUPS)
        filtered_dataframes['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attribute_constraints_input'], 'Period', PERIODS)
        filtered_dataframes['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attribute_constraints_input'], 'Resource', RESOURCES)
        filtered_dataframes['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attribute_constraints_input'], 'Node', NODES)
        filtered_dataframes['resource_attribute_constraints_input'] = DataPreprocessor.split_asterisk_values(filtered_dataframes['resource_attribute_constraints_input'], 'Resource Attribute', RESOURCE_ATTRIBUTES)
        
        # Create parameters
        parameter_processor = ParameterProcessor()
        list_of_parameters = parameter_processor.create_all_parameters(filtered_dataframes)
        node_in_nodegroup = list_of_parameters['node_in_nodegroup']
        distance = list_of_parameters['distance']
        transit_time = list_of_parameters['transit_time']
        transport_periods = list_of_parameters['transport_periods']
        demand = list_of_parameters['demand']
        max_vol_by_age = list_of_parameters['max_vol_by_age']
        age_constraint_violation_cost = list_of_parameters['age_constraint_violation_cost']
        flow_constraints_min = list_of_parameters['flow_constraints_min']
        flow_constraints_max = list_of_parameters['flow_constraints_max']
        flow_constraints_min_pct_ob = list_of_parameters['flow_constraints_min_pct_ob']
        flow_constraints_max_pct_ob = list_of_parameters['flow_constraints_max_pct_ob']
        flow_constraints_min_pct_ib = list_of_parameters['flow_constraints_min_pct_ib']
        flow_constraints_max_pct_ib = list_of_parameters['flow_constraints_max_pct_ib']
        flow_constraints_min_connections = list_of_parameters['flow_constraints_min_connections']
        flow_constraints_max_connections = list_of_parameters['flow_constraints_max_connections']
        processing_assembly_p1_required = list_of_parameters['processing_assembly_p1_required']
        processing_assembly_p2_required = list_of_parameters['processing_assembly_p2_required']
        shipping_assembly_p1_required = list_of_parameters['shipping_assembly_p1_required']
        shipping_assembly_p2_required = list_of_parameters['shipping_assembly_p2_required']
        transportation_cost_fixed = list_of_parameters['transportation_cost_fixed']
        transportation_cost_variable_distance = list_of_parameters['transportation_cost_variable_distance']
        transportation_cost_variable_time = list_of_parameters['transportation_cost_variable_time']
        transportation_cost_minimum = list_of_parameters['transportation_cost_minimum']
        products_measures = list_of_parameters['products_measures']
        operating_costs_variable = list_of_parameters['operating_costs_variable']
        capacity_consumption_periods = list_of_parameters['capacity_consumption_periods']
        delay_periods = list_of_parameters['delay_periods']
        load_capacity = list_of_parameters['load_capacity']
        capacity_type_hierarchy = list_of_parameters['capacity_type_hierarchy']
        transportation_constraints_min = list_of_parameters['transportation_constraints_min']
        transportation_constraints_max = list_of_parameters['transportation_constraints_max']
        transportation_expansion_capacity = list_of_parameters['transportation_expansion_capacity']
        transportation_expansion_cost = list_of_parameters['transportation_expansion_cost']
        transportation_expansion_persisting_cost = list_of_parameters['transportation_expansion_persisting_cost']
        transportation_expansion_min_count = list_of_parameters['transportation_expansion_min_count']
        transportation_expansion_max_count = list_of_parameters['transportation_expansion_max_count']
        ib_carrying_expansion_capacity = list_of_parameters['ib_carrying_expansion_capacity']
        ob_carrying_expansion_capacity = list_of_parameters['ob_carrying_expansion_capacity']
        carrying_expansions = list_of_parameters['carrying_expansions']
        carrying_expansions_persisting_cost = list_of_parameters['carrying_expansions_persisting_cost']
        pop_cost_per_move = list_of_parameters['pop_cost_per_move']
        pop_cost_per_volume_moved = list_of_parameters['pop_cost_per_volume_moved']
        pop_max_destinations_moved = list_of_parameters['pop_max_destinations_moved']
        max_distance = list_of_parameters['max_distance']
        max_transit_time = list_of_parameters['max_transit_time']
        operating_costs_fixed = list_of_parameters['operating_costs_fixed']
        launch_cost = list_of_parameters['launch_cost']
        shut_down_cost = list_of_parameters['shut_down_cost']
        min_launch_count = list_of_parameters['min_launch_count']
        max_launch_count = list_of_parameters['max_launch_count']
        min_operating_duration = list_of_parameters['min_operating_duration']
        max_operating_duration = list_of_parameters['max_operating_duration']
        min_shut_down_count = list_of_parameters['min_shut_down_count']
        max_shut_down_count = list_of_parameters['max_shut_down_count']
        min_shut_down_duration = list_of_parameters['min_shut_down_duration']
        max_shut_down_duration = list_of_parameters['max_shut_down_duration']
        launch_hard_constraint = list_of_parameters['launch_hard_constraint']
        shut_down_hard_constraint = list_of_parameters['shut_down_hard_constraint']
        ib_carrying_cost = list_of_parameters['ib_carrying_cost']
        ob_carrying_cost = list_of_parameters['ob_carrying_cost']
        dropping_cost = list_of_parameters['dropping_cost']
        ib_max_carried = list_of_parameters['ib_max_carried']
        ob_max_carried = list_of_parameters['ob_max_carried']
        max_dropped = list_of_parameters['max_dropped']
        ib_carrying_capacity = list_of_parameters['ib_carrying_capacity']
        ob_carrying_capacity = list_of_parameters['ob_carrying_capacity']
        period_weight = list_of_parameters['period_weight']
        transportation_group = list_of_parameters['transportation_group']
        node_types_min = list_of_parameters['node_types_min']
        node_types_max = list_of_parameters['node_types_max']
        resource_fixed_add_cost = list_of_parameters['resource_fixed_add_cost']
        resource_cost_per_time = list_of_parameters['resource_cost_per_time']
        resource_fixed_remove_cost = list_of_parameters['resource_fixed_remove_cost']
        resource_add_cohort_count = list_of_parameters['resource_add_cohort_count']
        resource_remove_cohort_count = list_of_parameters['resource_remove_cohort_count']
        resource_capacity_by_type = list_of_parameters['resource_capacity_by_type']
        resource_node_min_count = list_of_parameters['resource_node_min_count']
        resource_node_max_count = list_of_parameters['resource_node_max_count']
        resource_node_initial_count = list_of_parameters['resource_node_initial_count']
        resource_capacity_consumption = list_of_parameters['resource_capacity_consumption']
        resource_capacity_consumption_periods = list_of_parameters['resource_capacity_consumption_periods']
        resource_attribute_consumption_per = list_of_parameters['resource_attribute_consumption_per']
        resource_attribute_min = list_of_parameters['resource_attribute_min']
        resource_attribute_max = list_of_parameters['resource_attribute_max']
        resource_min_to_remove = list_of_parameters['resource_min_to_remove']
        resource_max_to_remove = list_of_parameters['resource_max_to_remove']
        resource_min_to_add = list_of_parameters['resource_min_to_add']
        resource_max_to_add = list_of_parameters['resource_max_to_add']
       
        logging.info(f"Done formatting inputs. {round((datetime.now() - format_inputs_start).seconds, 0)} seconds.")
        compile_model_start = datetime.now()

        model = pulp.LpProblem(name="My_Model", sense=pulp.LpMinimize)

        # Create variables
        variable_creator = VariableCreator(list_of_sets)
        variables, dimensions = variable_creator.create_all_variables()

        # Extract individual variables for existing constraint definitions
        departed_product_by_mode = variables['departed_product_by_mode']
        departed_product = variables['departed_product']
        processed_product = variables['processed_product']
        arrived_product = variables['arrived_product']
        use_carrying_capacity_option = variables['use_carrying_capacity_option']
        use_transportation_capacity_option = variables['use_transportation_capacity_option']
        arrived_and_completed_product = variables['arrived_and_completed_product']
        total_arrived_and_completed_product = variables['total_arrived_and_completed_product']
        resources_assigned = variables['resources_assigned']
        resources_added = variables['resources_added']
        resources_removed = variables['resources_removed']
        resource_capacity = variables['resource_capacity']
        resource_attribute_consumption = variables['resource_attribute_consumption']
        ib_carried_over_demand = variables['ib_carried_over_demand']
        ob_carried_over_demand = variables['ob_carried_over_demand']
        dropped_demand = variables['dropped_demand']
        resources_added_binary = variables['resources_added_binary']
        resources_removed_binary = variables['resources_removed_binary']
        resource_cohorts_added = variables['resource_cohorts_added']
        resource_cohorts_removed = variables['resource_cohorts_removed']
        resource_add_cost = variables['resource_add_cost']
        resource_remove_cost = variables['resource_remove_cost']
        resource_time_cost = variables['resource_time_cost']
        resource_grand_total_cost = variables['resource_grand_total_cost']
        variable_transportation_costs = variables['variable_transportation_costs']
        fixed_transportation_costs = variables['fixed_transportation_costs']
        transportation_costs = variables['transportation_costs']
        od_transportation_costs = variables['od_transportation_costs']
        mode_transportation_costs = variables['mode_transportation_costs']
        total_od_transportation_costs = variables['total_od_transportation_costs']
        total_mode_transportation_costs = variables['total_mode_transportation_costs']
        total_time_transportation_costs = variables['total_time_transportation_costs']
        grand_total_transportation_costs = variables['grand_total_transportation_costs']
        num_loads_by_group = variables['num_loads_by_group']
        num_loads = variables['num_loads']
        od_num_loads = variables['od_num_loads']
        mode_num_loads = variables['mode_num_loads']
        total_od_num_loads = variables['total_od_num_loads']
        total_mode_num_loads = variables['total_mode_num_loads']
        total_num_loads = variables['total_num_loads']
        grand_total_num_loads = variables['grand_total_num_loads']
        departed_measures = variables['departed_measures']
        vol_arrived_by_age = variables['vol_arrived_by_age']
        ib_vol_carried_over_by_age = variables['ib_vol_carried_over_by_age']
        ob_vol_carried_over_by_age = variables['ob_vol_carried_over_by_age']
        vol_processed_by_age = variables['vol_processed_by_age']
        vol_departed_by_age = variables['vol_departed_by_age']
        vol_dropped_by_age = variables['vol_dropped_by_age']
        demand_by_age = variables['demand_by_age']
        age_violation_cost = variables['age_violation_cost']
        grand_total_age_violation_cost = variables['grand_total_age_violation_cost']
        is_launched = variables['is_launched']
        is_shut_down = variables['is_shut_down']
        is_site_operating = variables['is_site_operating']
        total_launch_cost = variables['total_launch_cost']
        launch_costs_by_period = variables['launch_costs_by_period']
        grand_total_launch_cost = variables['grand_total_launch_cost']
        total_shut_down_cost = variables['total_shut_down_cost']
        shut_down_costs_by_period = variables['shut_down_costs_by_period']
        grand_total_shut_down_cost = variables['grand_total_shut_down_cost']
        pop_cost = variables['pop_cost']
        volume_moved = variables['volume_moved']
        num_destinations_moved = variables['num_destinations_moved']
        total_volume_moved = variables['total_volume_moved']
        total_num_destinations_moved = variables['total_num_destinations_moved']
        grand_total_pop_cost = variables['grand_total_pop_cost']
        binary_product_destination_assignment = variables['binary_product_destination_assignment']
        is_destination_assigned_to_origin = variables['is_destination_assigned_to_origin']
        dropped_volume_cost = variables['dropped_volume_cost']
        ib_carried_volume_cost = variables['ib_carried_volume_cost']
        ob_carried_volume_cost = variables['ob_carried_volume_cost']
        dropped_volume_cost_by_period = variables['dropped_volume_cost_by_period']
        ib_carried_volume_cost_by_period = variables['ib_carried_volume_cost_by_period']
        ob_carried_volume_cost_by_period = variables['ob_carried_volume_cost_by_period']
        dropped_volume_cost_by_product = variables['dropped_volume_cost_by_product']
        ib_carried_volume_cost_by_product = variables['ib_carried_volume_cost_by_product']
        ob_carried_volume_cost_by_product = variables['ob_carried_volume_cost_by_product']
        dropped_volume_cost_by_node = variables['dropped_volume_cost_by_node']
        ib_carried_volume_cost_by_node = variables['ib_carried_volume_cost_by_node']
        ob_carried_volume_cost_by_node = variables['ob_carried_volume_cost_by_node']
        ib_carried_volume_cost_by_node_time = variables['ib_carried_volume_cost_by_node_time']
        ob_carried_volume_cost_by_node_time = variables['ob_carried_volume_cost_by_node_time']
        dropped_volume_cost_by_product_time = variables['dropped_volume_cost_by_product_time']
        ib_carried_volume_cost_by_product_time = variables['ib_carried_volume_cost_by_product_time']
        ob_carried_volume_cost_by_product_time = variables['ob_carried_volume_cost_by_product_time']
        total_dropped_volume_cost = variables['total_dropped_volume_cost']
        total_ib_carried_volume_cost = variables['total_ib_carried_volume_cost']
        total_ob_carried_volume_cost = variables['total_ob_carried_volume_cost']
        grand_total_carried_and_dropped_volume_cost = variables['grand_total_carried_and_dropped_volume_cost']
        max_transit_distance = variables['max_transit_distance']
        max_capacity_utilization = variables['max_capacity_utilization']
        node_utilization = variables['node_utilization']
        variable_operating_costs = variables['variable_operating_costs']
        fixed_operating_costs = variables['fixed_operating_costs']
        operating_costs = variables['operating_costs']
        operating_costs_by_origin = variables['operating_costs_by_origin']
        total_operating_costs = variables['total_operating_costs']
        grand_total_operating_costs = variables['grand_total_operating_costs']
        t_capacity_option_cost = variables['t_capacity_option_cost']
        t_capacity_option_cost_by_location_type = variables['t_capacity_option_cost_by_location_type']
        t_capacity_option_cost_by_period_type = variables['t_capacity_option_cost_by_period_type']
        t_capacity_option_cost_by_location = variables['t_capacity_option_cost_by_location']
        t_capacity_option_cost_by_period = variables['t_capacity_option_cost_by_period']
        t_capacity_option_cost_by_type = variables['t_capacity_option_cost_by_type']
        grand_total_t_capacity_option = variables['grand_total_t_capacity_option']
        c_capacity_option_cost = variables['c_capacity_option_cost']
        c_capacity_option_cost_by_location_type = variables['c_capacity_option_cost_by_location_type']
        c_capacity_option_cost_by_period_type = variables['c_capacity_option_cost_by_period_type']
        c_capacity_option_cost_by_location = variables['c_capacity_option_cost_by_location']
        c_capacity_option_cost_by_period = variables['c_capacity_option_cost_by_period']
        c_capacity_option_cost_by_type = variables['c_capacity_option_cost_by_type']
        grand_total_c_capacity_option = variables['grand_total_c_capacity_option']
        max_age = variables['max_age']
        is_age_received = variables['is_age_received']

        # Flow Constraints

        # set arrived_and_completed_product equal to demand
        for n_r,t,p in product(RECEIVING_NODES,PERIODS,PRODUCTS):
            expr = (arrived_and_completed_product[t, p, n_r] == demand.get((t, p, n_r),0))
            model.addConstraint(expr, f"arrived_and_completed_product_equals_demand_{n_r}_{t}_{p}")
            expr = (arrived_and_completed_product[t, p, n_r] >= demand.get((t, p, n_r),0))
            model.addConstraint(expr, f"arrived_and_completed_product_at_least_demand_{n_r}_{t}_{p}")
        expr = (pulp.lpSum(arrived_and_completed_product[t, p, n_r] for t in PERIODS for p in PRODUCTS for n_r in RECEIVING_NODES) == total_arrived_and_completed_product)
        model.addConstraint(expr, f"total_arrived_and_completed_product_equals_demand")
        # processed volume assembly constraints
        for t, p1, p2, n, g in product(PERIODS, PRODUCTS, PRODUCTS, NODES, NODEGROUPS):
            if node_in_nodegroup.get((n,g),0)==1:
                if processing_assembly_p1_required.get((n,g,p1,p2),None) != None and processing_assembly_p2_required.get((n,g,p1,p2),None) != None:
                    expr = (processed_product[n,p1,t] * processing_assembly_p1_required[n,g,p1,p2] == processed_product[n,p2,t] * processing_assembly_p2_required[n,g,p1,p2])
                    model.addConstraint(expr, f"processed_volume_assembly_constraints_{n}_{t}_{p1}_{p2}")
        
        # shipping volume assembly constraints
        for t, p1, p2, n_d, n_r, g_d, g_r, m in product(PERIODS, PRODUCTS, PRODUCTS, DEPARTING_NODES, RECEIVING_NODES, NODEGROUPS, NODEGROUPS, MODES):
            if node_in_nodegroup.get((n_d,g_d),0)==1 and node_in_nodegroup.get((n_r,g_r),0)==1:
                if shipping_assembly_p1_required.get((n_d,n_r,g_d,g_r,p1,p2),None) != None and shipping_assembly_p2_required.get((n_d,n_r,g_d,g_r,p1,p2),None) != None:
                    expr = (departed_product_by_mode[n_d,n_r,p1,t,m] * shipping_assembly_p1_required[n_d,n_r,g_d,g_r,p1,p2] == departed_product_by_mode[n_d,n_r,p2,t,m] * shipping_assembly_p2_required[n_d,n_r,g_d,g_r,p1,p2])
                    model.addConstraint(expr, f"shipping_volume_assembly_constraints_{n_d}_{n_r}_{t}_{p1}_{p2}_{g_d}_{g_r}_{m}")

        # constraints on itermediate, inhubs and obhubs
        # ib hub can only receive from OB HUBS and origins
        for n, n2, p,t in product(DEPARTING_NODES, RECEIVING_NODES, PRODUCTS, PERIODS):
            max_value = 0
            if n == n2:
                max_value = max_value+ big_m
            if n in ORIGINS and n in SEND_TO_DESTINATIONS_NODES and n2 in DESTINATIONS and n2 in RECEIVE_FROM_ORIGIN_NODES:
                max_value = max_value+ big_m
            if n in ORIGINS and n in SEND_TO_INTERMEDIATES_NODES and n2 in INTERMEDIATES and n2 in RECEIVE_FROM_ORIGIN_NODES:
                max_value = max_value+ big_m
            if n in INTERMEDIATES and n in SEND_TO_DESTINATIONS_NODES and n2 in DESTINATIONS and n2 in RECEIVE_FROM_INTERMEDIATES_NODES:
                max_value = max_value+ big_m
            if n in INTERMEDIATES and n in SEND_TO_INTERMEDIATES_NODES and n2 in INTERMEDIATES and n2 in RECEIVE_FROM_INTERMEDIATES_NODES:
                max_value = max_value+ big_m
            expr = ( departed_product[n,n2,p,t] <=max_value )
            model += expr, f"node_type_constraints_{n}_{n2}_{p}_{t}"

        # Initialize aggregation symbols
        periods = list(PERIODS) + ['@']
        products = list(PRODUCTS) + ['@']
        nodes = list(NODES) + ['@']
        measures = list(MEASURES) + ['@']
        receiving_nodes = list(RECEIVING_NODES) + ['@']
        departing_nodes = list(DEPARTING_NODES) + ['@']

        # Handle dropped demand constraints
        for n_index in nodes:
            for g_index in NODEGROUPS:
                if n_index == '@' or node_in_nodegroup.get((n_index, g_index), 0) == 1:
                    nodes_list = NODES if n_index == '@' else [n_index]
                    
                    for t_index in periods:
                        periods_list = PERIODS if t_index == '@' else [t_index]
                        
                        for p_index in products:
                            products_list = PRODUCTS if p_index == '@' else [p_index]
                            
                            # Calculate dropped demand expression
                            right_exp = pulp.lpSum(dropped_demand[n, p, t] 
                                                for n in nodes_list 
                                                for p in products_list 
                                                for t in periods_list)
                            
                            max_dropped_expr = (max_dropped.get((t_index, p_index, n_index, g_index), big_m) >= right_exp)
                            model += max_dropped_expr, f"Max_Dropped_{t_index}_{p_index}_{n_index}_{g_index}"

        # Handle inbound carried demand constraints
        for n_index in receiving_nodes:
            for g_index in NODEGROUPS:
                if n_index == '@' or node_in_nodegroup.get((n_index, g_index), 0) == 1:
                    nodes_list = RECEIVING_NODES if n_index == '@' else [n_index]
                    for t_index in periods:
                        periods_list = PERIODS if t_index == '@' else [t_index]
                        for p_index in products:
                            products_list = PRODUCTS if p_index == '@' else [p_index]
                            # Calculate inbound carried demand expression
                            right_exp = pulp.lpSum(ib_carried_over_demand[n, p, t] 
                                                for n in nodes_list 
                                                for p in products_list 
                                                for t in periods_list)
                            max_ib_carried_expr = (ib_max_carried.get((t_index, p_index, n_index, g_index), big_m) >= right_exp)
                            model += max_ib_carried_expr, f"IB_Max_Carried_{t_index}_{p_index}_{n_index}_{g_index}"


        # Handle outbound carried demand constraints
        for n_index in departing_nodes:
            for g_index in NODEGROUPS:
                if n_index == '@' or node_in_nodegroup.get((n_index, g_index), 0) == 1:
                    nodes_list = DEPARTING_NODES if n_index == '@' else [n_index]
                    
                    for t_index in periods:
                        periods_list = PERIODS if t_index == '@' else [t_index]
                        
                        for p_index in products:
                            products_list = PRODUCTS if p_index == '@' else [p_index]
                            
                            # Calculate outbound carried demand expression
                            right_exp = pulp.lpSum(ob_carried_over_demand[n, p, t] 
                                                for n in nodes_list 
                                                for p in products_list 
                                                for t in periods_list)
                            
                            max_ob_carried_expr = (ob_max_carried.get((t_index, p_index, n_index, g_index), big_m) >= right_exp)
                            model += max_ob_carried_expr, f"OB_Max_Carried_{t_index}_{p_index}_{n_index}_{g_index}"


        # Adhere to min and max flow constraints - units
        periods = list(PERIODS) + ['@']
        departing_nodes = list(DEPARTING_NODES) + ['@']
        receiving_nodes = list(RECEIVING_NODES) + ['@']
        modes = list(MODES) + ['@']
        measures = list(MEASURES)
        products = list(PRODUCTS) + ['@']
        nodegroups = list(NODEGROUPS) + ['@']
        if flow_constraints_max or flow_constraints_min:
            for o_index in departing_nodes:
                for g_index in nodegroups:
                    if o_index == '@' or node_in_nodegroup.get((o_index, g_index),0)==1:
                        departing_nodes_list = DEPARTING_NODES if o_index=='@' else [o_index]
                        for d_index in receiving_nodes:
                            for g2_index in nodegroups:
                                if d_index == '@' or node_in_nodegroup.get((d_index,g2_index),0) == 1:
                                    receiving_nodes_list = RECEIVING_NODES if d_index=='@' else [d_index]
                                    for t_index  in periods:
                                        periods_list = PERIODS if t_index=='@' else [t_index]
                                        for m_index  in modes:
                                            modes_list = MODES if m_index=='@' else [m_index]
                                            left_exp = transportation_constraints_min.get((  t_index,o_index,d_index,m_index, 'load','count',g_index, g2_index	),0)
                                            right_exp = pulp.lpSum(num_loads[o,d,t,m]	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list  )
                                            min_expr = (
                                                left_exp <= right_exp
                                            )
                                            model += min_expr, f"load_constraints_min_{t_index}_{o_index}_{d_index}_{m_index}_{g_index}_{g2_index}"
                                            
                                            left_exp = transportation_constraints_max.get((  t_index,o_index,d_index,m_index, 'load','count',g_index, g2_index	),big_m)  +  pulp.lpSum(use_transportation_capacity_option[o,d,e,t] * transportation_expansion_capacity.get((e, m_index,'load','count'	),0) for	o in (DEPARTING_NODES if o_index=='@' else [o_index]) for d in (RECEIVING_NODES if d_index=='@' else [d_index]) for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in PRODUCTS  for	e in T_CAPACITY_EXPANSIONS )
                                            max_expr = (
                                                left_exp >= right_exp
                                            )
                                            model += max_expr, f"load_constraints_max_{t_index}_{o_index}_{d_index}_{m_index}_{g_index}_{g2_index}"
                                            
                                            for u_index  in measures:
                                                measures_list = MEASURES if u_index=='@' else [u_index]
                                                if transportation_constraints_min or transportation_constraints_max:
                                                    left_exp = transportation_constraints_min.get((	t_index,o_index,d_index,m_index,'unit',u_index,g_index,g2_index	),0) 
                                                    right_exp = pulp.lpSum(departed_measures[o,d,p,t,m,u]	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in PRODUCTS for u in measures_list )
                                                    transportation_constraints_min_expr = (
                                                        left_exp <= right_exp
                                                    )
                                                    model += transportation_constraints_min_expr, f"transportation_constraints_min_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{g_index}_{g2_index}"
                                                    
                                                    left_exp = transportation_constraints_max.get((	t_index,o_index,d_index,m_index,'unit',u_index,g_index,g2_index	),big_m) +  pulp.lpSum(use_transportation_capacity_option[o,d,e,t] * transportation_expansion_capacity.get((e, m_index,'unit',u_index	),0) for	o in (DEPARTING_NODES if o_index=='@' else [o_index]) for d in (RECEIVING_NODES if d_index=='@' else [d_index]) for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in PRODUCTS for u in (MEASURES if u_index=='@' else [u_index]) for	e in T_CAPACITY_EXPANSIONS )
                                                    transportation_constraints_max_expr = (
                                                        left_exp >= right_exp
                                                    )
                                                    model += transportation_constraints_max_expr, f"transportation_constraints_max_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{g_index}_{g2_index}"
                                                
                                                for p_index in products:
                                                    products_list = PRODUCTS if p_index=='@' else [p_index]
                                                    if products_measures.get((p_index,u_index),'NA') !='NA':
                                                        left_exp = flow_constraints_min.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index	),0)-(big_m*(1-is_launched[o_index,t_index]) if o_index != '@' and t_index != '@' else 0)-(big_m*(1-is_launched[d_index,t_index]) if d_index != '@' and t_index != '@' else 0)
                                                        right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),big_m)	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )
                                                        min_expr = (
                                                            left_exp <= right_exp
                                                        )
                                                        model += min_expr, f"flow_constraints_min_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                        
                                                        left_exp = flow_constraints_max.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index	),big_m) 
                                                        right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0)	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )
                                                        max_expr = (
                                                            left_exp >= right_exp
                                                        )
                                                        model += max_expr, f"flow_constraints_max_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                    
                                                        if flow_constraints_max_pct_ob or flow_constraints_min_pct_ob:
                                                            left_exp = flow_constraints_min_pct_ob.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),0) * pulp.lpSum( departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0) for o in (DEPARTING_NODES if o_index=='@' else [o_index]) for d in RECEIVING_NODES for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in (PRODUCTS if p_index=='@' else [p_index]) for u in (MEASURES if u_index=='@' else [u_index]) ) 
                                                            right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),big_m)	for	o in  departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )+(big_m*is_launched[o_index,t_index] if o_index != '@' and t_index != '@' else 0)+(big_m*is_launched[d_index,t_index] if d_index != '@' and t_index != '@' else 0)
                                                            min_expr = (
                                                                left_exp <= right_exp
                                                            )
                                                            model += min_expr, f"flow_constraints_min_pct_ob_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                            
                                                            left_exp = flow_constraints_max_pct_ob.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),big_m) * pulp.lpSum( departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0) for o in (DEPARTING_NODES if o_index=='@' else [o_index]) for d in RECEIVING_NODES  for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in (PRODUCTS if p_index=='@' else [p_index]) for u in (MEASURES if u_index=='@' else [u_index]) ) 
                                                            right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0)	for	o in  departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )
                                                            max_expr = (
                                                                left_exp >= right_exp
                                                            )
                                                            model += max_expr, f"flow_constraints_max_pct_ob_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"

                                                        if flow_constraints_max_pct_ib or flow_constraints_min_pct_ib:
                                                            left_exp = flow_constraints_min_pct_ib.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),0) * pulp.lpSum( departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0) for	o in DEPARTING_NODES  for d in (RECEIVING_NODES if d_index=='@' else [d_index]) for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in (PRODUCTS if p_index=='@' else [p_index]) for u in (MEASURES if u_index=='@' else [u_index])) 
                                                            right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),big_m)	for	o in  departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )+(big_m*is_launched[o_index,t_index] if o_index != '@' and t_index != '@' else 0)+(big_m*is_launched[d_index,t_index] if d_index != '@' and t_index != '@' else 0)
                                                            min_expr = (
                                                                left_exp <= right_exp
                                                            )
                                                            model += min_expr, f"flow_constraints_min_pct_ib_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                            
                                                            left_exp = flow_constraints_max_pct_ib.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),big_m) * pulp.lpSum(  departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0) for	o in DEPARTING_NODES for d in (RECEIVING_NODES if d_index=='@' else [d_index])  for	t in (PERIODS if t_index=='@' else [t_index]) for m in (MODES if m_index=='@' else [m_index]) for p in (PRODUCTS if p_index=='@' else [p_index]) for u in (MEASURES if u_index=='@' else [u_index])) 
                                                            right_exp = pulp.lpSum(departed_product_by_mode[o,d,p,t,m]*products_measures.get((p,u),0)	for	o in  departing_nodes_list for d in receiving_nodes_list for	t in periods_list for m in modes_list for p in products_list for u in measures_list )
                                                            max_expr = (
                                                                left_exp >= right_exp
                                                            )
                                                            model += max_expr, f"flow_constraints_max_pct_ib_units_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
            logging.info(f"Added flow constraint lower and upper bounds: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        #resource attribute consumption constraints
        resourceattributes = list(RESOURCE_ATTRIBUTES) + ['@']
        resources = list(RESOURCES) + ['@']
        nodes = list(NODES) + ['@']
        if resource_attribute_min or resource_attribute_max:
            for n_index in nodes:
                for g_index in nodegroups:
                    if n_index == '@' or node_in_nodegroup.get((n_index, g_index),0)==1:
                        nodes_list = NODES if n_index=='@' else [n_index]
                        for t_index  in periods:
                            periods_list = PERIODS if t_index=='@' else [t_index]
                            for r_index  in resources:
                                resources_list = RESOURCES if r_index=='@' else [r_index]
                                left_exp = resource_min_to_add.get(( t_index, n_index,r_index, g_index),0)
                                right_exp = pulp.lpSum(resources_added[r,n,t]	for	n in nodes_list for r in resources_list for	t in periods_list  )
                                min_expr = (
                                    left_exp <= right_exp
                                )
                                model += min_expr, f"resources_added_min_{t_index}_{n_index}_{r_index}_{g_index}"
                                
                                left_exp = resource_max_to_add.get(( t_index, n_index,r_index, g_index	),big_m)
                                max_expr = (
                                    left_exp >= right_exp
                                )
                                model += max_expr, f"resource_added_max_{t_index}_{n_index}_{r_index}_{g_index}"

                                left_exp = resource_min_to_remove.get(( t_index, n_index,r_index, g_index),0)
                                right_exp = pulp.lpSum(resources_removed[r,n,t]	for	n in nodes_list for r in resources_list for	t in periods_list  )
                                min_expr = (
                                    left_exp <= right_exp
                                )
                                model += min_expr, f"resources_removed_min_{t_index}_{n_index}_{r_index}_{g_index}"
                                
                                left_exp = resource_max_to_remove.get(( t_index, n_index,r_index, g_index	),big_m)
                                max_expr = (
                                    left_exp >= right_exp
                                )
                                model += max_expr, f"resource_removed_max_{t_index}_{n_index}_{r_index}_{g_index}"

                                resources_list = RESOURCES if r_index=='@' else [r_index]
                                left_exp =resource_node_min_count.get(( t_index, n_index,r_index, g_index),0)
                                right_exp = pulp.lpSum(resources_assigned[r,n,t]	for	n in nodes_list for r in resources_list for	t in periods_list  )
                                min_expr = (
                                    left_exp <= right_exp
                                )
                                model += min_expr, f"resources_total_min_{t_index}_{n_index}_{r_index}_{g_index}"
                                
                                left_exp = resource_node_max_count.get(( t_index, n_index,r_index, g_index	),big_m)
                                max_expr = (
                                    left_exp >= right_exp
                                )
                                model += max_expr, f"resources_total_max_{t_index}_{n_index}_{r_index}_{g_index}"

                                for a_index  in resourceattributes:
                                    resource_attributes_list = RESOURCE_ATTRIBUTES if a_index=='@' else [a_index]
                                    resources_list = RESOURCES if r_index=='@' else [r_index]
                                    left_exp = resource_attribute_min.get(( t_index, n_index,r_index, g_index, a_index	),0)
                                    right_exp = pulp.lpSum(resources_assigned[r,n,t] * resource_attribute_consumption_per.get((t,r,a),0)	for	n in nodes_list for r in resources_list for	t in periods_list for	a in resource_attributes_list  )
                                    min_expr = (
                                        left_exp <= right_exp
                                    )
                                    model += min_expr, f"resource_attribute_min_constraint_{t_index}_{n_index}_{a_index}_{r_index}_{g_index}"
                                    
                                    left_exp = resource_attribute_max.get(( t_index, n_index,r_index, g_index, a_index	),big_m)
                                    max_expr = (
                                        left_exp >= right_exp
                                    )
                                    model += max_expr, f"resource_attribute_max_constraint_{t_index}_{n_index}_{a_index}_{r_index}_{g_index}"
            logging.info(f"Added resource attribute upper and lower bounds: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        # Constraints for capacity option costs

        for t, n, e_c in product(PERIODS, NODES, C_CAPACITY_EXPANSIONS):
            c_constraint_expr = (
                c_capacity_option_cost[t, n, e_c] ==
                period_weight.get((int(t)),1) * use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) +
                use_carrying_capacity_option[n,e_c,t] * pulp.lpSum(carrying_expansions_persisting_cost.get((t2, n, e_c),0) for t2 in PERIODS if int(t2) >= int(t))
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCost_{t}_{n}_{e_c}"

        for n, e_c in product(NODES, C_CAPACITY_EXPANSIONS):
            c_constraint_expr = (
                c_capacity_option_cost_by_location_type[n, e_c] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for t in PERIODS)
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCostByLocationType_{n}_{e_c}"

        for e_c, t in product(C_CAPACITY_EXPANSIONS, PERIODS):
            c_constraint_expr = (
                c_capacity_option_cost_by_period_type[e_c, t] ==
                period_weight.get((int(t)),1) * pulp.lpSum(use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for n in NODES)
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCostByPeriodType_{e_c}_{t}"

        for n in NODES:
            c_constraint_expr = (
                c_capacity_option_cost_by_location[n] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for t, e_c in product(PERIODS, C_CAPACITY_EXPANSIONS))
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCostByLocation_{n}"

        for t in PERIODS:
            c_constraint_expr = (
                c_capacity_option_cost_by_period[t] ==
                period_weight.get((int(t)),1) * pulp.lpSum(use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for n, e_c in product(NODES, C_CAPACITY_EXPANSIONS))
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCostByPeriod_{t}"

        for e_c in C_CAPACITY_EXPANSIONS:
            c_constraint_expr = (
                c_capacity_option_cost_by_type[e_c] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for n, t in product(NODES, PERIODS))
            )
            model += c_constraint_expr, f"CarryingCapacityOptionCostByType_{e_c}"


        constraint_expr = (
            grand_total_c_capacity_option ==
            pulp.lpSum(period_weight.get((int(t)),1) * use_carrying_capacity_option[n,e_c,t] * carrying_expansions.get((t, n, e_c),0) for n, t, e_p in product(NODES, PERIODS, C_CAPACITY_EXPANSIONS))
        )
        model += constraint_expr, "GrandTotalCarryingCapacityOption"
        logging.info(f"Added capacity option cost constrainst: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        #Calculate shipped volume metrics
        for o, d, p, t, m, u in product(DEPARTING_NODES, RECEIVING_NODES, PRODUCTS, PERIODS, MODES, MEASURES):
            departed_measures_expr = departed_measures[o, d, p, t, m, u] == pulp.lpSum(departed_product_by_mode[o,d,p,t,m] * products_measures.get((p,u),0) for p in PRODUCTS)
            model += departed_measures_expr, f"DepartedMeasures_{o}_{d}_{p}_{t}_{m}_{u}"


        for t, o,d, e_t in product(PERIODS, DEPARTING_NODES, RECEIVING_NODES, T_CAPACITY_EXPANSIONS):
            t_constraint_expr = (
                use_transportation_capacity_option[o,d,e_t,t] >= transportation_expansion_min_count.get((t, o,d,e_t),0)
            )
            model += t_constraint_expr, f"TransportationCapacityOptionMinCount_{t}_{o}_{d}_{e_t}"
        for t, o,d, e_t in product(PERIODS, DEPARTING_NODES, RECEIVING_NODES, T_CAPACITY_EXPANSIONS):
            t_constraint_expr = (
                use_transportation_capacity_option[o,d,e_t,t] >= transportation_expansion_max_count.get((t, o,d,e_t),0)
            )
            model += t_constraint_expr, f"TransportationCapacityOptionMaxCount_{t}_{o}_{d}_{e_t}"

        for t, o,d, e_t in product(PERIODS, DEPARTING_NODES, RECEIVING_NODES, T_CAPACITY_EXPANSIONS):
            t_constraint_expr = (
                t_capacity_option_cost[t, o,d, e_t] ==
                period_weight.get((int(t)),1) * use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o,d,e_t),0) +
                use_transportation_capacity_option[o,d,e_t,t] * pulp.lpSum(transportation_expansion_persisting_cost.get((t2, o,d, e_t),0) for t2 in PERIODS if int(t2) >= int(t))
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCost_{t}_{o}_{d}_{e_t}"

        for o,d, e_t in product(DEPARTING_NODES, RECEIVING_NODES, T_CAPACITY_EXPANSIONS):
            t_constraint_expr = (
                t_capacity_option_cost_by_location_type[o,d, e_t] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o,d, e_t),0) for t in PERIODS)
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCostByLocationType_{o}_{d}_{e_t}"

        for e_t, t in product(T_CAPACITY_EXPANSIONS, PERIODS):
            t_constraint_expr = (t_capacity_option_cost_by_period_type[e_t, t] ==
                period_weight.get((int(t)),1) * pulp.lpSum(use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o,d, e_t),0) for o, d in product(DEPARTING_NODES, RECEIVING_NODES))
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCostByPeriodType_{e_t}_{t}"

        for o,d in product(DEPARTING_NODES, RECEIVING_NODES):
            t_constraint_expr = (
                t_capacity_option_cost_by_location[o,d] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o, d, e_t),0) for t, t_p in product(PERIODS, T_CAPACITY_EXPANSIONS))
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCostByLocation_{o}_{d}"

        for t in PERIODS:
            t_constraint_expr = (
                t_capacity_option_cost_by_period[t] ==
                period_weight.get((int(t)),1) * pulp.lpSum(use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o, d, e_t),0) for o, d, e_t in product(DEPARTING_NODES, RECEIVING_NODES, T_CAPACITY_EXPANSIONS))
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCostByPeriod_{t}"

        for e_t in T_CAPACITY_EXPANSIONS:
            t_constraint_expr = (
                t_capacity_option_cost_by_type[e_t] ==
                pulp.lpSum(period_weight.get((int(t)),1) * use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o, d, e_t),0) for o, d, t in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS))
            )
            model += t_constraint_expr, f"TransportationCapacityOptionCostByType_{e_t}"


        constraint_expr = (
            grand_total_t_capacity_option ==
            pulp.lpSum(period_weight.get((int(t)),1) * use_transportation_capacity_option[o,d,e_t,t] * transportation_expansion_cost.get((t, o, d, e_t),0) for o, d, t, e_t in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS, T_CAPACITY_EXPANSIONS))
        )
        model += constraint_expr, "GrandTotalTransportationCapacityOption"
        logging.info(f"Added transportation capacity option cost constrainst: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        for n, t, p,g, a in product(RECEIVING_NODES, PERIODS, PRODUCTS, NODEGROUPS, AGES):
            carried_volume_cost_expr = (ib_carried_volume_cost[n,p,t, a] >= period_weight.get((int(t)),1) * ib_vol_carried_over_by_age[n,p,t,a] * ib_carrying_cost.get((t,p,n,g),0))	
            model += carried_volume_cost_expr, f"ib_carried_volume_cost_{n}_{p}_{t}_{g}_{a}"
        for n, t, p,g, a in product(DEPARTING_NODES, PERIODS, PRODUCTS, NODEGROUPS, AGES):
            carried_volume_cost_expr = (ob_carried_volume_cost[n,p,t, a] >= period_weight.get((int(t)),1) * ob_vol_carried_over_by_age[n,p,t, a] * ob_carrying_cost.get((t,p,n,g),0))	
            model += carried_volume_cost_expr, f"ob_carried_volume_cost_{n}_{p}_{t}_{g}_{a}"	
        for n, t, p,g, a in product(NODES, PERIODS, PRODUCTS, NODEGROUPS, AGES):
            dropped_volume_cost_expr = (dropped_volume_cost[n,p,t, a] >= period_weight.get((int(t)),1) * vol_dropped_by_age[n,p,t,a] * dropping_cost.get((t,p,n,g),0))
            model += dropped_volume_cost_expr, f"dropped_volume_cost_{n}_{p}_{t}_{g}_{a}"
        for t in PERIODS:
            ib_carried_volume_cost_by_period_expr = (ib_carried_volume_cost_by_period[t] == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for n, p, a in product(RECEIVING_NODES, PRODUCTS, AGES)))
            ob_carried_volume_cost_by_period_expr = (ob_carried_volume_cost_by_period[t] == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for n, p, a in product(DEPARTING_NODES, PRODUCTS, AGES)))
            dropped_volume_cost_by_period_expr = (dropped_volume_cost_by_period[t] == pulp.lpSum(dropped_volume_cost[n,p,t, a] for n, p, a in product(NODES, PRODUCTS, AGES)))
            model += ib_carried_volume_cost_by_period_expr, f"ib_carried_volume_cost_by_period_{t}"
            model += ob_carried_volume_cost_by_period_expr, f"ob_carried_volume_cost_by_period_{t}"
            model += dropped_volume_cost_by_period_expr, f"dropped_volume_cost_by_period_{t}"
        for p in PRODUCTS:
            ib_carried_volume_cost_by_product_expr = (ib_carried_volume_cost_by_product[p] == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for n, t, a in product(RECEIVING_NODES, PERIODS, AGES)))
            ob_carried_volume_cost_by_product_expr = (ob_carried_volume_cost_by_product[p] == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for n, t, a in product(DEPARTING_NODES, PERIODS, AGES)))
            dropped_volume_cost_by_product_expr = (dropped_volume_cost_by_product[p] == pulp.lpSum(dropped_volume_cost[n,p,t, a] for n, t, a in product(NODES, PERIODS, AGES)))
            model += ib_carried_volume_cost_by_product_expr, f"ib_carried_volume_cost_by_product_{p}"
            model += ob_carried_volume_cost_by_product_expr, f"ob_carried_volume_cost_by_product_{p}"
            model += dropped_volume_cost_by_product_expr, f"dropped_volume_cost_by_product_{p}"
        for n in RECEIVING_NODES:
            ib_carried_volume_cost_by_node_expr = (ib_carried_volume_cost_by_node[n] == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for p, t, a in product(PRODUCTS, PERIODS, AGES)))
            model += ib_carried_volume_cost_by_node_expr, f"ib_carried_volume_cost_by_node_{n}"
        for n in DEPARTING_NODES:
            ob_carried_volume_cost_by_node_expr = (ob_carried_volume_cost_by_node[n] == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for p, t, a in product(PRODUCTS, PERIODS, AGES)))
            model += ob_carried_volume_cost_by_node_expr, f"ob_carried_volume_cost_by_node_{n}"
        for n in NODES:
            dropped_volume_cost_by_node_expr = (dropped_volume_cost_by_node[n] == pulp.lpSum(dropped_volume_cost[n,p,t, a] for p, t, a in product(PRODUCTS, PERIODS, AGES)))
            model += dropped_volume_cost_by_node_expr, f"dropped_volume_cost_by_node_{n}"
        for n, t in product(RECEIVING_NODES, PERIODS):
            ib_carried_volume_cost_by_node_time_expr = (ib_carried_volume_cost_by_node_time[n,t] == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for p in PRODUCTS for a in AGES))
            model += ib_carried_volume_cost_by_node_time_expr, f"ib_carried_volume_cost_by_node_time_{n}_{t}"
        for n, t in product(DEPARTING_NODES , PERIODS):
            ob_carried_volume_cost_by_node_time_expr = (ob_carried_volume_cost_by_node_time[n,t] == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for p in PRODUCTS for a in AGES))
            model += ob_carried_volume_cost_by_node_time_expr, f"ob_carried_volume_cost_by_node_time_{n}_{t}"
        # for n, t in product(NODES, PERIODS):
        #     dropped_volume_cost_by_node_time_expr = (dropped_volume_cost_by_node_time[n,t] == pulp.lpSum(dropped_volume_cost[n,p,t, a] for p in PRODUCTS for a in AGES))
        #     model += dropped_volume_cost_by_node_time_expr, f"dropped_volume_cost_by_node_time_{n}_{t}"
        for p, t in product(PRODUCTS, PERIODS):
            ib_carried_volume_cost_by_product_time_expr = (ib_carried_volume_cost_by_product_time[p,t] == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for n in RECEIVING_NODES for a in AGES))
            ob_carried_volume_cost_by_product_time_expr = (ob_carried_volume_cost_by_product_time[p,t] == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for n in DEPARTING_NODES for a in AGES))
            dropped_volume_cost_by_product_time_expr = (dropped_volume_cost_by_product_time[p,t] == pulp.lpSum(dropped_volume_cost[n,p,t, a] for n in NODES for a in AGES))
            model += ib_carried_volume_cost_by_product_time_expr, f"ib_carried_volume_cost_by_product_time_{p}_{t}"
            model += ob_carried_volume_cost_by_product_time_expr, f"ob_carried_volume_cost_by_product_time_{p}_{t}"
            model += dropped_volume_cost_by_product_time_expr, f"dropped_volume_cost_by_product_time_{p}_{t}"
        total_dropped_volume_cost_expr = (total_dropped_volume_cost == pulp.lpSum(dropped_volume_cost[n,p,t, a] for n, p, t, a in product(NODES, PRODUCTS, PERIODS, AGES)))
        total_ib_carried_volume_cost_expr = (total_ib_carried_volume_cost == pulp.lpSum(ib_carried_volume_cost[n,p,t, a] for n, p, t, a in product(RECEIVING_NODES, PRODUCTS, PERIODS, AGES)))
        total_ob_carried_volume_cost_expr = (total_ob_carried_volume_cost == pulp.lpSum(ob_carried_volume_cost[n,p,t, a] for n, p, t, a in product(DEPARTING_NODES, PRODUCTS, PERIODS, AGES)))
        model += total_dropped_volume_cost_expr, "total_dropped_volume_cost_constraint"
        model += total_ib_carried_volume_cost_expr, "total_ib_carried_volume_cost_constraint"
        model += total_ob_carried_volume_cost_expr, "total_ob_carried_volume_cost_constraint"

        # Constraint for grand_total_carried_and_dropped_volume_cost
        grand_total_carried_and_dropped_volume_cost_expr = (grand_total_carried_and_dropped_volume_cost 
                                                            == total_dropped_volume_cost 
                                                            + total_ib_carried_volume_cost
                                                            + total_ob_carried_volume_cost)
        model += grand_total_carried_and_dropped_volume_cost_expr, "grand_total_carried_and_dropped_volume_cost_constraint"
        logging.info(f"Added carried and dropped volume cost constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        for o, p, t, g in product(NODES, PRODUCTS, PERIODS,NODEGROUPS):
            if node_in_nodegroup.get((o,g),0)==1:
                constraint_expr = variable_operating_costs[o, p, t] == period_weight.get((int(t)),1) * operating_costs_variable.get((t, o, p, g),0) * processed_product[o, p, t]
                model += constraint_expr, f"variable_operating_costs_{o}_{p}_{t}_{g}"

        for o, t in product(NODES, PERIODS):
            constraint_expr = is_site_operating[o, t] * big_m >= pulp.lpSum(
                processed_product[o, p, t] for p in PRODUCTS
            )
            model += constraint_expr, f"is_site_operating_constraint_{o}_{t}"

        for o, t, g in product(NODES, PERIODS,NODEGROUPS):
            constraint_expr = fixed_operating_costs[o, t] == period_weight.get((int(t)),1) * (
                operating_costs_fixed.get((t, o,g),0) * is_site_operating[o, t]
            )
            model += constraint_expr, f"fixed_operating_costs_{o}_{t}_{g}"

        for o, t in product(NODES, PERIODS):
            constraint_expr = operating_costs[o, t] == fixed_operating_costs[o, t] + pulp.lpSum(
                variable_operating_costs[o, p, t] for p in PRODUCTS
            )
            model += constraint_expr, f"operating_costs_{o}_{t}"

        for o in NODES:
            constraint_expr = operating_costs_by_origin[o] == pulp.lpSum(
                operating_costs[o, t] for t in PERIODS
            )
            model += constraint_expr, f"operating_costs_by_origin_{o}"

        for t in PERIODS:
            constraint_expr = total_operating_costs[t] == pulp.lpSum(
                operating_costs[o, t] for o in NODES
            )
            model += constraint_expr, f"total_operating_costs_{t}"
        logging.info(f"Added operating cost constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")
        

        grand_total_operating_costs_constraint = (grand_total_operating_costs == pulp.lpSum(total_operating_costs[t] for t in PERIODS))
        model += grand_total_operating_costs_constraint, "grand_total_operating_costs"

       

        #node max launch count
        for o in NODES:
            is_launched_constraint = (pulp.lpSum(is_launched[o,t] for t in PERIODS) <= max_launch_count.get((n),big_m))
            model += is_launched_constraint, f"is_launched_{o}_{t}_max"

        #node min launch count
        for o in NODES:
            is_launched_constraint = (pulp.lpSum(is_launched[o,t] for t in PERIODS) >= min_launch_count.get((n),big_m))
            model += is_launched_constraint, f"is_launched_{o}_{t}_min"
        
        for o, t in product(NODES, PERIODS):
            launch_hard_constraint = (is_launched[o,t] >= launch_hard_constraint.get((o,t),0))
            model += launch_hard_constraint, f"launch_hard_constraint_{o}_{t}"

        for o, t,g in product(NODES, PERIODS, NODEGROUPS):
            total_launch_cost_constraint = (total_launch_cost[o,t] >= is_launched[o,t] * launch_cost.get((t,o,g),0))
            model += total_launch_cost_constraint, f"total_launch_cost_{o}_{t}_{g}"

        for t in PERIODS:
            launch_costs_by_period_constraint = (launch_costs_by_period[t] == pulp.lpSum(total_launch_cost[o,t] for o in NODES))
            model += launch_costs_by_period_constraint, f"launch_costs_by_period_{t}"

        grand_total_launch_cost_constraint = (grand_total_launch_cost == pulp.lpSum(total_launch_cost[o,t] for o in NODES for t in PERIODS))
        model += grand_total_launch_cost_constraint, "grand_total_launch_cost"
        grand_total_launch_cost_constraint_2 = (grand_total_launch_cost <= scenarios_input['Max Launch Cost'][0])
        model += grand_total_launch_cost_constraint_2, "grand_total_launch_cost_2"
        logging.info(f"Added launch cost constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")


        #if the node processes volume then it must have been launched at or before the same period
        for o, t in product(NODES, PERIODS):
            launch_volume_constraint = ((pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if t2 <= t)-pulp.lpSum(is_shut_down[o,t3] for t3 in PERIODS if  int(t3) <=  int(t)) )* big_m >= 
                                        pulp.lpSum(processed_product[o,p,t] for p in PRODUCTS))
            model += launch_volume_constraint, f"launch_volume_{o}_{t}"

        #cannot launch twice without shutting down
        for o, t in product(NODES, PERIODS):
            cannot_launch_twice_constraint = (pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if int(t2) <= int(t))-pulp.lpSum(is_shut_down[o,t3] for t3 in PERIODS if  int(t3) <=  int(t)) <= 1)
            model += cannot_launch_twice_constraint, f"cannot_launch_twice_constraint_{o}_{t}"
            cannot_shut_down_twice_constraint = (pulp.lpSum(is_shut_down[o,t3] for t3 in PERIODS if  int(t3) <=  int(t)) <= pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if  int(t2) <=  int(t)))
            model += cannot_shut_down_twice_constraint, f"cannot_shut_down_twice_constraint_{o}_{t}"

        #min operating duration min_shut_down_duration
        for o, t in product(NODES, PERIODS):
            min_operating_duration = (is_shut_down[o,t] <= 1- pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if  int(t2)> int(t)-min_operating_duration.get((o),0) if int(t2)<=int(t) ))
            model += min_operating_duration, f"min_operating_duration_{o}_{t}"

        #must shut down at some timer period within max operating window after launch
        for o, t in product(NODES, PERIODS):
            if int(t)-max_operating_duration.get((o),big_m) >0:
                max_operating_duration = (pulp.lpSum(is_shut_down[o,t3] for t3 in PERIODS if  int(t3)> int(t)-max_shut_down_duration.get((o),big_m) if int(t3)<=int(t))  >= pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if  int(t2)> int(t)-max_operating_duration.get((o),big_m) if int(t2)<=int(t) ))
                model += max_operating_duration, f"max_operating_duration_{o}_{t}"

        #min shut down duration
        for o, t in product(NODES, PERIODS):
            min_shut_down_duration = (is_launched[o,t] <= 1- pulp.lpSum(is_shut_down[o,t2] for t2 in PERIODS if  int(t2)> int(t)-min_shut_down_duration.get((o),0) if int(t2)<=int(t) ))
            model += min_shut_down_duration, f"min_shut_down_duration_{o}_{t}"
        
        #max shut_down duration min_shut_down_duration
        for o, t in product(NODES, PERIODS):
            if int(t)-max_shut_down_duration.get((o),big_m) >0:
                max_shut_down_duration = (pulp.lpSum(is_launched[o,t3] for t3 in PERIODS if  int(t3)> int(t)-max_shut_down_duration.get((o),big_m) if int(t3)<=int(t)) >= pulp.lpSum(is_shut_down[o,t2] for t2 in PERIODS if  int(t2)> int(t)-max_shut_down_duration.get((o),big_m) if int(t2)<=int(t) ))
                model += max_shut_down_duration, f"max_shut_down_duration_{o}_{t}"

        for o, t in product(NODES, PERIODS):
            shut_down_hard_constraint = (is_shut_down[o,t] >= shut_down_hard_constraint.get((o,t),0))
            model += shut_down_hard_constraint, f"shut_down_hard_constraint_{o}_{t}"

        for o, t in product(NODES, PERIODS):
            is_shut_down_constraint = (pulp.lpSum(is_shut_down[o,t] for t2 in PERIODS) <=  max_shut_down_count.get((n),big_m))
            model += is_shut_down_constraint, f"is_shut_down_{o}_{t}_max"

        for o, t in product(NODES, PERIODS):
            is_shut_down_constraint = (pulp.lpSum(is_shut_down[o,t2] for t2 in PERIODS) <=  min_shut_down_count.get((n),big_m))
            model += is_shut_down_constraint, f"is_shut_down_{o}_{t}_min"

        for o, t, nt in product(NODES, PERIODS, NODETYPES):
            is_shut_down_type_max_constraint = (pulp.lpSum(is_launched[o,t2]*node_type[o,nt] for t2 in PERIODS if t2<=t) - pulp.lpSum(is_shut_down[o,t2]*node_type[o,nt] for t2 in PERIODS if t2<=t) <= node_types_max.get((t,nt),0))
            model += is_shut_down_type_max_constraint, f"is_shut_down_type_max_constraint_{o}_{t}_{nt}"

        for o, t, nt in product(NODES, PERIODS, NODETYPES):
            is_shut_down_type_min_constraint = (pulp.lpSum(is_launched[o,t2]*node_type[o,nt] for t2 in PERIODS if t2<=t) - pulp.lpSum(is_shut_down[o,t2]*node_type[o,nt] for t2 in PERIODS if t2<=t) >= node_types_min.get((t,nt),0))
            model += is_shut_down_type_min_constraint, f"is_shut_down_type_min_constraint_{o}_{t}_{nt}"

        for o, t in product(NODES, PERIODS):
            shut_down_constraint = (is_shut_down[o,t]  <= 
                                        pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if t2 < t))
            model += shut_down_constraint, f"shut_down_after_launch_constraint_{o}_{t}"

        for o, t in product(NODES, PERIODS):
            shut_down_volume_constraint = ((1-pulp.lpSum(is_shut_down[o,t2] for t2 in PERIODS if t2 <= t)) * big_m >= 
                                        pulp.lpSum(processed_product[o,p,t2] for p in PRODUCTS for t2 in PERIODS if t2 >= t))
            model += shut_down_volume_constraint, f"shut_down_volume_{o}_{t}"

        for o, t in product(NODES, PERIODS):
            early_shut_down_constraint = (is_shut_down[o,t] <= 1-
                                    pulp.lpSum(processed_product[o,p,t2] for p in PRODUCTS for t2 in PERIODS if t2 >= t) / big_m  )
            model += early_shut_down_constraint, f"early_shut_down_2_{o}_{t}"

        for o, t,g in product(NODES, PERIODS, NODEGROUPS):
            total_shut_down_cost_constraint = (total_shut_down_cost[o,t] >= is_shut_down[o,t] * shut_down_cost.get((t,o,g),0))
            model += total_shut_down_cost_constraint, f"total_shut_down_cost_{o}_{t}_{g}"

        for t in PERIODS:
            shut_down_costs_by_period_constraint = (shut_down_costs_by_period[t] == pulp.lpSum(total_shut_down_cost[o,t] for o in NODES))
            model += shut_down_costs_by_period_constraint, f"shut_down_costs_by_period_{t}"

        grand_total_shut_down_cost_constraint = (grand_total_shut_down_cost == pulp.lpSum(total_shut_down_cost[o,t] for o in NODES for t in PERIODS))
        model += grand_total_shut_down_cost_constraint, "grand_total_shut_down_cost"
        logging.info(f"Added shut_down cost constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        for o, t in product(NODES, PERIODS):
            constraint_expr = (is_site_operating[o, t] <= pulp.lpSum(is_launched[o,t2] for t2 in PERIODS if t2 <= t)- pulp.lpSum(is_shut_down[o,t2] for t2 in PERIODS if t2 <= t))
            model += constraint_expr, f"is_site_operating_shut_down_constraint_{o}_{t}"
        
     
        if flow_constraints_min_connections or flow_constraints_max_connections:
            for o_index in departing_nodes:
                for g_index in nodegroups:
                    if o_index == '@' or node_in_nodegroup.get((o_index, g_index),0)==1 :
                        
                        if o_index=='@' and g_index != '@':
                            FROM_NODES = [n for n in DEPARTING_NODES if node_in_nodegroup.get((n, g_index), 0) == 1]
                        else:
                            FROM_NODES = DEPARTING_NODES
                        
                        departing_nodes_list =FROM_NODES if o_index=='@' else [o_index]
                        for d_index in receiving_nodes:
                            receiving_nodes_list = RECEIVING_NODES if d_index=='@' else [d_index]
                            for g2_index in nodegroups:
                                if  d_index == '@' or node_in_nodegroup.get((d_index,g2_index),0)==1:
                                    if d_index=='@' and g2_index != '@':
                                        TO_NODES = [n for n in RECEIVING_NODES if node_in_nodegroup.get((n, g2_index), 0) == 1]
                                    else:
                                        TO_NODES = RECEIVING_NODES
                                    receiving_nodes_list = TO_NODES if d_index=='@' else [d_index]
                                    for t_index  in  periods:
                                        periods_list = PERIODS if t_index=='@' else [t_index]
                                        for m_index  in modes:
                                            for u_index  in measures:
                                                for p_index in products:
                                                    left_exp = flow_constraints_min_connections.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),0)
                                                    right_exp = pulp.lpSum(is_destination_assigned_to_origin[o,d,t]	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list  )+(big_m*(1-is_launched[o_index,t_index]) if o_index != '@' and t_index != '@' else 0)+(big_m*(1-is_launched[d_index,t_index]) if d_index != '@' and t_index != '@' else 0)
                                                    min_expr = (
                                                        left_exp <= right_exp
                                                    )
                                                    model += min_expr, f"flow_constraints_min_connections_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
                                                    
                                                    left_exp = flow_constraints_max_connections.get(( o_index,d_index,p_index, t_index, m_index,'unit',u_index, g_index, g2_index),big_m) 
                                                    right_exp = pulp.lpSum(is_destination_assigned_to_origin[o,d,t]	for	o in departing_nodes_list for d in receiving_nodes_list for	t in periods_list  )
                                                    max_expr = (
                                                        left_exp >= right_exp
                                                    )
                                                    model += max_expr, f"flow_constraints_max_connections_{t_index}_{o_index}_{d_index}_{m_index}_{u_index}_{p_index}_{g_index}_{g2_index}"
            logging.info(f"Added flow ob pct constraint lower and upper bounds: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        
        for o, d, t in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS):
            is_destination_assigned_to_origin_constraint = (is_destination_assigned_to_origin[o,d,t] <= 
                                                        pulp.lpSum(departed_product[o,d,p,t] * 9999 for p in PRODUCTS))
            model += is_destination_assigned_to_origin_constraint, f"is_destination_assigned_{o}_{d}_{t}_1"

        for o, d, t in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS):
            is_destination_assigned_to_origin_constraint = (is_destination_assigned_to_origin[o,d,t] * big_m >= 
                                                        pulp.lpSum(departed_product[o,d,p,t]  for p in PRODUCTS))
            model += is_destination_assigned_to_origin_constraint, f"is_destination_assigned_{o}_{d}_{t}_2"

        if distance and max_distance:
            for o, d, t, m,g,g2 in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS, MODES,NODEGROUPS,NODEGROUPS):
                if node_in_nodegroup.get((o,g),0)==1 and node_in_nodegroup.get((d,g2),0)==1:
                    distance_constraint = (is_destination_assigned_to_origin[o,d,t] * distance.get((o,d,m),big_m) <= max_distance.get((o,t,m,g,n_r,g2),big_m))
                    model += distance_constraint, f"distance_{o}_{d}_{t}_{m}_{g}_{n_r}_{g2}"

        if transit_time and max_transit_time:
            for n_d, n_r, t, m,g,g2 in product(DEPARTING_NODES, RECEIVING_NODES, PERIODS, MODES,NODEGROUPS,NODEGROUPS):
                if node_in_nodegroup.get((n_d,g),0)==1 and node_in_nodegroup.get((n_r,g2),0)==1:
                    if transit_time.get((n_d,n_r,m),0)>max_transit_time.get((n_d,t,m,g,n_r, g2),big_m):
                        transit_time_constraint = (pulp.lpSum(departed_product_by_mode[n_d,n_r,p,t,m]  for p in PRODUCTS) ==0 )
                        model += transit_time_constraint, f"transit_time_{n_d}_{n_r}_{t}_{m}_{g}_{n_r}_{g2}"
            logging.info(f"Added volume move constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        for o, t, p, d in product(DEPARTING_NODES, PERIODS, PRODUCTS, RECEIVING_NODES):
            binary_assignment_lower_constraint = (binary_product_destination_assignment[o,t,p,d]*big_m >= 
                                                departed_product[o,d,p,t])
            model += binary_assignment_lower_constraint, f"binary_assignment_lower_{o}_{t}_{p}_{d}"
            
            binary_assignment_upper_constraint = (binary_product_destination_assignment[o,t,p,d] <= 
                                                departed_product[o,d,p,t])
            model += binary_assignment_upper_constraint, f"binary_assignment_upper_{o}_{t}_{p}_{d}"
            
            if int(t) > 1:
                volume_moved_constraint = (volume_moved[str(int(t)-1),t,p,o,d] >=departed_product[o,d,p,t] + 
                                        big_m*(binary_product_destination_assignment[o,t,p,d] - binary_product_destination_assignment[o,str(int(t)-1),p,d] - 1))
                model += volume_moved_constraint, f"volume_moved_{o}_{t}_{p}_{d}"

                num_destinations_moved_constraint = (num_destinations_moved[str(int(t)-1),t,p,o,d] )>=(binary_product_destination_assignment[o,t,p,d] - binary_product_destination_assignment[o,str(int(t)-1),p,d])
                model += num_destinations_moved_constraint, f"num_destinations_moved_{o}_{t}_{p}_{d}"

        if pop_cost_per_move or  pop_cost_per_volume_moved:
            for o, t, p, d,g,g2 in product(DEPARTING_NODES, PERIODS, PRODUCTS, RECEIVING_NODES, NODEGROUPS, NODEGROUPS):            
                if int(t) > 1:
                    if node_in_nodegroup.get((o,g),0)==1 and node_in_nodegroup.get((d,g2),0)==1:
                        pop_cost_constraint = (pop_cost[str(int(t)-1),t,p,o,d] == 
                                            pop_cost_per_volume_moved.get((str(int(t)-1),t,p,o,d,g,g2),0)*volume_moved[str(int(t)-1),t,p,o,d] + 
                                            pop_cost_per_move.get((str(int(t)-1),t,p,o,d,g,g2),0)*(binary_product_destination_assignment[o,t,p,d] - binary_product_destination_assignment[o,str(int(t)-1),p,d]))
                        model += pop_cost_constraint, f"pop_cost_{o}_{t}_{p}_{d}_{g}_{g2}"

                        pop_max_destinations_moved_constraint = (pop_max_destinations_moved.get((str(int(t)-1),t,p,o,d,g,g2),big_m) >= 
                                                                (binary_product_destination_assignment[o,t,p,d] - binary_product_destination_assignment[o,str(int(t)-1),p,d]))
                        model += pop_max_destinations_moved_constraint, f"pop_max_destinations_moved_{o}_{t}_{p}_{d}_{g}_{g2}"

        total_volume_moved_constraint = (total_volume_moved>=pulp.lpSum(volume_moved[str(int(t)-1),t,p,o,d] for t in PERIODS for p in PRODUCTS for o in DEPARTING_NODES for d in RECEIVING_NODES if int()>1))
        model += total_volume_moved_constraint, f"total_volume_moved_constraint"
        total_num_destinations_moved_constraint = (total_num_destinations_moved>=pulp.lpSum(num_destinations_moved[str(int(t)-1),t,p,o,d] for t in PERIODS for p in PRODUCTS for o in DEPARTING_NODES for d in RECEIVING_NODES if int()>1))
        model += total_num_destinations_moved_constraint, f"total_num_destinations_moved_constraint"

        grand_total_pop_cost_constraint = (grand_total_pop_cost == pulp.lpSum(pop_cost[t1,t2,p,o,d] for o in DEPARTING_NODES for t1 in PERIODS for t2 in PERIODS for p in PRODUCTS for d in RECEIVING_NODES))
        model += grand_total_pop_cost_constraint, f"grand_total_pop_cost_constraint"

        logging.info(f"Added plan-over-plan cost constraints: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")
        logging.info(f"Compile model time: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")
        
        if resource_capacity_consumption:
            for r, n,t,c,g in product(RESOURCES, NODES,PERIODS,RESOURCE_CHILD_CAPACITY_TYPES, NODEGROUPS):
                if node_in_nodegroup.get((n,g),0)==1 and resource_capacity_by_type.get((t,n,r,c,g),None) != None:
                    initial_capacity = resource_capacity_by_type.get((t,n,r,c,g),1)*resource_node_initial_count.get((n,r,g),0)
                    if c in RESOURCE_CHILD_CAPACITY_TYPES:
                        if initial_capacity>0:
                            expr = (node_utilization[n,t,c] <=( pulp.lpSum(
                                    processed_product[n, p, t] * resource_capacity_consumption.get((p, t, g, n, c),0) for p in PRODUCTS
                                ) +
                                pulp.lpSum(
                                    processed_product[n, p, t2] * resource_capacity_consumption.get((p, t2, g, n, c),0) for t2,p in product(PERIODS, PRODUCTS) if int(t2)>=int(t)-int(capacity_consumption_periods.get((t2,n,p,g),0)) and int(t2)<int(t)
                                ))/
                                (initial_capacity )
                            )
                        else:
                            expr = (node_utilization[n,t,c] ==0)
                    if c in RESOURCE_PARENT_CAPACITY_TYPES:
                        c_p=c
                        if initial_capacity>0:
                            expr = (node_utilization[n,t,c_p] <=( pulp.lpSum(
                                        processed_product[n, p, t] * resource_capacity_consumption.get((p, t, g, n, c2),0) * capacity_type_hierarchy.get((c2,c_p),0) for p in PRODUCTS for c2 in RESOURCE_CHILD_CAPACITY_TYPES
                                    ) +
                                    pulp.lpSum( 
                                        processed_product[n, p, t2] * resource_capacity_consumption.get((p, t2, g, n, c2),0) * capacity_type_hierarchy.get((c2,c_p),0) for t2,p,c2 in product(PERIODS, PRODUCTS,RESOURCE_CHILD_CAPACITY_TYPES) if int(t2)>=int(t)-int(capacity_consumption_periods.get((t2,n,p,g),0)) and int(t2)<int(t)
                                    ))/
                                    (initial_capacity )
                                )
                        else:
                            expr = (node_utilization[n,t,c_p] ==0)
                    model.addConstraint(expr, f"Utilization_constraint_{r}_{n}_{t}_{c}_{g}")
            logging.info(f"Added procesing less than processing capacity constraint: {round((datetime.now() - compile_model_start).seconds, 0)} seconds.")

        for n_d, p, t, a, m in product(DEPARTING_NODES, PRODUCTS, PERIODS, AGES,MODES):
            expr = ( pulp.lpSum(vol_departed_by_age[n_d,n_r, p, t, a,m] for n_r in RECEIVING_NODES )<=pulp.lpSum(departed_product_by_mode[n_d, n_r, p, t,m] for n_r in RECEIVING_NODES)-pulp.lpSum(vol_departed_by_age[n_d,n_r, p, t, a2,m] for n_r in RECEIVING_NODES for a2 in AGES if int(a2)>int(a)))
            model.addConstraint(expr, f"departed_by_age_fifo_constraint_{n_d}_{p}_{t}_{a}_{m}")

        # Create constraint handlers
        flow_constraints = FlowConstraints(variables, list_of_sets, list_of_parameters)
        age_constraints = AgeConstraints(variables, list_of_sets, list_of_parameters)
        transportation_constraints = TransportationConstraints(variables, list_of_sets, list_of_parameters)
        resource_constraints = ResourceConstraints(variables, list_of_sets, list_of_parameters)
        capacity_constraints = CapacityConstraints(variables, list_of_sets, list_of_parameters)

        # Add constraints to model
        flow_constraints.build(model)
        age_constraints.build(model)
        transportation_constraints.build(model)
        resource_constraints.build(model)
        capacity_constraints.build(model)

        solve_start =datetime.now()
        result = get_solver_results(model,objectives_input,parameters_input,list_of_sets,list_of_parameters,variables, settings)
        logging.info(f"Solver time: {round((datetime.now() - solve_start).seconds, 0)} seconds.")

        output_results={}
        output_results['variables'] = variables
        output_results['model']=result
        output_results['sets']=list_of_sets
        output_results['dimensions']=dimensions
        
        if s == SCENARIOS[0]:
            if result !=-1:
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

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__) 
    input_file_path = os.path.join(script_dir,"examples/demo_inputs_transportation_facility_location.xlsx")
    results = optimize_network(input_file_path)
    output_file_path = os.path.join(script_dir,"examples/demo_inputs_transportation_facility_location_results.xlsx")
    export_results(results,output_file_path)