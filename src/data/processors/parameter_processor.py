from typing import Dict, List, Any
import pandas as pd

class ParameterProcessor:
    """Handles the creation of parameter dictionaries from input data"""

    @staticmethod
    def create_parameter_dict(df: pd.DataFrame, index_cols: List[str], value_col: str) -> Dict:
        """Create a parameter dictionary from a DataFrame
        
        Args:
            df: Input DataFrame
            index_cols: Columns to use as dictionary index
            value_col: Column containing values
            
        Returns:
            Dictionary with multi-level index as key and values from value_col
        """
        return df.set_index(index_cols)[value_col].to_dict()

    def create_all_parameters(self, input_data: Dict[str, pd.DataFrame]) -> Dict[str, Dict]:
        """Create all parameter dictionaries from input data"""
        parameters = {}

        # Node groups parameters
        parameters['node_in_nodegroup'] = self.create_parameter_dict(
            input_data['node_groups_input'],
            ['Node', 'Group'],
            'assigned'
        )

        # Distance and transit parameters
        parameters['distance'] = self.create_parameter_dict(
            input_data['od_distances_and_transit_times_input'],
            ['Origin', 'Destination', 'Mode'],
            'Distance'
        )
        parameters['transit_time'] = self.create_parameter_dict(
            input_data['od_distances_and_transit_times_input'],
            ['Origin', 'Destination', 'Mode'],
            'Transit Time'
        )
        parameters['transport_periods'] = self.create_parameter_dict(
            input_data['od_distances_and_transit_times_input'],
            ['Origin', 'Destination', 'Mode'],
            'Periods'
        )

        # Demand parameters
        parameters['demand'] = self.create_parameter_dict(
            input_data['demand_input'],
            ['Period', 'Product', 'Destination'],
            'Demand'
        )

        # Age constraint parameters
        parameters['max_vol_by_age'] = self.create_parameter_dict(
            input_data['age_constraints_input'],
            ['Period', 'Product', 'Destination', 'Age', 'Destination Node Group'],
            'Max Volume'
        )
        parameters['age_constraint_violation_cost'] = self.create_parameter_dict(
            input_data['age_constraints_input'],
            ['Period', 'Product', 'Destination', 'Age', 'Destination Node Group'],
            'Cost per Unit to Violate'
        )

        # Flow constraint parameters
        parameters['flow_constraints_min'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Min'
        )
        parameters['flow_constraints_max'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Max'
        )
        parameters['flow_constraints_min_pct_ob'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Min Pct of OB'
        )
        parameters['flow_constraints_max_pct_ob'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Max Pct of OB'
        )
        parameters['flow_constraints_min_pct_ib'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Min Pct of IB'
        )
        parameters['flow_constraints_max_pct_ib'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Max Pct of IB'
        )
        parameters['flow_constraints_min_connections'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Min Connections'
        )
        parameters['flow_constraints_max_connections'] = self.create_parameter_dict(
            input_data['flow_input'],
            ['Node', 'Downstream Node', 'Product', 'Period', 'Mode', 'Container', 
             'Measure', 'Node Group', 'Downstream Node Group'],
            'Max Connections'
        )

        # Processing assembly parameters
        parameters['processing_assembly_p1_required'] = self.create_parameter_dict(
            input_data['processing_assembly_constraints_input'],
            ['Period', 'Node', 'Node Group', 'Product 1', 'Product 2'],
            'Product 1 Qty'
        )
        parameters['processing_assembly_p2_required'] = self.create_parameter_dict(
            input_data['processing_assembly_constraints_input'],
            ['Period', 'Node', 'Node Group', 'Product 1', 'Product 2'],
            'Product 2 Qty'
        )

        # Shipping assembly parameters
        parameters['shipping_assembly_p1_required'] = self.create_parameter_dict(
            input_data['shipping_assembly_constraints_input'],
            ['Period', 'Origin', 'Destination', 'Origin Node Group', 
             'Destination Node Group', 'Product 1', 'Product 2'],
            'Product 1 Qty'
        )
        parameters['shipping_assembly_p2_required'] = self.create_parameter_dict(
            input_data['shipping_assembly_constraints_input'],
            ['Period', 'Origin', 'Destination', 'Origin Node Group', 
             'Destination Node Group', 'Product 1', 'Product 2'],
            'Product 2 Qty'
        )

        # Transportation cost parameters
        parameters['transportation_cost_fixed'] = self.create_parameter_dict(
            input_data['transportation_costs_input'],
            ['Origin', 'Destination', 'Mode', 'Container', 'Measure', 'Period',
             'Origin Node Group', 'Destination Node Group'],
            'Fixed Cost'
        )
        parameters['transportation_cost_variable_distance'] = self.create_parameter_dict(
            input_data['transportation_costs_input'],
            ['Origin', 'Destination', 'Mode', 'Container', 'Measure', 'Period',
             'Origin Node Group', 'Destination Node Group'],
            'Cost per Unit of Distance'
        )
        parameters['transportation_cost_variable_time'] = self.create_parameter_dict(
            input_data['transportation_costs_input'],
            ['Origin', 'Destination', 'Mode', 'Container', 'Measure', 'Period',
             'Origin Node Group', 'Destination Node Group'],
            'Cost per Unit of Time'
        )
        parameters['transportation_cost_minimum'] = self.create_parameter_dict(
            input_data['transportation_costs_input'],
            ['Origin', 'Destination', 'Mode', 'Container', 'Measure', 'Period',
             'Origin Node Group', 'Destination Node Group'],
            'Minimum Cost Regardless of Distance'
        )

        # Products and measures parameters
        parameters['products_measures'] = self.create_parameter_dict(
            input_data['products_input'],
            ['Product', 'Measure'],
            'Value'
        )

        # Operating costs parameters
        parameters['operating_costs_variable'] = self.create_parameter_dict(
            input_data['variable_operating_costs_input'],
            ['Period', 'Name', 'Product', 'Node Group'],
            'Variable Cost'
        )
        parameters['capacity_consumption_periods'] = self.create_parameter_dict(
            input_data['variable_operating_costs_input'],
            ['Period', 'Name', 'Product', 'Node Group'],
            'Periods of Capacity Consumption'
        )
        parameters['delay_periods'] = self.create_parameter_dict(
            input_data['variable_operating_costs_input'],
            ['Period', 'Name', 'Product', 'Node Group'],
            'Periods Delay'
        )

        # Load capacity parameters
        parameters['load_capacity'] = self.create_parameter_dict(
            input_data['load_capacity_input'],
            ['Period', 'Origin', 'Destination', 'Mode', 'Measure', 
             'Origin Node Group', 'Destination Node Group'],
            'Capacity'
        )

        # Capacity hierarchy parameters
        parameters['capacity_type_heirarchy'] = self.create_parameter_dict(
            input_data['resource_capacity_types_input'][
                ~input_data['resource_capacity_types_input']['Parent Capacity Type'].isna()
            ],
            ['Capacity Type', 'Parent Capacity Type'],
            'Relative Rate'
        )

        # Transportation constraint parameters
        parameters['transportation_constraints_min'] = self.create_parameter_dict(
            input_data['transportation_constraints_input'],
            ['Period', 'Origin', 'Destination', 'Mode', 'Container', 'Measure',
             'Origin Node Group', 'Destination Node Group'],
            'Min'
        )
        parameters['transportation_constraints_max'] = self.create_parameter_dict(
            input_data['transportation_constraints_input'],
            ['Period', 'Origin', 'Destination', 'Mode', 'Container', 'Measure',
             'Origin Node Group', 'Destination Node Group'],
            'Max'
        )

        # Transportation expansion parameters
        parameters['transportation_expansion_capacity'] = self.create_parameter_dict(
            input_data['transportation_expansion_capacities_input'],
            ['Incremental Capacity Label', 'Mode', 'Container', 'Measure'],
            'Incremental Capacity'
        )
        parameters['transportation_expansion_cost'] = self.create_parameter_dict(
            input_data['transportation_expansions_input'],
            ['Period', 'Origin', 'Destination', 'Incremental Capacity Label'],
            'Cost'
        )
        parameters['transportation_expansion_persisting_cost'] = self.create_parameter_dict(
            input_data['transportation_expansions_input'],
            ['Period', 'Origin', 'Destination', 'Incremental Capacity Label'],
            'Persisting Cost'
        )
        parameters['transportation_expansion_min_count'] = self.create_parameter_dict(
            input_data['transportation_expansions_input'],
            ['Period', 'Origin', 'Destination', 'Incremental Capacity Label'],
            'Min'
        )
        parameters['transportation_expansion_max_count'] = self.create_parameter_dict(
            input_data['transportation_expansions_input'],
            ['Period', 'Origin', 'Destination', 'Incremental Capacity Label'],
            'Max'
        )

        # Carrying expansion parameters
        parameters['ib_carrying_expansion_capacity'] = self.create_parameter_dict(
            input_data['carrying_expansions_input'],
            ['Period', 'Location', 'Incremental Capacity Label'],
            'Inbound Incremental Capacity'
        )
        parameters['ob_carrying_expansion_capacity'] = self.create_parameter_dict(
            input_data['carrying_expansions_input'],
            ['Period', 'Location', 'Incremental Capacity Label'],
            'Outbound Incremental Capacity'
        )
        parameters['carrying_expansions'] = self.create_parameter_dict(
            input_data['carrying_expansions_input'],
            ['Period', 'Location', 'Incremental Capacity Label'],
            'Cost'
        )
        parameters['carrying_expansions_persisting_cost'] = self.create_parameter_dict(
            input_data['carrying_expansions_input'],
            ['Period', 'Location', 'Incremental Capacity Label'],
            'Persisting Cost'
        )

        # PoP demand change parameters
        parameters['pop_cost_per_move'] = self.create_parameter_dict(
            input_data['pop_demand_change_const_input'],
            ['Period 1', 'Period 2', 'Product', 'Origin', 'Destination',
             'Origin Node Group', 'Destination Node Group'],
            'Cost per Destination Move'
        )
        parameters['pop_cost_per_volume_moved'] = self.create_parameter_dict(
            input_data['pop_demand_change_const_input'],
            ['Period 1', 'Period 2', 'Product', 'Origin', 'Destination',
             'Origin Node Group', 'Destination Node Group'],
            'Cost per Volume Move'
        )
        parameters['pop_max_destinations_moved'] = self.create_parameter_dict(
            input_data['pop_demand_change_const_input'],
            ['Period 1', 'Period 2', 'Product', 'Origin', 'Destination',
             'Origin Node Group', 'Destination Node Group'],
            'Max Destinations Moved'
        )

        # Transit time and distance parameters
        parameters['max_distance'] = self.create_parameter_dict(
            input_data['max_transit_time_distance_input'],
            ['Origin', 'Period', 'Mode', 'Origin Node Group', 'Destination',
             'Destination Node Group'],
            'Max Distance'
        )
        parameters['max_transit_time'] = self.create_parameter_dict(
            input_data['max_transit_time_distance_input'],
            ['Origin', 'Period', 'Mode', 'Origin Node Group', 'Destination',
             'Destination Node Group'],
            'Max Transit Time'
        )

        # Operating cost parameters
        parameters['operating_costs_fixed'] = self.create_parameter_dict(
            input_data['fixed_operating_costs_input'],
            ['Period', 'Name', 'Node Group'],
            'Fixed Cost'
        )
        parameters['launch_cost'] = self.create_parameter_dict(
            input_data['fixed_operating_costs_input'],
            ['Period', 'Name', 'Node Group'],
            'Launch Cost'
        )
        parameters['shut_down_cost'] = self.create_parameter_dict(
            input_data['fixed_operating_costs_input'],
            ['Period', 'Name', 'Node Group'],
            'Shut Down Cost'
        )

        # Node parameters
        parameters['min_launch_count'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Min Launches'
        )
        parameters['max_launch_count'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Max Launches'
        )
        parameters['min_operating_duration'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Min Operating Duration'
        )
        parameters['max_operating_duration'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Max Operating Duration'
        )
        # Node parameters continued
        parameters['min_shut_down_count'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Min Shutdowns'
        )
        parameters['max_shut_down_count'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Max Launches'
        )
        parameters['min_shut_down_duration'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Min Shutdown Duration'
        )
        parameters['max_shut_down_duration'] = self.create_parameter_dict(
            input_data['nodes_input'],
            ['Name'],
            'Max Shutdown Duration'
        )

        # Launch and shutdown parameters
        parameters['launch_hard_constraint'] = self.create_parameter_dict(
            input_data['node_shut_down_launch_hard_constraints_input'],
            ['Name', 'Period'],
            'Launch'
        )
        parameters['shut_down_hard_constraint'] = self.create_parameter_dict(
            input_data['node_shut_down_launch_hard_constraints_input'],
            ['Name', 'Period'],
            'Shutdown'
        )

        # Carrying and demand cost parameters
        parameters['ib_carrying_cost'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_cost_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Inbound Carrying Cost'
        )
        parameters['ob_carrying_cost'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_cost_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Outbound Carrying Cost'
        )
        parameters['dropping_cost'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_cost_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Drop Cost'
        )

        # Carrying and demand constraint parameters
        parameters['ib_max_carried'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_constraints_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Max Inbound Carrying'
        )
        parameters['ob_max_carried'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_constraints_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Max Outbound Carrying'
        )
        parameters['max_dropped'] = self.create_parameter_dict(
            input_data['carrying_or_missed_demand_constraints_input'],
            ['Period', 'Product', 'Node', 'Node Group'],
            'Max Dropped'
        )

        # Carrying capacity parameters
        parameters['ib_carrying_capacity'] = self.create_parameter_dict(
            input_data['carrying_capacity_input'],
            ['Period', 'Node', 'Measure', 'Node Group'],
            'Inbound Capacity'
        )
        parameters['ob_carrying_capacity'] = self.create_parameter_dict(
            input_data['carrying_capacity_input'],
            ['Period', 'Node', 'Measure', 'Node Group'],
            'Outbound Capacity'
        )

        # Period parameters
        parameters['period_weight'] = self.create_parameter_dict(
            input_data['periods_input'],
            ['Period'],
            'Weight'
        )

        # Transportation group parameters
        parameters['transportation_group'] = self.create_parameter_dict(
            input_data['product_transportation_groups_input'],
            ['Product', 'Group'],
            'value'
        )

        # Node type parameters
        parameters['node_types_min'] = self.create_parameter_dict(
            input_data['node_types_input'],
            ['Period', 'Node Type'],
            'Min Count'
        )
        parameters['node_types_max'] = self.create_parameter_dict(
            input_data['node_types_input'],
            ['Period', 'Node Type'],
            'Max Count'
        )

        # Resource parameters
        parameters['resource_fixed_add_cost'] = self.create_parameter_dict(
            input_data['resource_costs_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Fixed Cost to Add Resource'
        )
        parameters['resource_cost_per_time'] = self.create_parameter_dict(
            input_data['resource_costs_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Resource Cost per Time Unit'
        )
        parameters['resource_fixed_remove_cost'] = self.create_parameter_dict(
            input_data['resource_costs_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Fixed Cost to Remove Resource'
        )
        parameters['resource_add_cohort_count'] = self.create_parameter_dict(
            input_data['resource_costs_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Add Resources in Units of'
        )
        parameters['resource_remove_cohort_count'] = self.create_parameter_dict(
            input_data['resource_costs_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Remove Resources in Units of'
        )

        # Resource capacity parameters
        parameters['resource_capacity_by_type'] = self.create_parameter_dict(
            input_data['resource_capacities_input'],
            ['Period', 'Node', 'Resource', 'Capacity Type', 'Node Group'],
            'Capacity per Resource'
        )

        # Resource node constraint parameters
        parameters['resource_node_min_count'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Min Count'
        )
        parameters['resource_node_max_count'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Max Count'
        )
        parameters['resource_min_to_add'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Minimum Resources to Add'
        )
        parameters['resource_max_to_add'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Maximum Resources to Add'
        )
        parameters['resource_min_to_remove'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Minimum Resources to Remove'
        )
        parameters['resource_max_to_remove'] = self.create_parameter_dict(
            input_data['node_resource_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group'],
            'Maximum Resources to Remove'
        )

        # Resource attribute parameters
        parameters['resource_attribute_min'] = self.create_parameter_dict(
            input_data['resource_attribute_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group', 'Resource Attribute'],
            'Min'
        )
        parameters['resource_attribute_max'] = self.create_parameter_dict(
            input_data['resource_attribute_constraints_input'],
            ['Period', 'Node', 'Resource', 'Node Group', 'Resource Attribute'],
            'Max'
        )

        parameters['resource_attribute_consumption_per'] = self.create_parameter_dict(
            input_data['resource_attributes_input'],
            ['Period', 'Resource', 'Resource Attribute'],
            'Value per Resource'
        )

        parameters['resource_node_initial_count'] = self.create_parameter_dict(
            input_data['resource_initial_counts_input'],
            ['Node', 'Resource', 'Node Group'],
            'Initial Count'
        )

        parameters['resource_capacity_consumption'] = self.create_parameter_dict(
            input_data['resource_capacity_consumption_input'],
            ['Product', 'Period', 'Node Group', 'Node', 'Capacity Type'],
            'Capacity Required per Unit'
        )
        parameters['resource_capacity_consumption_periods'] = self.create_parameter_dict(
            input_data['resource_capacity_consumption_input'],
            ['Product', 'Period', 'Node Group', 'Node', 'Capacity Type'],
            'Periods of Capacity Consumption'
        )

        return parameters