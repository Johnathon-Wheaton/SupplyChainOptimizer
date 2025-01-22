from typing import Dict, List, Any
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Set, Tuple
from .node import Node

class Network:
    """Represents the supply chain network structure"""
    
    def __init__(self, input_data: Dict[str, pd.DataFrame]):
        """Initialize network from input data
        
        Args:
            input_data: Dictionary containing all input DataFrames
        """
        self.input_data = input_data
        self.nodes: Dict[str, Node] = {}
        self._initialize_nodes()
        self._initialize_sets()
        self.validate_network()
        
    def _initialize_sets(self) -> None:
        """Initialize all network sets from input data"""
        # Nodes and node types
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
            "NODES": self.nodes.keys(),
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

    def _initialize_nodes(self) -> None:
        """Initialize node objects from input data"""
        nodes_df = self.input_data['nodes_input']
        node_groups_df = self.input_data['node_groups_input']

        # Get node groups for each node
        node_groups = {}
        for _, row in node_groups_df.iterrows():
            if row['Node'] not in node_groups:
                node_groups[row['Node']] = []
            node_groups[row['Node']].append(row['Group'])

        # Create Node objects
        for _, row in nodes_df.iterrows():
            self.nodes[row['Name']] = Node(
                name=row['Name'],
                node_type=row['Node Type'],
                node_groups=node_groups.get(row['Name'], []),
                is_origin=row['Origin Node'] == "X",
                is_destination=row['Destination Node'] == "X",
                is_intermediate=row['Intermediate Node'] == "X",
                can_receive_from_origins=row['Receive from Origins'] == "X",
                can_receive_from_intermediates=row['Receive from Intermediates'] == "X",
                can_send_to_destinations=row['Send to Destinations'] == "X",
                can_send_to_intermediates=row['Send to Intermediates'] == "X",
                min_launches=row['Min Launches'],
                max_launches=row['Max Launches'],
                min_operating_duration=row['Min Operating Duration'],
                max_operating_duration=row['Max Operating Duration'],
                min_shutdowns=row['Min Shutdowns'],
                max_shutdowns=row['Max Launches'],
                min_shutdown_duration=row['Min Shutdown Duration'],
                max_shutdown_duration=row['Max Shutdown Duration']
            )

    def validate_network(self) -> None:
        """Validate network structure and configuration"""
        self._validate_node_connections()
        self._validate_node_types()
        self._validate_node_groups()
        self._validate_flow_paths()

    def _validate_node_connections(self) -> None:
        """Validate node connection rules"""
        for node in self.nodes.values():
            if node.is_origin and node.can_receive_from_origins:
                logging.warning(f"Origin node {node.name} should not receive from origins")
            if node.is_destination and node.can_send_to_destinations:
                logging.warning(f"Destination node {node.name} should not send to destinations")

    def _validate_node_types(self) -> None:
        """Validate node type configurations"""
        for node in self.nodes.values():
            if sum([node.is_origin, node.is_destination, node.is_intermediate]) != 1:
                raise ValueError(f"Node {node.name} must be exactly one type: origin, destination, or intermediate")

    def _validate_node_groups(self) -> None:
        """Validate node group assignments"""
        for node in self.nodes.values():
            if not node.node_groups:
                logging.warning(f"Node {node.name} is not assigned to any groups")

    def _validate_flow_paths(self) -> None:
        """Validate that valid flow paths exist"""
        # Check connectivity from origins to destinations
        reachable_nodes = self._get_reachable_nodes()
        unreachable_destinations = [
            node.name for node in self.nodes.values()
            if node.is_destination and node.name not in reachable_nodes
        ]
        if unreachable_destinations:
            logging.warning(f"Destinations unreachable from any origin: {unreachable_destinations}")

    def _get_reachable_nodes(self) -> Set[str]:
        """Get set of nodes reachable from origins"""
        reachable = set()
        queue = [node.name for node in self.nodes.values() if node.is_origin]
        while queue:
            current = queue.pop(0)
            if current not in reachable:
                reachable.add(current)
                queue.extend(self._get_downstream_nodes(current))
        return reachable

    def _get_downstream_nodes(self, node_name: str) -> List[str]:
        """Get list of nodes that can receive from given node"""
        node = self.nodes[node_name]
        downstream = []
        for other in self.nodes.values():
            if node.is_origin:
                if other.can_receive_from_origins:
                    downstream.append(other.name)
            elif node.is_intermediate:
                if other.can_receive_from_intermediates:
                    downstream.append(other.name)
        return downstream

    def get_node_distances(self) -> Dict[Tuple[str, str], float]:
        """Get dictionary of distances between connected nodes"""
        distances = {}
        distance_df = self.input_data['od_distances_and_transit_times_input']
        
        for _, row in distance_df.iterrows():
            distances[(row['Origin'], row['Destination'])] = row['Distance']
        return distances

    def get_node_transit_times(self) -> Dict[Tuple[str, str], float]:
        """Get dictionary of transit times between connected nodes"""
        transit_times = {}
        transit_df = self.input_data['od_distances_and_transit_times_input']
        
        for _, row in transit_df.iterrows():
            transit_times[(row['Origin'], row['Destination'])] = row['Transit Time']
        return transit_times

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get list of nodes of specified type"""
        return [node for node in self.nodes.values() if node.node_type == node_type]

    def get_nodes_by_group(self, group: str) -> List[Node]:
        """Get list of nodes in specified group"""
        return [node for node in self.nodes.values() if group in node.node_groups]

    def get_node_connections(self) -> Dict[str, List[str]]:
        """Get dictionary mapping nodes to their possible downstream nodes"""
        connections = {}
        for node in self.nodes.values():
            connections[node.name] = self._get_downstream_nodes(node.name)
        return connections

    def analyze_network_structure(self) -> Dict[str, Any]:
        """Analyze network structure and return metrics"""
        return {
            'num_nodes': len(self.nodes),
            'num_origins': len([n for n in self.nodes.values() if n.is_origin]),
            'num_destinations': len([n for n in self.nodes.values() if n.is_destination]),
            'num_intermediates': len([n for n in self.nodes.values() if n.is_intermediate]),
            'node_types': len(set(n.node_type for n in self.nodes.values())),
            'node_groups': len(set(g for n in self.nodes.values() for g in n.node_groups)),
            'avg_connections': sum(len(self._get_downstream_nodes(n)) 
                                 for n in self.nodes) / len(self.nodes)
        }