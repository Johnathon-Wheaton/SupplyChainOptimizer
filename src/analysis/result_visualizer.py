from typing import Dict, Any, List
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

class ResultVisualizer:
    """Creates visualizations of optimization results."""
    
    def __init__(self, results: Dict[str, pd.DataFrame]):
        self.results = results
        self.logger = logging.getLogger(__name__)

    def create_network_flow_visual(self) -> Dict[str, Any]:
        """Creates network flow visualization."""
        try:
            if 'departed_product' not in self.results:
                raise ValueError("Flow data not found in results")

            flow_df = self.results['departed_product']
            
            # Create network visualization data
            nodes = pd.concat([
                flow_df['Origin'].unique(),
                flow_df['Destination'].unique()
            ]).unique()
            
            edges = flow_df.groupby(['Origin', 'Destination'])['Value'].sum().reset_index()
            
            return {
                'nodes': [{'id': node, 'label': node} for node in nodes],
                'edges': [
                    {
                        'from': row['Origin'],
                        'to': row['Destination'],
                        'value': row['Value']
                    }
                    for _, row in edges.iterrows()
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Error creating network visualization: {str(e)}")
            raise