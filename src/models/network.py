from typing import Dict, List, Any
import pandas as pd
import numpy as np

class Network:
    """Represents the supply chain network structure"""
    
    def __init__(self, input_data: Dict[str, pd.DataFrame]):
        """Initialize network from input data
        
        Args:
            input_data: Dictionary containing all input DataFrames
        """
        self.input_data = input_data
        self._initialize_sets()
        
    def _initialize_sets(self) -> None:
        """Initialize all network sets from input data"""
        # Nodes and node types
        self.nodes = self.input_data['nodes_input']['Name'].unique()
        self.node_types = self.input_data['node_types_input']['Node Type'].unique()
        self.node_groups = self.input_data['node_groups_input']['Group'].unique()
        
        # Origin/destination nodes
        self.origins = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Origin Node']=="X"
        ]['Name'].unique()
        
        self.destinations = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Destination Node']=="X"
        ]['Name'].unique()
        
        # Intermediate nodes
        self.receive_from_origin_nodes = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Receive from Origins']=="X"
        ]['Name'].unique()
        
        self.receive_from_intermediates_nodes = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Receive from Intermediates']=="X"
        ]['Name'].unique()
        
        self.send_to_destinations_nodes = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Send to Destinations']=="X"
        ]['Name'].unique()
        
        self.send_to_intermediates_nodes = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Send to Intermediates']=="X"
        ]['Name'].unique()
        
        self.intermediates = self.input_data['nodes_input'][
            self.input_data['nodes_input']['Intermediate Node']=="X"
        ]['Name'].unique()
        
        # Combined node sets
        self.departing_nodes = np.unique(np.concatenate((self.intermediates, self.origins)))
        self.receiving_nodes = np.unique(np.concatenate((self.intermediates, self.destinations)))
        
        # Time periods
        self.periods = list(map(str, self.input_data['periods_input']['Period'].unique()))
        self.ages = [str(int(age)-1) for age in self.periods]
        
        # Products and measures
        self.products = self.input_data['products_input']['Product'].unique()
        measures = self.input_data['products_input']['Measure'].unique()
        self.measures = [measure for measure in measures if measure != "*"]
        
        # Transportation
        containers = self.input_data['transportation_costs_input']['Container'].unique()
        self.containers = [container for container in containers if container != "*"]
        modes = self.input_data['transportation_costs_input']['Mode'].unique()
        self.modes = [mode for mode in modes if mode != "*"]
        
        # Capacity expansions
        c_capacity_expansions = self.input_data['carrying_expansions_input']['Incremental Capacity Label'].unique()
        self.c_capacity_expansions = c_capacity_expansions if len(c_capacity_expansions) > 0 else ["NA"]
        
        t_capacity_expansions = self.input_data['transportation_expansions_input']['Incremental Capacity Label'].unique()
        self.t_capacity_expansions = t_capacity_expansions if len(t_capacity_expansions) > 0 else ["NA"]
        
        # Transportation groups
        self.transportation_groups = self.input_data['product_transportation_groups_input']['Group'].unique()
        
        # Resources
        self.resources = self.input_data['resource_costs_input']['Resource'].unique()
        self.resource_capacity_types = self.input_data['resource_capacity_types_input']['Capacity Type'].unique()
        
        resource_parent_capacity_types = self.input_data['resource_capacity_types_input']['Parent Capacity Type'].unique()
        self.resource_parent_capacity_types = [cap_type for cap_type in resource_parent_capacity_types if pd.notna(cap_type)]
        self.resource_child_capacity_types = [cap_type for cap_type in self.resource_capacity_types 
                                            if cap_type not in self.resource_parent_capacity_types]
        
        # Resource attributes
        resource_attributes = self.input_data['resource_attributes_input']['Resource Attribute'].unique()
        self.resource_attributes = resource_attributes if len(resource_attributes) > 0 else ["NA"]

    def get_all_sets(self) -> Dict[str, List]:
        """Get dictionary of all network sets
        
        Returns:
            Dictionary containing all network sets
        """
        return {
            "NODES": self.nodes,
            "NODETYPES": self.node_types,
            "NODEGROUPS": self.node_groups.tolist(),
            "ORIGINS": self.origins,
            "DESTINATIONS": self.destinations,
            "RECEIVE_FROM_ORIGIN_NODES": self.receive_from_origin_nodes,
            "RECEIVE_FROM_INTERMEDIATES_NODES": self.receive_from_intermediates_nodes,
            "SEND_TO_DESTINATIONS_NODES": self.send_to_destinations_nodes,
            "SEND_TO_INTERMEDIATES_NODES": self.send_to_intermediates_nodes,
            "INTERMEDIATES": self.intermediates,
            "DEPARTING_NODES": self.departing_nodes,
            "RECEIVING_NODES": self.receiving_nodes,
            "PERIODS": self.periods,
            "AGES": self.ages,
            "PRODUCTS": self.products,
            "MEASURES": self.measures,
            "CONTAINERS": self.containers,
            "MODES": self.modes,
            "C_CAPACITY_EXPANSIONS": self.c_capacity_expansions,
            "T_CAPACITY_EXPANSIONS": self.t_capacity_expansions,
            "TRANSPORTATION_GROUPS": self.transportation_groups,
            "RESOURCES": self.resources.tolist(),
            "RESOURCE_CAPACITY_TYPES": self.resource_capacity_types.tolist(),
            "RESOURCE_PARENT_CAPACITY_TYPES": self.resource_parent_capacity_types,
            "RESOURCE_CHILD_CAPACITY_TYPES": self.resource_child_capacity_types,
            "RESOURCE_ATTRIBUTES": self.resource_attributes,
        }