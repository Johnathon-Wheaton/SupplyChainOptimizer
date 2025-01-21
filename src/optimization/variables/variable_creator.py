from typing import Dict, Any, Tuple
import pulp
from itertools import product

class VariableCreator:
    """Creates and manages optimization variables"""

    def __init__(self, network_sets: Dict[str, Any]):
        self.network_sets = network_sets
        self.big_m = 999999999
        
    def create_flow_variables(self) -> Dict[str, Any]:
        """Create variables related to flow in the network"""
        variables = {}
        
        # Main flow variables
        variables['departed_product_by_mode'] = pulp.LpVariable.dicts(
            "departed_product_by_mode",
            ((n_d, n_r, p, t, m) for n_d, n_r, p, t, m in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES']
            )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        variables['departed_product'] = pulp.LpVariable.dicts(
            "departed_product",
            ((n_d, n_r, p, t) for n_d, n_r, p, t in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS']
            )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        variables['processed_product'] = pulp.LpVariable.dicts(
            "processed_product",
            ((n, p, t) for n, p, t in product(
                self.network_sets['NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS']
            )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        variables['arrived_product'] = pulp.LpVariable.dicts(
            "arrived_product",
            ((n_r, p, t) for n_r, p, t in product(
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS']
            )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        return variables

    def create_capacity_variables(self) -> Dict[str, Any]:
        """Create variables related to capacity"""
        variables = {}
        
        variables['use_carrying_capacity_option'] = pulp.LpVariable.dicts(
            "use_carrying_capacity_option",
            ((n, e_c, t) for n, e_c, t in product(
                self.network_sets['NODES'],
                self.network_sets['C_CAPACITY_EXPANSIONS'],
                self.network_sets['PERIODS']
            )),
            lowBound=0,
            cat=pulp.LpInteger
        )
        
        variables['use_transportation_capacity_option'] = pulp.LpVariable.dicts(
            "use_transportation_capacity_option",
            ((o, d, e_t, t) for o, d, e_t, t in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['T_CAPACITY_EXPANSIONS'],
                self.network_sets['PERIODS']
            )),
            lowBound=0,
            cat=pulp.LpInteger
        )

        return variables

    def create_demand_variables(self) -> Dict[str, Any]:
        """Create variables related to demand"""
        variables = {}
        
        # Add all demand-related variables
        variables['arrived_and_completed_product'] = pulp.LpVariable.dicts(
            "arrived_and_completed_product",
            ((t, p, n_r) for t, p, n_r in product(
                self.network_sets['PERIODS'],
                self.network_sets['PRODUCTS'],
                self.network_sets['RECEIVING_NODES']
            )),
            lowBound=0,
            upBound=self.big_m,
            cat=pulp.LpContinuous
        )

        variables['total_arrived_and_completed_product'] = pulp.LpVariable(
            "total_arrived_and_completed_product",
            lowBound=0,
            upBound=self.big_m,
            cat=pulp.LpContinuous
        )

        return variables
        
    def create_cost_variables(self) -> Dict[str, Any]:
        """Create variables related to costs"""
        variables = {}
        
        # Transportation costs
        variables['variable_transportation_costs'] = pulp.LpVariable.dicts(
            "variable_transportation_costs",
            ((o, d, t, m, u) for o, d, t, m, u in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['MEASURES']
            )),
            lowBound=0,
            cat="Continuous"
        )

        variables['fixed_transportation_costs'] = pulp.LpVariable.dicts(
            "fixed_transportation_costs",
            ((o, d, t, m, u) for o, d, t, m, u in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['MEASURES']
            )),
            lowBound=0,
            cat="Continuous"
        )

        # Transportation cost aggregations
        for cost_var in ['transportation_costs', 'od_transportation_costs', 'mode_transportation_costs',
                        'total_od_transportation_costs', 'total_mode_transportation_costs', 
                        'total_time_transportation_costs']:
            if cost_var == 'transportation_costs':
                indices = ((o, d, t, m) for o, d, t, m in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES'],
                    self.network_sets['PERIODS'],
                    self.network_sets['MODES']
                ))
            elif cost_var == 'od_transportation_costs':
                indices = ((o, d, t) for o, d, t in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES'],
                    self.network_sets['PERIODS']
                ))
            elif cost_var == 'mode_transportation_costs':
                indices = ((t, m) for t, m in product(
                    self.network_sets['PERIODS'],
                    self.network_sets['MODES']
                ))
            elif cost_var == 'total_od_transportation_costs':
                indices = ((o, d) for o, d in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES']
                ))
            elif cost_var == 'total_mode_transportation_costs':
                indices = self.network_sets['MODES']
            elif cost_var == 'total_time_transportation_costs':
                indices = self.network_sets['PERIODS']
            
            variables[cost_var] = pulp.LpVariable.dicts(
                cost_var,
                indices,
                lowBound=0,
                cat="Continuous"
            )

        variables['grand_total_transportation_costs'] = pulp.LpVariable(
            "grand_total_transportation_costs",
            lowBound=0,
            cat="Continuous"
        )

        # Operating costs
        for cost_var in ['variable_operating_costs', 'fixed_operating_costs', 'operating_costs',
                        'operating_costs_by_origin', 'total_operating_costs']:
            if cost_var == 'variable_operating_costs':
                indices = ((o, p, t) for o, p, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PRODUCTS'],
                    self.network_sets['PERIODS']
                ))
            elif cost_var == 'fixed_operating_costs':
                indices = ((o, t) for o, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                ))
            elif cost_var == 'operating_costs':
                indices = ((o, t) for o, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                ))
            elif cost_var == 'operating_costs_by_origin':
                indices = self.network_sets['NODES']
            elif cost_var == 'total_operating_costs':
                indices = self.network_sets['PERIODS']
                
            variables[cost_var] = pulp.LpVariable.dicts(
                cost_var,
                indices,
                lowBound=0,
                cat="Continuous"
            )

        variables['grand_total_operating_costs'] = pulp.LpVariable(
            "grand_total_operating_costs",
            lowBound=0,
            cat="Continuous"
        )

        # Launch and shutdown costs
        for cost_var in ['total_launch_cost', 'launch_costs_by_period',
                        'total_shut_down_cost', 'shut_down_costs_by_period']:
            if cost_var in ['total_launch_cost', 'total_shut_down_cost']:
                indices = ((o, t) for o, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                ))
            else:
                indices = self.network_sets['PERIODS']
                
            variables[cost_var] = pulp.LpVariable.dicts(
                cost_var,
                indices,
                lowBound=0,
                cat="Continuous"
            )

        variables['grand_total_launch_cost'] = pulp.LpVariable(
            "grand_total_launch_cost",
            lowBound=0,
            cat="Continuous"
        )
        
        variables['grand_total_shut_down_cost'] = pulp.LpVariable(
            "grand_total_shut_down_cost",
            lowBound=0,
            cat="Continuous"
        )

        return variables

    def create_resource_variables(self) -> Dict[str, Any]:
        """Create variables related to resources"""
        variables = {}
        
        # Resource assignment variables
        for var_name in ['resources_assigned', 'resources_added', 'resources_removed']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                ((r, n, t) for r, n, t in product(
                    self.network_sets['RESOURCES'],
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                )),
                lowBound=0,
                cat=pulp.LpContinuous
            )

        # Resource binary variables
        for var_name in ['resources_added_binary', 'resources_removed_binary']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                ((r, n, t) for r, n, t in product(
                    self.network_sets['RESOURCES'],
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                )),
                lowBound=0,
                cat=pulp.LpBinary
            )

        # Resource cohort variables
        for var_name in ['resource_cohorts_added', 'resource_cohorts_removed']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                ((r, n, t) for r, n, t in product(
                    self.network_sets['RESOURCES'],
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                )),
                lowBound=0,
                cat=pulp.LpInteger
            )

        # Resource capacity
        variables['resource_capacity'] = pulp.LpVariable.dicts(
            "resource_capacity",
            ((r, n, t, c) for r, n, t, c in product(
                self.network_sets['RESOURCES'],
                self.network_sets['NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['RESOURCE_CAPACITY_TYPES']
            )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Resource attributes
        variables['resource_attribute_consumption'] = pulp.LpVariable.dicts(
            "resource_attribute_consumption",
            ((r, t, n, a) for r, t, n, a in product(
                self.network_sets['RESOURCES'],
                self.network_sets['PERIODS'],
                self.network_sets['NODES'],
                self.network_sets['RESOURCE_ATTRIBUTES']
            )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Resource costs
        for cost_var in ['resource_add_cost', 'resource_remove_cost', 'resource_time_cost']:
            variables[cost_var] = pulp.LpVariable.dicts(
                cost_var,
                ((t, n, r) for t, n, r in product(
                    self.network_sets['PERIODS'],
                    self.network_sets['NODES'],
                    self.network_sets['RESOURCES']
                )),
                lowBound=0,
                cat=pulp.LpContinuous
            )

        variables['resource_grand_total_cost'] = pulp.LpVariable(
            "resource_grand_total_cost",
            lowBound=0,
            cat=pulp.LpContinuous
        )

        return variables
    
    def create_load_variables(self) -> Dict[str, Any]:
        """Create variables related to loads and transportation measures"""
        variables = {}
        
        # Load variables
        variables['num_loads_by_group'] = pulp.LpVariable.dicts(
            "num_loads_by_group",
            ((o, d, t, m, g) for o, d, t, m, g in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['TRANSPORTATION_GROUPS']
            )),
            lowBound=0,
            cat="Integer"
        )

        # Load aggregations
        for load_var in ['num_loads', 'od_num_loads', 'mode_num_loads', 'total_od_num_loads',
                        'total_mode_num_loads', 'total_num_loads']:
            if load_var == 'num_loads':
                indices = ((o, d, t, m) for o, d, t, m in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES'],
                    self.network_sets['PERIODS'],
                    self.network_sets['MODES']
                ))
            elif load_var == 'od_num_loads':
                indices = ((o, d, t) for o, d, t in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES'],
                    self.network_sets['PERIODS']
                ))
            elif load_var == 'mode_num_loads':
                indices = ((m, t) for m, t in product(
                    self.network_sets['MODES'],
                    self.network_sets['PERIODS']
                ))
            elif load_var == 'total_od_num_loads':
                indices = ((o, d) for o, d in product(
                    self.network_sets['DEPARTING_NODES'],
                    self.network_sets['RECEIVING_NODES']
                ))
            elif load_var == 'total_mode_num_loads':
                indices = self.network_sets['MODES']
            elif load_var == 'total_num_loads':
                indices = self.network_sets['PERIODS']
                
            variables[load_var] = pulp.LpVariable.dicts(
                load_var,
                indices,
                lowBound=0,
                cat="Continuous"
            )

        variables['grand_total_num_loads'] = pulp.LpVariable(
            "grand_total_num_loads",
            lowBound=0,
            cat="Continuous"
        )

        # Departed measures
        variables['departed_measures'] = pulp.LpVariable.dicts(
            "departed_measures",
            ((o, d, p, t, m, u) for o, d, p, t, m, u in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS'],
                self.network_sets['MODES'],
                self.network_sets['MEASURES']
            )),
            lowBound=0,
            cat='Continuous'
        )

        return variables

    def create_age_variables(self) -> Dict[str, Any]:
        """Create variables related to product aging"""
        variables = {}
        
        # Age tracking variables
        age_var_bases = [
            'vol_arrived_by_age',
            'ib_vol_carried_over_by_age',
            'ob_vol_carried_over_by_age',
            'vol_processed_by_age',
            'vol_dropped_by_age',
            'demand_by_age'
        ]
        
        for var_base in age_var_bases:
            if var_base in ['vol_arrived_by_age', 'ib_vol_carried_over_by_age']:
                nodes = self.network_sets['RECEIVING_NODES']
            elif var_base in ['ob_vol_carried_over_by_age']:
                nodes = self.network_sets['DEPARTING_NODES']
            else:
                nodes = self.network_sets['NODES']
                
            variables[var_base] = pulp.LpVariable.dicts(
                var_base,
                ((n, p, t, a) for n, p, t, a in product(
                    nodes,
                    self.network_sets['PRODUCTS'],
                    self.network_sets['PERIODS'],
                    self.network_sets['AGES']
                )),
                lowBound=0,
                cat=pulp.LpContinuous
            )

        # Departed volume by age
        variables['vol_departed_by_age'] = pulp.LpVariable.dicts(
            "vol_departed_by_age",
            ((n_d, n_r, p, t, a, m) for n_d, n_r, p, t, a, m in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS'],
                self.network_sets['AGES'],
                self.network_sets['MODES']
            )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        # Age violation costs
        variables['age_violation_cost'] = pulp.LpVariable.dicts(
            "age_violation_cost",
            ((n, p, t, a) for n, p, t, a in product(
                self.network_sets['NODES'],
                self.network_sets['PRODUCTS'],
                self.network_sets['PERIODS'],
                self.network_sets['AGES']
            )),
            lowBound=0,
            cat=pulp.LpContinuous
        )

        variables['grand_total_age_violation_cost'] = pulp.LpVariable(
            "grand_total_age_violation_cost",
            lowBound=0,
            cat=pulp.LpContinuous
        )
        
        # Maximum age tracking
        variables['max_age'] = pulp.LpVariable(
            "max_age",
            lowBound=0,
            cat="Integer"
        )
        
        variables['is_age_received'] = pulp.LpVariable.dicts(
            "is_age_received",
            self.network_sets['AGES'],
            cat="Binary"
        )

        return variables

    def create_node_operation_variables(self) -> Dict[str, Any]:
        """Create variables related to node operations (launch/shutdown)"""
        variables = {}
        
        # Basic operation variables
        for var_name in ['is_launched', 'is_shut_down', 'is_site_operating']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                ((o, t) for o, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                )),
                cat="Binary"
            )

        return variables

    def create_pop_variables(self) -> Dict[str, Any]:
        """Create variables related to plan-over-plan changes"""
        variables = {}
        
        # Plan-over-plan base variables
        base_indices = ((t1, t2, p, o, d) for t1, t2, p, o, d in product(
            self.network_sets['PERIODS'],
            self.network_sets['PERIODS'],
            self.network_sets['PRODUCTS'],
            self.network_sets['DEPARTING_NODES'],
            self.network_sets['RECEIVING_NODES']
        ))
        
        for var_name in ['pop_cost', 'volume_moved', 'num_destinations_moved']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                base_indices,
                lowBound=0,
                cat="Continuous"
            )

        # Total metrics
        variables['total_volume_moved'] = pulp.LpVariable(
            "total_volume_moved",
            lowBound=0,
            cat="Continuous"
        )
        
        variables['total_num_destinations_moved'] = pulp.LpVariable(
            "total_num_destinations_moved",
            lowBound=0,
            cat="Continuous"
        )
        
        variables['grand_total_pop_cost'] = pulp.LpVariable(
            "grand_total_pop_cost",
            lowBound=0,
            cat="Continuous"
        )

        # Destination assignment
        variables['binary_product_destination_assignment'] = pulp.LpVariable.dicts(
            "binary_product_destination_assignment",
            ((o, t, p, d) for o, t, p, d in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['PRODUCTS'],
                self.network_sets['RECEIVING_NODES']
            )),
            cat="Binary"
        )
        
        variables['is_destination_assigned_to_origin'] = pulp.LpVariable.dicts(
            "is_destination_assigned_to_origin",
            ((o, d, t) for o, d, t in product(
                self.network_sets['DEPARTING_NODES'],
                self.network_sets['RECEIVING_NODES'],
                self.network_sets['PERIODS']
            )),
            cat="Binary"
        )

        return variables

    def create_carrying_capacity_variables(self) -> Dict[str, Any]:
        """Create variables related to carrying capacity"""
        variables = {}
        
        # Carrying cost variables by category
        for var_name in ['dropped_volume_cost', 'ib_carried_volume_cost', 'ob_carried_volume_cost']:
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                ((n, p, t, a) for n, p, t, a in product(
                    self.network_sets['NODES'],
                    self.network_sets['PRODUCTS'],
                    self.network_sets['PERIODS'],
                    self.network_sets['AGES']
                )),
                lowBound=0,
                cat="Continuous"
            )

        # Cost aggregations by different dimensions
        aggregation_vars = [
            'dropped_volume_cost_by_period',
            'ib_carried_volume_cost_by_period',
            'ob_carried_volume_cost_by_period',
            'dropped_volume_cost_by_product',
            'ib_carried_volume_cost_by_product',
            'ob_carried_volume_cost_by_product',
            'dropped_volume_cost_by_node',
            'ib_carried_volume_cost_by_node',
            'ob_carried_volume_cost_by_node',
            'ib_carried_volume_cost_by_node_time',
            'ob_carried_volume_cost_by_node_time',
            'dropped_volume_cost_by_product_time',
            'ib_carried_volume_cost_by_product_time',
            'ob_carried_volume_cost_by_product_time'
        ]

        for var_name in aggregation_vars:
            if var_name.endswith('_by_period'):
                indices = self.network_sets['PERIODS']
            elif var_name.endswith('_by_product'):
                indices = self.network_sets['PRODUCTS']
            elif var_name.endswith('_by_node'):
                indices = self.network_sets['NODES']
            elif var_name.endswith('_by_node_time'):
                indices = ((n, t) for n, t in product(
                    self.network_sets['NODES'],
                    self.network_sets['PERIODS']
                ))
            elif var_name.endswith('_by_product_time'):
                indices = ((p, t) for p, t in product(
                    self.network_sets['PRODUCTS'],
                    self.network_sets['PERIODS']
                ))
                
            variables[var_name] = pulp.LpVariable.dicts(
                var_name,
                indices,
                lowBound=0,
                cat="Continuous"
            )

        # Total costs
        for var_name in ['total_dropped_volume_cost', 'total_ib_carried_volume_cost',
                        'total_ob_carried_volume_cost', 'grand_total_carried_and_dropped_volume_cost']:
            variables[var_name] = pulp.LpVariable(
                var_name,
                lowBound=0,
                cat="Continuous"
            )

        return variables

    def create_metric_variables(self) -> Dict[str, Any]:
        """Create variables for tracking various metrics"""
        variables = {}
        
        variables['max_transit_distance'] = pulp.LpVariable(
            "max_transit_distance",
            lowBound=0,
            cat="Continuous"
        )
        
        variables['max_capacity_utilization'] = pulp.LpVariable(
            "max_capacity_utilization",
            lowBound=0,
            cat="Continuous"
        )
        
        variables['node_utilization'] = pulp.LpVariable.dicts(
            "node_utilization",
            ((n, t, c) for n, t, c in product(
                self.network_sets['NODES'],
                self.network_sets['PERIODS'],
                self.network_sets['RESOURCE_CAPACITY_TYPES']
            )),
            lowBound=0,
            cat="Continuous"
        )

        return variables
    
    def get_variable_dimensions(self) -> Dict[str, List[str]]:
        """Get dimensions for all variables
        
        Returns:
            Dictionary mapping variable names to their dimension lists
        """
        dimensions = {
            # Flow variables
            'departed_product_by_mode': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PRODUCTS', 'PERIODS', 'MODES'],
            'departed_product': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PRODUCTS', 'PERIODS'],
            'processed_product': ['NODES', 'PRODUCTS', 'PERIODS'],
            'arrived_product': ['RECEIVING_NODES', 'PRODUCTS', 'PERIODS'],

            # Capacity variables
            'use_carrying_capacity_option': ['NODES', 'C_CAPACITY_EXPANSIONS', 'PERIODS'],
            'use_transportation_capacity_option': ['DEPARTING_NODES', 'RECEIVING_NODES', 'T_CAPACITY_EXPANSIONS', 'PERIODS'],

            # Demand variables
            'arrived_and_completed_product': ['PERIODS', 'PRODUCTS', 'RECEIVING_NODES'],
            'total_arrived_and_completed_product': [],

            # Cost variables
            'variable_transportation_costs': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS', 'MODES', 'MEASURES'],
            'fixed_transportation_costs': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS', 'MODES', 'MEASURES'],
            'transportation_costs': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS', 'MODES'],
            'od_transportation_costs': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS'],
            'mode_transportation_costs': ['PERIODS', 'MODES'],
            'total_od_transportation_costs': ['DEPARTING_NODES', 'RECEIVING_NODES'],
            'total_mode_transportation_costs': ['MODES'],
            'total_time_transportation_costs': ['PERIODS'],
            'grand_total_transportation_costs': [],

            # Operating costs
            'variable_operating_costs': ['NODES', 'PRODUCTS', 'PERIODS'],
            'fixed_operating_costs': ['NODES', 'PERIODS'],
            'operating_costs': ['NODES', 'PERIODS'],
            'operating_costs_by_origin': ['NODES'],
            'total_operating_costs': ['PERIODS'],
            'grand_total_operating_costs': [],

            # Resource variables
            'resources_assigned': ['RESOURCES', 'NODES', 'PERIODS'],
            'resources_added': ['RESOURCES', 'NODES', 'PERIODS'],
            'resources_removed': ['RESOURCES', 'NODES', 'PERIODS'],
            'resources_added_binary': ['RESOURCES', 'NODES', 'PERIODS'],
            'resources_removed_binary': ['RESOURCES', 'NODES', 'PERIODS'],
            'resource_cohorts_added': ['RESOURCES', 'NODES', 'PERIODS'],
            'resource_cohorts_removed': ['RESOURCES', 'NODES', 'PERIODS'],
            'resource_capacity': ['RESOURCES', 'NODES', 'PERIODS', 'RESOURCE_CAPACITY_TYPES'],
            'resource_attribute_consumption': ['RESOURCES', 'PERIODS', 'NODES', 'RESOURCE_ATTRIBUTES'],
            'resource_add_cost': ['PERIODS', 'NODES', 'RESOURCES'],
            'resource_remove_cost': ['PERIODS', 'NODES', 'RESOURCES'],
            'resource_time_cost': ['PERIODS', 'NODES', 'RESOURCES'],
            'resource_grand_total_cost': [],

            # Load variables
            'num_loads_by_group': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS', 'MODES', 'TRANSPORTATION_GROUPS'],
            'num_loads': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS', 'MODES'],
            'od_num_loads': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS'],
            'mode_num_loads': ['MODES', 'PERIODS'],
            'total_od_num_loads': ['DEPARTING_NODES', 'RECEIVING_NODES'],
            'total_mode_num_loads': ['MODES'],
            'total_num_loads': ['PERIODS'],
            'grand_total_num_loads': [],
            'departed_measures': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PRODUCTS', 'PERIODS', 'MODES', 'MEASURES'],

            # Age variables
            'vol_arrived_by_age': ['RECEIVING_NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'ib_vol_carried_over_by_age': ['RECEIVING_NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'ob_vol_carried_over_by_age': ['DEPARTING_NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'vol_processed_by_age': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'vol_dropped_by_age': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'demand_by_age': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'vol_departed_by_age': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PRODUCTS', 'PERIODS', 'AGES', 'MODES'],
            'age_violation_cost': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'grand_total_age_violation_cost': [],
            'max_age': [],
            'is_age_received': ['AGES'],

            # Node operation variables
            'is_launched': ['NODES', 'PERIODS'],
            'is_shut_down': ['NODES', 'PERIODS'],
            'is_site_operating': ['NODES', 'PERIODS'],
            'total_launch_cost': ['NODES', 'PERIODS'],
            'launch_costs_by_period': ['PERIODS'],
            'grand_total_launch_cost': [],
            'total_shut_down_cost': ['NODES', 'PERIODS'],
            'shut_down_costs_by_period': ['PERIODS'],
            'grand_total_shut_down_cost': [],

            # Plan-over-plan variables
            'pop_cost': ['PERIODS', 'PERIODS', 'PRODUCTS', 'DEPARTING_NODES', 'RECEIVING_NODES'],
            'volume_moved': ['PERIODS', 'PERIODS', 'PRODUCTS', 'DEPARTING_NODES', 'RECEIVING_NODES'],
            'num_destinations_moved': ['PERIODS', 'PERIODS', 'PRODUCTS', 'DEPARTING_NODES', 'RECEIVING_NODES'],
            'total_volume_moved': [],
            'total_num_destinations_moved': [],
            'grand_total_pop_cost': [],
            'binary_product_destination_assignment': ['DEPARTING_NODES', 'PERIODS', 'PRODUCTS', 'RECEIVING_NODES'],
            'is_destination_assigned_to_origin': ['DEPARTING_NODES', 'RECEIVING_NODES', 'PERIODS'],

            # Carrying capacity variables
            'dropped_volume_cost': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'ib_carried_volume_cost': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'ob_carried_volume_cost': ['NODES', 'PRODUCTS', 'PERIODS', 'AGES'],
            'dropped_volume_cost_by_period': ['PERIODS'],
            'ib_carried_volume_cost_by_period': ['PERIODS'],
            'ob_carried_volume_cost_by_period': ['PERIODS'],
            'dropped_volume_cost_by_product': ['PRODUCTS'],
            'ib_carried_volume_cost_by_product': ['PRODUCTS'],
            'ob_carried_volume_cost_by_product': ['PRODUCTS'],
            'dropped_volume_cost_by_node': ['NODES'],
            'ib_carried_volume_cost_by_node': ['NODES'],
            'ob_carried_volume_cost_by_node': ['NODES'],
            'ib_carried_volume_cost_by_node_time': ['NODES', 'PERIODS'],
            'ob_carried_volume_cost_by_node_time': ['NODES', 'PERIODS'],
            'dropped_volume_cost_by_product_time': ['PRODUCTS', 'PERIODS'],
            'ib_carried_volume_cost_by_product_time': ['PRODUCTS', 'PERIODS'],
            'ob_carried_volume_cost_by_product_time': ['PRODUCTS', 'PERIODS'],
            'total_dropped_volume_cost': [],
            'total_ib_carried_volume_cost': [],
            'total_ob_carried_volume_cost': [],
            'grand_total_carried_and_dropped_volume_cost': [],

            # Metric variables
            'max_transit_distance': [],
            'max_capacity_utilization': [],
            'node_utilization': ['NODES', 'PERIODS', 'RESOURCE_CAPACITY_TYPES']
        }
        
        return dimensions

     def create_all_variables(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Create all optimization variables
        
        Returns:
            Tuple containing:
            - Dictionary of all variables
            - Dictionary of variable dimensions
        """
        variables = {}
        dimensions = self.get_variable_dimensions()

        # Combine variables from all categories
        variables.update(self.create_flow_variables())
        variables.update(self.create_capacity_variables())
        variables.update(self.create_demand_variables())
        variables.update(self.create_cost_variables())
        variables.update(self.create_resource_variables())
        variables.update(self.create_load_variables())
        variables.update(self.create_age_variables())
        variables.update(self.create_node_operation_variables())
        variables.update(self.create_pop_variables())
        variables.update(self.create_carrying_capacity_variables())
        variables.update(self.create_metric_variables())

        return variables, dimensions