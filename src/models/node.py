from typing import Dict, Any, List, Set, Tuple
from dataclasses import dataclass
import pandas as pd
import logging

@dataclass
class Node:
    """Represents a node in the network"""
    name: str
    node_type: str
    node_groups: List[str]
    is_origin: bool
    is_destination: bool
    is_intermediate: bool
    can_receive_from_origins: bool
    can_receive_from_intermediates: bool
    can_send_to_destinations: bool
    can_send_to_intermediates: bool
    min_launches: int
    max_launches: int
    min_operating_duration: int
    max_operating_duration: int
    min_shutdowns: int
    max_shutdowns: int
    min_shutdown_duration: int
    max_shutdown_duration: int