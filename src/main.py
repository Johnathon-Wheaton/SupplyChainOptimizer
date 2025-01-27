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
       
        logging.info(f"Done formatting inputs. {round((datetime.now() - format_inputs_start).seconds, 0)} seconds.")
        compile_model_start = datetime.now()

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