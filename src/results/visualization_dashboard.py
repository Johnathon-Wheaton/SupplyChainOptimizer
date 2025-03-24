"""
PuLP Solver Visualization Module
This module creates interactive dashboards for PuLP solver results, supporting both 
transportation networks (with maps) and resource-task networks (with graphs).
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import plotly.express as px
import plotly.graph_objs as go
import networkx as nx
from dash_ag_grid import AgGrid
import dash_cytoscape as cyto
import dash_mantine_components as dmc


class PulpViz:
    """Main class for PuLP visualization dashboard."""
    
    def __init__(self, input_file=None, results_file=None, title="Solver Results Dashboard"):
        """
        Initialize the PuLP visualization dashboard.
        
        Args:
            input_file (str): Path to the input file (Excel or JSON)
            results_file (str): Path to the results file (Excel or JSON)
            title (str): Title for the dashboard
        """
        self.title = title
        self.input_file = input_file
        self.results_file = results_file
        self.data = {}
        self.has_lat_lon = False
        self.has_periods = False
        self.periods = []
        self.app = dash.Dash(__name__, 
                            external_stylesheets=[dbc.themes.BOOTSTRAP],
                            suppress_callback_exceptions=True)
        
        # Load and process data if files are provided
        if input_file and results_file:
            self.load_data(input_file, results_file)
            self.create_dashboard()
    
    def load_data(self, input_file, results_file):
        """
        Load data from input and results files.
        
        Args:
            input_file (str): Path to the input file (Excel or JSON)
            results_file (str): Path to the results file (Excel or JSON)
        """
        self.input_file = input_file
        self.results_file = results_file
        
        # Load input data based on file extension
        input_ext = os.path.splitext(input_file)[1].lower()
        if input_ext == '.xlsx' or input_ext == '.xls':
            self.data['input'] = self._load_excel(input_file)
        elif input_ext == '.json':
            self.data['input'] = self._load_json(input_file)
        else:
            raise ValueError(f"Unsupported input file format: {input_ext}")
        
        # Load results data based on file extension
        sheet_names = ['vol_departed_by_age', 
            'vol_processed_by_age', 
            'vol_arrived_by_age', 
            'ib_vol_carried_over_by_age', 
            'ob_vol_carried_over_by_age', 
            'vol_dropped_by_age', 
            'use_carrying_capacity_option', 
            'use_transportation_capacit (1)', 
            'arrived_and_completed_product', 
            'variable_transportation_costs', 
            'fixed_transportation_costs', 
            'variable_operating_costs', 
            'fixed_operating_costs', 
            'total_launch_cost', 
            'total_shut_down_cost', 
            'resources_assigned', 
            'resources_added', 
            'resources_removed', 
            'resource_capacity', 
            'resource_attribute_consumption', 
            'resource_add_cost', 
            'resource_remove_cost', 
            'resource_time_cost', 
            'num_loads_by_group', 
            'departed_measures', 
            'demand_by_age', 
            'age_violation_cost', 
            'pop_cost', 
            'volume_moved']
        
        results_ext = os.path.splitext(results_file)[1].lower()
        if results_ext == '.xlsx' or results_ext == '.xls':
            self.data['results'] = self._load_excel(results_file, sheet_names)
        elif results_ext == '.json':
            self.data['results'] = self._load_json(results_file, sheet_names)
        else:
            raise ValueError(f"Unsupported results file format: {results_ext}")
        
        # Check if the data has lat/lon coordinates
        self.has_lat_lon = self._check_for_lat_lon()
        
        # Process the data for visualization
        self._process_data()
    
    def _load_excel(self, file_path, sheet_names = None):
        """
        Load data from Excel file.
        
        Args:
            file_path (str): Path to the Excel file
            
        Returns:
            dict: Dictionary with sheet names as keys and pandas DataFrames as values
        """
        # Load all sheets from Excel file
        excel_data={}
        if sheet_names is not None:
            for sheet in sheet_names:
                try:
                    excel_data[sheet] = pd.read_excel(file_path, sheet_name=sheet)
                except:
                    print(f"Warning: Sheet '{sheet}' not found in Excel file")
        else:
            excel_data = pd.read_excel(file_path, sheet_name=None)
        return excel_data
    
    def _load_json(self, file_path, sheet_names=None):
        """
        Load data from JSON file.
        
        Args:
            file_path (str): Path to the JSON file
            
        Returns:
            dict: Dictionary with data from JSON file
        """
        with open(file_path, 'r') as f:
            json_data = json.load(f)
        
        # Convert JSON data to pandas DataFrames where possible
        processed_data = {}
        if isinstance(json_data, dict):
            if sheet_names is not None:
                # Process only the specified keys
                for key in sheet_names:
                    if key in json_data:
                        value = json_data[key]
                        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                            processed_data[key] = pd.DataFrame(value)
                        else:
                            processed_data[key] = value
                    else:
                        print(f"Warning: Key '{key}' not found in JSON data")
            else:
                # Process all keys (original behavior)
                for key, value in json_data.items():
                    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                        processed_data[key] = pd.DataFrame(value)
                    else:
                        processed_data[key] = value

        return processed_data
    
    def _check_for_lat_lon(self):
        """
        Check if the input data has latitude and longitude coordinates.
        
        Returns:
            bool: True if lat/lon coordinates are found, False otherwise
        """
        if 'input' not in self.data:
            return False
        
        # Check for Nodes sheet in Excel input
        if 'Nodes' in self.data['input']:
            nodes_df = self.data['input']['Nodes']
            
            # Common column names for latitude and longitude
            lat_cols = ['Latitude', 'latitude', 'lat', 'Lat']
            lon_cols = ['Longitude', 'longitude', 'lon', 'Lon']
            
            # Check if any of the latitude column names exist
            has_lat = any(col in nodes_df.columns for col in lat_cols)
            
            # Check if any of the longitude column names exist
            has_lon = any(col in nodes_df.columns for col in lon_cols)
            
            return has_lat and has_lon
        
        # For JSON input, check for nodes with lat/lon properties
        elif 'nodes' in self.data['input']:
            nodes = self.data['input']['nodes']
            if isinstance(nodes, pd.DataFrame) and len(nodes) > 0:
                # Check DataFrame columns
                lat_cols = ['Latitude', 'latitude', 'lat', 'Lat']
                lon_cols = ['Longitude', 'longitude', 'lon', 'Lon']
                
                has_lat = any(col in nodes.columns for col in lat_cols)
                has_lon = any(col in nodes.columns for col in lon_cols)
                
                return has_lat and has_lon
            elif isinstance(nodes, list) and len(nodes) > 0:
                # Check dictionary keys in the first node
                if isinstance(nodes[0], dict):
                    first_node = nodes[0]
                    
                    lat_keys = ['Latitude', 'latitude', 'lat', 'Lat']
                    lon_keys = ['Longitude', 'longitude', 'lon', 'Lon']
                    
                    has_lat = any(key in first_node for key in lat_keys)
                    has_lon = any(key in first_node for key in lon_keys)
                    
                    return has_lat and has_lon
        
        return False
    
    def _get_lat_lon_columns(self):
        """
        Get the column names for latitude and longitude.
        
        Returns:
            tuple: (latitude_column, longitude_column)
        """
        if 'Nodes' not in self.data['input']:
            return None, None
        
        nodes_df = self.data['input']['Nodes']
        
        # Common column names for latitude and longitude
        lat_cols = ['Latitude', 'latitude', 'lat', 'Lat']
        lon_cols = ['Longitude', 'longitude', 'lon', 'Lon']
        
        # Find the first matching column name
        lat_col = next((col for col in lat_cols if col in nodes_df.columns), None)
        lon_col = next((col for col in lon_cols if col in nodes_df.columns), None)
        
        return lat_col, lon_col
    
    def _process_data(self):
        """Process the data for visualization."""
        if 'input' not in self.data or 'results' not in self.data:
            print("DEBUG: Missing input or results data")
            return
        
        # Process nodes data
        if 'Nodes' in self.data['input']:
            nodes_df = self.data['input']['Nodes']
            print(f"DEBUG: Nodes data shape: {nodes_df.shape}")
            
            # Get node name column (usually 'Name')
            name_col = 'Name' if 'Name' in nodes_df.columns else nodes_df.columns[1]
            print(f"DEBUG: Using '{name_col}' as node name column")
            
            # Store nodes with their properties
            self.data['nodes'] = nodes_df
            
            # If we have lat/lon, prepare nodes for map visualization
            if self.has_lat_lon:
                lat_col, lon_col = self._get_lat_lon_columns()
                print(f"DEBUG: Found lat/lon columns: {lat_col}, {lon_col}")
                if lat_col and lon_col:
                    self.data['node_locations'] = nodes_df[[name_col, lat_col, lon_col]].copy()
                    self.data['node_locations'].columns = ['name', 'latitude', 'longitude']
                    print(f"DEBUG: Processed node_locations shape: {self.data['node_locations'].shape}")
                    print(f"DEBUG: First few node locations:\n{self.data['node_locations'].head()}")
                else:
                    print("DEBUG: lat_col or lon_col is None")
            else:
                print("DEBUG: No lat/lon data (self.has_lat_lon is False)")
        
        # Process flow data for edges
        flow_sheets = [sheet for sheet in self.data['results'].keys() 
                    if any(term in sheet.lower() for term in ['departed', 'flow', 'transport'])]
        
        if flow_sheets:
            # Use the first matching sheet
            flow_sheet = flow_sheets[0]
            flow_df = self.data['results'][flow_sheet]
            print(f"DEBUG: Using flow sheet: {flow_sheet}")
            print(f"DEBUG: Flow data shape: {flow_df.shape}")
            print(f"DEBUG: Flow data columns: {flow_df.columns.tolist()}")
            
            # Store the original flow data for filtering by period later
            self.data['flow_data'] = flow_df.copy()
            
            # Check if we have PERIODS column for filtering
            self.has_periods = 'PERIODS' in flow_df.columns
            if self.has_periods:
                # Get all unique periods for the filter dropdown
                self.periods = sorted(flow_df['PERIODS'].unique())
                print(f"DEBUG: Found periods: {self.periods}")
            
            # Check for Scenario column for filtering
            self.has_scenarios = 'Scenario' in flow_df.columns
            if self.has_scenarios:
                # Get all unique scenarios for the filter dropdown
                self.scenarios = sorted(flow_df['Scenario'].unique())
                print(f"DEBUG: Found scenarios: {self.scenarios}")
            
            # Check for Scenario column
            has_scenario = 'Scenario' in flow_df.columns
            print(f"DEBUG: Has Scenario column: {has_scenario}")
            
            if has_scenario:
                scenarios = flow_df['Scenario'].unique().tolist()
                print(f"DEBUG: Found scenarios: {scenarios}")
            
            # Identify origin and destination columns
            origin_cols = [col for col in flow_df.columns 
                        if any(term in col.lower() for term in ['origin', 'departing', 'from'])]
            
            dest_cols = [col for col in flow_df.columns 
                        if any(term in col.lower() for term in ['destination', 'receiving', 'to'])]
            
            if origin_cols and dest_cols:
                origin_col = origin_cols[0]
                dest_col = dest_cols[0]
                print(f"DEBUG: Origin column: {origin_col}")
                print(f"DEBUG: Destination column: {dest_col}")
                
                # Find value column
                value_cols = [col for col in flow_df.columns 
                            if col.lower() == flow_sheet.lower() or 
                            any(term in col.lower() for term in ['departed_product_by_mode', 'value', 'volume', 'quantity'])]
                
                value_col = value_cols[0] if value_cols else flow_df.columns[-1]
                print(f"DEBUG: Value column: {value_col}")
                
                # Process edges data based on whether we have Scenario column
                if has_scenario:
                    print("DEBUG: Processing edges with scenarios")
                    edges_list = []
                    
                    for scenario in scenarios:
                        scenario_df = flow_df[flow_df['Scenario'] == scenario]
                        
                        # If we have time periods, select the latest period
                        if 'PERIODS' in scenario_df.columns:
                            # Get all periods to create a time series
                            periods = sorted(scenario_df['PERIODS'].unique())
                            latest_period = periods[-1]
                            
                            # Process data for the latest period
                            period_df = scenario_df[scenario_df['PERIODS'] == latest_period]
                            period_edges = period_df.groupby([origin_col, dest_col])[value_col].sum().reset_index()
                            period_edges['Scenario'] = scenario
                            period_edges['Period'] = latest_period
                            
                            edges_list.append(period_edges)
                        else:
                            # No periods, just group by origin and destination
                            scenario_edges = scenario_df.groupby([origin_col, dest_col])[value_col].sum().reset_index()
                            scenario_edges['Scenario'] = scenario
                            
                            edges_list.append(scenario_edges)
                    
                    # Combine all edges
                    if edges_list:
                        combined_edges = pd.concat(edges_list)
                        
                        # Rename columns for consistency
                        if 'Period' in combined_edges.columns:
                            combined_edges.columns = ['source', 'target', 'value', 'Scenario', 'Period']
                        else:
                            combined_edges.columns = ['source', 'target', 'value', 'Scenario']
                        
                        # Filter to keep only edges with positive values
                        combined_edges = combined_edges[combined_edges['value'] > 0]
                        
                        self.data['edges'] = combined_edges
                        print(f"DEBUG: Processed edges shape: {combined_edges.shape}")
                        print(f"DEBUG: First few edges:\n{combined_edges.head()}")
                    else:
                        print("DEBUG: No edges data generated")
                else:
                    print("DEBUG: Processing edges without scenarios")
                    # No Scenario column, process as before
                    if 'PERIODS' in flow_df.columns:
                        # If we have time periods, select the most recent one
                        latest_period = flow_df['PERIODS'].max()
                        edges_df = flow_df[flow_df['PERIODS'] == latest_period].groupby(
                            [origin_col, dest_col])[value_col].sum().reset_index()
                    else:
                        edges_df = flow_df.groupby([origin_col, dest_col])[value_col].sum().reset_index()
                    
                    edges_df.columns = ['source', 'target', 'value']
                    
                    # Add a default scenario
                    edges_df['Scenario'] = 'Default'
                    
                    # Filter to keep only edges with positive values
                    edges_df = edges_df[edges_df['value'] > 0]
                    
                    self.data['edges'] = edges_df
                    print(f"DEBUG: Processed edges shape: {edges_df.shape}")
                    print(f"DEBUG: First few edges:\n{edges_df.head()}")
            else:
                print(f"DEBUG: Could not identify origin/destination columns. Available columns: {flow_df.columns.tolist()}")
        else:
            print("DEBUG: No flow sheets found")
                
    def create_map_figure(self):
        """
        Create a map visualization of the network with scenarios as layers,
        origin nodes with color palette, edges colored by origin,
        and destination nodes in dark blue.
        
        Returns:
            plotly.graph_objects.Figure: Map figure
        """
        print("DEBUG: Creating enhanced map figure")
        if not self.has_lat_lon:
            print("DEBUG: No lat/lon data available")
            return go.Figure()
        
        if 'node_locations' not in self.data:
            print("DEBUG: No node_locations data available")
            return go.Figure()
            
        if 'edges' not in self.data:
            print("DEBUG: No edges data available")
            return go.Figure()
        
        nodes = self.data['node_locations']
        edges = self.data['edges']
        
        print(f"DEBUG: Number of nodes: {len(nodes)}")
        print(f"DEBUG: Number of edges: {len(edges)}")
        
        if len(nodes) == 0:
            print("DEBUG: Empty nodes dataframe")
            return go.Figure()
            
        if len(edges) == 0:
            print("DEBUG: Empty edges dataframe")
            # Still continue to at least show the nodes
        
        # Find the Scenario column from the original data to create layers
        flow_sheets = [sheet for sheet in self.data['results'].keys() 
                    if any(term in sheet.lower() for term in ['departed', 'flow', 'transport'])]
        
        scenarios = []
        if flow_sheets:
            flow_sheet = flow_sheets[0]
            flow_df = self.data['results'][flow_sheet]
            
            if 'Scenario' in flow_df.columns:
                # Get unique scenarios for layers
                scenarios = flow_df['Scenario'].unique().tolist()
                # Join the original Scenario data with the edges dataframe
                origin_col = [col for col in flow_df.columns if any(term in col.lower() for term in ['origin', 'departing', 'from'])][0]
                dest_col = [col for col in flow_df.columns if any(term in col.lower() for term in ['destination', 'receiving', 'to'])][0]
                value_col = flow_df.columns[-1]
                
                # We need to recreate the edges with the Scenario column included
                edges_with_scenario = []
                
                # Group by Scenario, origin, and destination
                for scenario in scenarios:
                    scenario_df = flow_df[flow_df['Scenario'] == scenario]
                    
                    # If we have time periods, use the latest period
                    if 'PERIODS' in flow_df.columns:
                        latest_period = scenario_df['PERIODS'].max()
                        scenario_df = scenario_df[scenario_df['PERIODS'] == latest_period]
                    
                    # Group by origin and destination for this scenario
                    grouped = scenario_df.groupby([origin_col, dest_col])[value_col].sum().reset_index()
                    grouped['Scenario'] = scenario
                    edges_with_scenario.append(grouped)
                
                # Combine all scenarios
                if edges_with_scenario:
                    edges = pd.concat(edges_with_scenario)
                    edges.columns = ['source', 'target', 'value', 'Scenario']
                    
                    # Filter to keep only edges with positive values
                    edges = edges[edges['value'] > 0]
                else:
                    # If we couldn't process Scenario data, just add a default scenario
                    edges['Scenario'] = 'Default'
                    scenarios = ['Default']
        else:
            # If no Scenario column, create a default scenario
            edges['Scenario'] = 'Default'
            scenarios = ['Default']
        
        # Create a figure with layers
        fig = go.Figure()
        
        # Define a color palette for origin nodes and their edges
        # Using a qualitative colorscale for distinct origins
        origin_nodes = edges['source'].unique()
        num_origins = len(origin_nodes)
        
        # Create a color mapping dictionary for origins
        if num_origins <= 10:
            # Use qualitative color scale for few origins
            colors = px.colors.qualitative.Plotly
        else:
            # Use a sequential color scale for many origins
            colors = px.colors.sequential.Viridis
        
        # Map each origin to a color
        origin_color_map = {origin: colors[i % len(colors)] for i, origin in enumerate(origin_nodes)}
        
        # Calculate min and max values for edge width scaling
        min_value = edges['value'].min()
        max_value = edges['value'].max()
        
        # Edge width range (min width to max width)
        min_width = 2
        max_width = 10
        
        # Create a layer for each scenario
        for scenario in scenarios:
            scenario_edges = edges[edges['Scenario'] == scenario]
            
            # First, add destination nodes with dark blue color
            dest_nodes = set(scenario_edges['target'].unique())
            
            # Filter nodes that are only destinations (not origins)
            only_dest_nodes = [node for node in dest_nodes if node not in origin_nodes]
            
            if only_dest_nodes:
                dest_node_data = nodes[nodes['name'].isin(only_dest_nodes)]
                
                # Create destination node trace (dark blue)
                dest_node_trace = go.Scattermapbox(
                    lat=dest_node_data['latitude'],
                    lon=dest_node_data['longitude'],
                    mode='markers',
                    marker=dict(
                        size=10, 
                        color='darkblue'
                    ),
                    text=dest_node_data['name'],
                    hoverinfo='text',
                    name=f'Destination Nodes - {scenario}',
                    legendgroup=scenario,
                    visible=(scenario == scenarios[0])  # Only first scenario visible by default
                )
                fig.add_trace(dest_node_trace)
            
            # Add origin nodes with color palette
            for origin in origin_nodes:
                if origin in scenario_edges['source'].unique():
                    origin_node_data = nodes[nodes['name'] == origin]
                    
                    if len(origin_node_data) > 0:
                        # Origin node color from the color map
                        origin_color = origin_color_map[origin]
                        
                        # Create origin node trace
                        origin_node_trace = go.Scattermapbox(
                            lat=origin_node_data['latitude'],
                            lon=origin_node_data['longitude'],
                            mode='markers',
                            marker=dict(
                                size=12,
                                color=origin_color
                                # Note: Removed the 'line' property as it's not supported in Scattermapbox
                            ),
                            text=origin_node_data['name'],
                            hoverinfo='text',
                            name=f'Origin: {origin} - {scenario}',
                            legendgroup=scenario,
                            visible=(scenario == scenarios[0])  # Only first scenario visible by default
                        )
                        fig.add_trace(origin_node_trace)
                        
                        # Add edges from this origin
                        origin_edges = scenario_edges[scenario_edges['source'] == origin]
                        
                        for _, edge in origin_edges.iterrows():
                            source_node = nodes[nodes['name'] == edge['source']]
                            target_node = nodes[nodes['name'] == edge['target']]
                            
                            if len(source_node) == 0 or len(target_node) == 0:
                                continue
                                
                            # Skip self-loops for map visualization
                            if edge['source'] == edge['target']:
                                continue
                                
                            # Calculate edge width scaled between min_width and max_width
                            width = min_width
                            if max_value > min_value:  # Avoid division by zero
                                width = min_width + (max_width - min_width) * ((edge['value'] - min_value) / (max_value - min_value))
                            
                            edge_trace = go.Scattermapbox(
                                lat=[source_node.iloc[0]['latitude'], target_node.iloc[0]['latitude']],
                                lon=[source_node.iloc[0]['longitude'], target_node.iloc[0]['longitude']],
                                mode='lines',
                                line=dict(
                                    width=width, 
                                    color=origin_color
                                ),
                                opacity=0.7,
                                hoverinfo='text',
                                hovertext=f"{edge['source']} to {edge['target']}: {edge['value']:.0f}",
                                text=f"{edge['source']} to {edge['target']}: {edge['value']:.0f}",
                                name=f"{edge['source']} to {edge['target']} - {scenario}",
                                legendgroup=scenario,
                                showlegend=False,
                                visible=(scenario == scenarios[0])  # Only first scenario visible by default
                            )
                            fig.add_trace(edge_trace)
        
        # Create a node trace for nodes that are both origin and destination
        both_nodes = [node for node in dest_nodes if node in origin_nodes]
        
        if both_nodes:
            both_node_data = nodes[nodes['name'].isin(both_nodes)]
            
            # Use a different marker size/color for nodes that are both origin and destination
            both_node_trace = go.Scattermapbox(
                lat=both_node_data['latitude'],
                lon=both_node_data['longitude'],
                mode='markers',
                marker=dict(
                    size=14,
                    color='purple'  # Different color for nodes that are both origin and destination
                    # Note: Removed the 'line' property as it's not supported in Scattermapbox
                ),
                text=[f"{node}" for node in both_node_data['name']],
                hoverinfo='text',
                name='Origin & Destination Nodes',
                visible=True  # Always visible regardless of scenario
            )
            fig.add_trace(both_node_trace)
        
        # Set the map layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=4,
                center=dict(
                    lat=nodes['latitude'].mean(),
                    lon=nodes['longitude'].mean()
                )
            ),
            margin=dict(l=0, r=0, t=30, b=0),
            height=700,
            hovermode='closest',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)"
            ),
            title="Transportation Network Visualization"
        )
        
        # Add buttons to toggle between scenarios
        if len(scenarios) > 1:
            buttons = []
            
            # Create a button for each scenario
            for i, scenario in enumerate(scenarios):
                visibility = [True if trace.legendgroup == scenario or trace.name == 'Origin & Destination Nodes' else False 
                            for trace in fig.data]
                
                buttons.append(dict(
                    label=scenario,
                    method="update",
                    args=[{"visible": visibility}]
                ))
            
            # Add a button to show all scenarios
            all_visible = [True] * len(fig.data)
            buttons.append(dict(
                label="All Scenarios",
                method="update",
                args=[{"visible": all_visible}]
            ))
            
            # Add the buttons to the layout
            fig.update_layout(
                updatemenus=[dict(
                    type="buttons",
                    direction="right",
                    active=0,
                    buttons=buttons,
                    x=0.1,
                    y=1.1,
                    xanchor="left",
                    yanchor="top"
                )]
            )
        
        return fig
    
    def create_filtered_map_figure(self, filtered_edges):
        """
        Create a map visualization with filtered edges.
        
        Args:
            filtered_edges (pd.DataFrame): DataFrame with filtered edge data
            
        Returns:
            plotly.graph_objects.Figure: Map figure
        """
        print("DEBUG: Creating filtered map figure")
        if not self.has_lat_lon or 'node_locations' not in self.data:
            print("DEBUG: No lat/lon data available")
            return go.Figure()
        
        nodes = self.data['node_locations']
        edges = filtered_edges
        
        print(f"DEBUG: Number of nodes: {len(nodes)}")
        print(f"DEBUG: Number of filtered edges: {len(edges)}")
        
        if len(edges) == 0:
            # If no edges after filtering, show an empty map with nodes
            fig = go.Figure()
            
            node_trace = go.Scattermapbox(
                lat=nodes['latitude'],
                lon=nodes['longitude'],
                mode='markers',
                marker=dict(size=10, color='blue'),
                text=nodes['name'],
                hoverinfo='text',
                name='Nodes'
            )
            
            fig.add_trace(node_trace)
            
            # Set the map layout
            fig.update_layout(
                mapbox=dict(
                    style="open-street-map",
                    zoom=4,
                    center=dict(
                        lat=nodes['latitude'].mean(),
                        lon=nodes['longitude'].mean()
                    )
                ),
                margin=dict(l=0, r=0, t=30, b=0),
                height=700,
                hovermode='closest',
                title="Transportation Network Visualization (No flows in selected periods)"
            )
            return fig
        
        # Create a figure with layers
        fig = go.Figure()
        
        # Get unique scenarios
        scenarios = edges['Scenario'].unique().tolist()
        
        # Define a color palette for origin nodes and their edges
        origin_nodes = edges['source'].unique()
        num_origins = len(origin_nodes)
        
        # Create a color mapping dictionary for origins
        if num_origins <= 10:
            colors = px.colors.qualitative.Plotly
        else:
            colors = px.colors.sequential.Viridis
        
        # Map each origin to a color
        origin_color_map = {origin: colors[i % len(colors)] for i, origin in enumerate(origin_nodes)}
        
        # Calculate min and max values for edge width scaling
        min_value = edges['value'].min()
        max_value = edges['value'].max()
        
        # Edge width range
        min_width = 2
        max_width = 10
        
        # Create a layer for each scenario
        for scenario in scenarios:
            scenario_edges = edges[edges['Scenario'] == scenario]
            
            # First, add destination nodes with dark blue color
            dest_nodes = set(scenario_edges['target'].unique())
            
            # Filter nodes that are only destinations (not origins)
            only_dest_nodes = [node for node in dest_nodes if node not in origin_nodes]
            
            if only_dest_nodes:
                dest_node_data = nodes[nodes['name'].isin(only_dest_nodes)]
                
                dest_node_trace = go.Scattermapbox(
                    lat=dest_node_data['latitude'],
                    lon=dest_node_data['longitude'],
                    mode='markers',
                    marker=dict(size=10, color='darkblue'),
                    text=dest_node_data['name'],
                    hoverinfo='text',
                    name=f'Destination Nodes - {scenario}',
                    legendgroup=scenario,
                    visible=(scenario == scenarios[0])
                )
                fig.add_trace(dest_node_trace)
            
            # Add origin nodes with color palette
            for origin in origin_nodes:
                if origin in scenario_edges['source'].unique():
                    origin_node_data = nodes[nodes['name'] == origin]
                    
                    if len(origin_node_data) > 0:
                        origin_color = origin_color_map[origin]
                        
                        origin_node_trace = go.Scattermapbox(
                            lat=origin_node_data['latitude'],
                            lon=origin_node_data['longitude'],
                            mode='markers',
                            marker=dict(size=12, color=origin_color),
                            text=origin_node_data['name'],
                            hoverinfo='text',
                            name=f'Origin: {origin} - {scenario}',
                            legendgroup=scenario,
                            visible=(scenario == scenarios[0])
                        )
                        fig.add_trace(origin_node_trace)
                        
                        # Add edges from this origin
                        origin_edges = scenario_edges[scenario_edges['source'] == origin]
                        
                        for _, edge in origin_edges.iterrows():
                            source_node = nodes[nodes['name'] == edge['source']]
                            target_node = nodes[nodes['name'] == edge['target']]
                            
                            if len(source_node) == 0 or len(target_node) == 0:
                                continue
                                
                            if edge['source'] == edge['target']:
                                continue
                                
                            width = min_width
                            if max_value > min_value:
                                width = min_width + (max_width - min_width) * ((edge['value'] - min_value) / (max_value - min_value))
                            
                            edge_trace = go.Scattermapbox(
                                lat=[source_node.iloc[0]['latitude'], target_node.iloc[0]['latitude']],
                                lon=[source_node.iloc[0]['longitude'], target_node.iloc[0]['longitude']],
                                mode='lines',
                                line=dict(width=width, color=origin_color),
                                opacity=0.7,
                                hoverinfo='text',
                                hovertext=f"{edge['source']} to {edge['target']}: {edge['value']:.0f}",
                                text=f"{edge['source']} to {edge['target']}: {edge['value']:.0f}",
                                name=f"{edge['source']} to {edge['target']} - {scenario}",
                                legendgroup=scenario,
                                showlegend=False,
                                visible=(scenario == scenarios[0])
                            )
                            fig.add_trace(edge_trace)
        
        # Create a node trace for nodes that are both origin and destination
        both_nodes = [node for node in dest_nodes if node in origin_nodes]
        
        if both_nodes:
            both_node_data = nodes[nodes['name'].isin(both_nodes)]
            
            both_node_trace = go.Scattermapbox(
                lat=both_node_data['latitude'],
                lon=both_node_data['longitude'],
                mode='markers',
                marker=dict(size=14, color='purple'),
                text=[f"{node}" for node in both_node_data['name']],
                hoverinfo='text',
                name='Origin & Destination Nodes',
                visible=True
            )
            fig.add_trace(both_node_trace)
        
        # Set the map layout
        fig.update_layout(
            mapbox=dict(
                style="open-street-map",
                zoom=4,
                center=dict(
                    lat=nodes['latitude'].mean(),
                    lon=nodes['longitude'].mean()
                )
            ),
            margin=dict(l=0, r=0, t=30, b=0),
            height=700,
            hovermode='closest',
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
                bgcolor="rgba(255, 255, 255, 0.8)"
            ),
            title=f"Transportation Network Visualization (Filtered by Selected Periods)"
        )
        
        # Add buttons to toggle between scenarios
        if len(scenarios) > 1:
            buttons = []
            
            for i, scenario in enumerate(scenarios):
                visibility = [True if trace.legendgroup == scenario or trace.name == 'Origin & Destination Nodes' else False 
                             for trace in fig.data]
                
                buttons.append(dict(
                    label=scenario,
                    method="update",
                    args=[{"visible": visibility}]
                ))
            
            # Add a button to show all scenarios
            all_visible = [True] * len(fig.data)
            buttons.append(dict(
                label="All Scenarios",
                method="update",
                args=[{"visible": all_visible}]
            ))
            
            # Add the buttons to the layout
            fig.update_layout(
                updatemenus=[dict(
                    type="buttons",
                    direction="right",
                    active=0,
                    buttons=buttons,
                    x=0.1,
                    y=1.1,
                    xanchor="left",
                    yanchor="top"
                )]
            )
        
        return fig

    def create_network_figure(self):
        """
        Create a network graph visualization.
        
        Returns:
            plotly.graph_objects.Figure: Network graph figure
        """
        if 'edges' not in self.data:
            return go.Figure()
        
        edges = self.data['edges']
        
        # Create a NetworkX graph
        G = nx.DiGraph()
        
        # Add edges with weights
        for _, edge in edges.iterrows():
            G.add_edge(edge['source'], edge['target'], weight=edge['value'])
        
        # Calculate node positions using a layout algorithm
        pos = nx.spring_layout(G, seed=42)
        
        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"Node: {node}<br>Connections: {G.degree(node)}")
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                size=10,
                color='blue',
                line=dict(width=1, color='black')
            ),
            name='Nodes'
        )
        
        # Create edge traces
        edge_x = []
        edge_y = []
        edge_text = []
        edge_width = []
        
        for source, target, data in G.edges(data=True):
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_text.append(f"{source} to {target}: {data['weight']:.0f}")
            edge_width.append(1 + np.log1p(data['weight']) * 0.5)
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            hoverinfo='text',
            text=edge_text * 3,  # Repeat text for each segment
            line=dict(width=2, color='red'),
            opacity=0.7,
            name='Edges'
        )
        
        # Create the figure
        fig = go.Figure(data=[edge_trace, node_trace])
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            hovermode='closest',
            margin=dict(l=0, r=0, t=0, b=0),
            height=600,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        
        return fig
    
    def create_filtered_network_figure(self, filtered_edges):
        """
        Create a network graph visualization with filtered edges.
        
        Args:
            filtered_edges (pd.DataFrame): DataFrame with filtered edge data
            
        Returns:
            plotly.graph_objects.Figure: Network graph figure
        """
        print("DEBUG: Creating filtered network figure")
        
        edges = filtered_edges
        
        if len(edges) == 0:
            # Return empty figure if no edges after filtering
            return go.Figure()
        
        # Create a NetworkX graph
        G = nx.DiGraph()
        
        # Add edges with weights
        for _, edge in edges.iterrows():
            G.add_edge(edge['source'], edge['target'], weight=edge['value'])
        
        # Calculate node positions using a layout algorithm
        pos = nx.spring_layout(G, seed=42)
        
        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_text.append(f"Node: {node}<br>Connections: {G.degree(node)}")
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                size=10,
                color='blue',
                line=dict(width=1, color='black')
            ),
            name='Nodes'
        )
        
        # Create edge traces
        edge_x = []
        edge_y = []
        edge_text = []
        edge_width = []
        
        for source, target, data in G.edges(data=True):
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
            edge_text.append(f"{source} to {target}: {data['weight']:.0f}")
            edge_width.append(1 + np.log1p(data['weight']) * 0.5)
        
        edge_trace = go.Scatter(
            x=edge_x, y=edge_y,
            mode='lines',
            hoverinfo='text',
            text=edge_text * 3,  # Repeat text for each segment
            line=dict(width=2, color='red'),
            opacity=0.7,
            name='Edges'
        )
        
        # Create the figure
        fig = go.Figure(data=[edge_trace, node_trace])
        
        # Update layout
        fig.update_layout(
            showlegend=True,
            hovermode='closest',
            margin=dict(l=0, r=0, t=30, b=0),
            height=600,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            title=f"Network Graph Visualization (Filtered by Selected Periods)"
        )
        
        return fig
    
    def create_dashboard(self):
        """Create the dashboard layout and callbacks."""
        # Get available result tables
        result_tables = list(self.data['results'].keys())
        
        # Define the app layout
        self.app.layout = dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.H1(self.title, className='text-center my-4')
                ])
            ]),
            
            dbc.Row([
                # Sidebar for navigation
                dbc.Col([
                    html.H4("Navigation"),
                    dbc.Nav(
                        [
                            dbc.NavLink("Network Visualization", href="#", id="nav-network", active=True, 
                                        className="mb-1"),
                            html.Hr(),
                            html.H5("Available Tables:"),
                            html.Div([
                                dbc.NavLink(
                                    table_name[:25] + '...' if len(table_name) > 25 else table_name,
                                    href="#",
                                    id=f"table-{i}",
                                    className="mb-1 text-truncate"
                                ) for i, table_name in enumerate(result_tables)
                            ], style={'maxHeight': '400px', 'overflowY': 'auto'})
                        ],
                        vertical=True,
                        pills=True,
                    ),
                ], width=2, className="bg-light p-3", style={"height": "calc(100vh - 100px)"}),
                
                # Main content area
                dbc.Col([
                    # Content container that will be updated by callbacks
                    html.Div(id="page-content", className="p-3", children=[
                        # Initial view - network visualization with filters
                        html.Div([
                            html.H3("Network Visualization"),
                            # Add filters row with period and scenario filters
                            dbc.Row([
                                # Period filter
                                dbc.Col([
                                    html.Label("Filter by Periods:"),
                                    dcc.Dropdown(
                                        id="period-filter",
                                        options=[{'label': f"Period {p}", 'value': p} for p in self.periods] if hasattr(self, 'periods') else [],
                                        value=self.periods if hasattr(self, 'periods') else [],
                                        multi=True,
                                        placeholder="Select periods to display"
                                    )
                                ], width=6, style={'display': 'block' if hasattr(self, 'has_periods') and self.has_periods else 'none'}),
                                
                                # Scenario filter
                                dbc.Col([
                                    html.Label("Filter by Scenarios:"),
                                    dcc.Dropdown(
                                        id="scenario-filter",
                                        options=[{'label': f"Scenario {s}", 'value': s} for s in self.scenarios] if hasattr(self, 'scenarios') else [],
                                        value=self.scenarios if hasattr(self, 'scenarios') else [],
                                        multi=True,
                                        placeholder="Select scenarios to display"
                                    )
                                ], width=6, style={'display': 'block' if hasattr(self, 'has_scenarios') and self.has_scenarios else 'none'}),
                            ], className="mb-4"),
                            
                            dcc.Graph(
                                id='network-graph',
                                figure=self.create_map_figure() if self.has_lat_lon else self.create_network_figure(),
                                style={'height': 'calc(100vh - 250px)'}
                            )
                        ], id="network-view")
                    ])
                ], width=10)
            ])
        ], fluid=True)
        
        # Add callback to update the graph based on period filter
        @self.app.callback(
            Output("network-graph", "figure"),
            [Input("period-filter", "value"),
            Input("scenario-filter", "value")]
        )
        def update_graph_by_filters(selected_periods, selected_scenarios):
            print(f"DEBUG: Updating graph for periods: {selected_periods}, scenarios: {selected_scenarios}")
            
            # If no filters selected or no filter data, return the default graph
            if ((not selected_periods or not self.has_periods) and 
                (not selected_scenarios or not self.has_scenarios)):
                return self.create_map_figure() if self.has_lat_lon else self.create_network_figure()
            
            # Filter flow data by selected periods and scenarios
            if 'flow_data' in self.data:
                flow_df = self.data['flow_data']
                filtered_flow = flow_df.copy()
                
                # Apply period filter if it exists
                if selected_periods and self.has_periods:
                    filtered_flow = filtered_flow[filtered_flow['PERIODS'].isin(selected_periods)]
                
                # Apply scenario filter if it exists
                if selected_scenarios and self.has_scenarios:
                    filtered_flow = filtered_flow[filtered_flow['Scenario'].isin(selected_scenarios)]
                
                # If no data after filtering, return empty graph
                if len(filtered_flow) == 0:
                    empty_fig = go.Figure()
                    empty_fig.update_layout(
                        title="No data available for the selected filters",
                        height=600
                    )
                    return empty_fig
                
                # Identify origin and destination columns
                origin_cols = [col for col in flow_df.columns 
                            if any(term in col.lower() for term in ['origin', 'departing', 'from'])]
                
                dest_cols = [col for col in flow_df.columns 
                            if any(term in col.lower() for term in ['destination', 'receiving', 'to'])]
                
                if origin_cols and dest_cols:
                    origin_col = origin_cols[0]
                    dest_col = dest_cols[0]
                    
                    # Find value column
                    value_cols = [col for col in flow_df.columns 
                                if any(term in col.lower() for term in ['departed_product_by_mode', 'value', 'volume', 'quantity'])]
                    
                    value_col = value_cols[0] if value_cols else flow_df.columns[-1]
                    
                    # Group by origin, destination, and scenario (if present)
                    group_cols = [origin_col, dest_col]
                    if 'Scenario' in flow_df.columns:
                        group_cols.append('Scenario')
                    
                    # Aggregate by summing the values
                    edges_df = filtered_flow.groupby(group_cols)[value_col].sum().reset_index()
                    
                    # Set up column names correctly for visualization functions
                    if 'Scenario' in edges_df.columns:
                        edges_df.columns = ['source', 'target', 'Scenario', 'value']
                    else:
                        edges_df.columns = ['source', 'target', 'value']
                        edges_df['Scenario'] = 'Default'  # Add default scenario if missing
                    
                    # Filter to keep only edges with positive values
                    edges_df = edges_df[edges_df['value'] > 0]
                    
                    # Store the filtered edges for visualization
                    self.data['filtered_edges'] = edges_df
                    
                    # Create visualization based on filtered data
                    if self.has_lat_lon:
                        return self.create_filtered_map_figure(edges_df)
                    else:
                        return self.create_filtered_network_figure(edges_df)
            
            # Fallback to default visualization
            return self.create_map_figure() if self.has_lat_lon else self.create_network_figure()
        
        # Also update the page content callback to include the scenario filter
        @self.app.callback(
            Output("page-content", "children"),
            [Input("nav-network", "n_clicks")] + 
            [Input(f"table-{i}", "n_clicks") for i in range(len(result_tables))],
            [State("page-content", "children")]
        )
        def update_page_content(*args):
            ctx = dash.callback_context
            if not ctx.triggered:
                return dash.no_update
            
            # Get the ID of the element that triggered the callback
            trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
            
            if trigger_id == "nav-network":
                # Show network visualization with period and scenario filters
                return html.Div([
                    html.H3("Network Visualization"),
                    # Add filters row with period and scenario filters
                    dbc.Row([
                        # Period filter
                        dbc.Col([
                            html.Label("Filter by Periods:"),
                            dcc.Dropdown(
                                id="period-filter",
                                options=[{'label': f"Period {p}", 'value': p} for p in self.periods] if hasattr(self, 'periods') else [],
                                value=self.periods if hasattr(self, 'periods') else [],
                                multi=True,
                                placeholder="Select periods to display"
                            )
                        ], width=6, style={'display': 'block' if hasattr(self, 'has_periods') and self.has_periods else 'none'}),
                        
                        # Scenario filter
                        dbc.Col([
                            html.Label("Filter by Scenarios:"),
                            dcc.Dropdown(
                                id="scenario-filter",
                                options=[{'label': f"Scenario {s}", 'value': s} for s in self.scenarios] if hasattr(self, 'scenarios') else [],
                                value=self.scenarios if hasattr(self, 'scenarios') else [],
                                multi=True,
                                placeholder="Select scenarios to display"
                            )
                        ], width=6, style={'display': 'block' if hasattr(self, 'has_scenarios') and self.has_scenarios else 'none'}),
                    ], className="mb-4"),
                    
                    dcc.Graph(
                        id='network-graph',
                        figure=self.create_map_figure() if self.has_lat_lon else self.create_network_figure(),
                        style={'height': 'calc(100vh - 250px)'}
                    )
                ], id="network-view")
            
            elif trigger_id.startswith("table-"):
                # Show specific table view
                table_idx = int(trigger_id.split("-")[1])
                if table_idx < len(result_tables):
                    table_name = result_tables[table_idx]
                    df = self.data['results'][table_name]
                    
                    # If dataframe is too large, show only first 1000 rows
                    if len(df) > 1000:
                        df = df.head(1000)
                        truncated_message = "Note: Table truncated to 1000 rows"
                    else:
                        truncated_message = ""
                    
                    return html.Div([
                        html.H3(f"Table: {table_name}"),
                        html.P(truncated_message, style={"color": "red"}) if truncated_message else None,
                        
                        # Add controls for the AG Grid
                        html.Div([
                            html.H5("Table Configuration"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Group By:"),
                                    dcc.Dropdown(
                                        id=f"group-by-{table_idx}",
                                        options=[{'label': col, 'value': col} for col in df.columns],
                                        multi=True,
                                        placeholder="Select columns to group by"
                                    )
                                ], width=6),
                                dbc.Col([
                                    html.Label("Aggregate:"),
                                    dcc.Dropdown(
                                        id=f"aggregate-{table_idx}",
                                        options=[{'label': col, 'value': col} for col in df.select_dtypes(include=[np.number]).columns],
                                        multi=True,
                                        placeholder="Select columns to aggregate"
                                    )
                                ], width=6)
                            ]),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Aggregate Function:"),
                                    dcc.Dropdown(
                                        id=f"agg-func-{table_idx}",
                                        options=[
                                            {'label': 'Sum', 'value': 'sum'},
                                            {'label': 'Average', 'value': 'mean'},
                                            {'label': 'Minimum', 'value': 'min'},
                                            {'label': 'Maximum', 'value': 'max'},
                                            {'label': 'Count', 'value': 'count'}
                                        ],
                                        value='sum',
                                        placeholder="Select aggregation function"
                                    )
                                ], width=6),
                                dbc.Col([
                                    dbc.Button("Apply", id=f"apply-agg-{table_idx}", color="primary", className="mt-4")
                                ], width=6)
                            ]),
                            html.Hr()
                        ]),
                        
                        # AG Grid for interactive table
                        html.Div([
                            AgGrid(
                                id=f'grid-{table_idx}',
                                rowData=df.to_dict('records'),
                                columnDefs=[{'field': col} for col in df.columns],
                                defaultColDef={
                                    'resizable': True,
                                    'sortable': True,
                                    'filter': True,
                                    'floatingFilter': True
                                },
                                dashGridOptions={
                                    'pagination': True,
                                    'paginationPageSize': 15,
                                    'enableRangeSelection': True,
                                    'enableCharts': True,
                                    'animateRows': True,
                                },
                                className="ag-theme-alpine",
                                style={'height': '600px'}
                            )
                        ])
                    ], id=f"table-view-{table_idx}")
            
            return dash.no_update
        
        # Define callbacks for aggregation in tables
        for idx, table_name in enumerate(result_tables):
            @self.app.callback(
                Output(f'grid-{idx}', 'rowData'),
                [Input(f'apply-agg-{idx}', 'n_clicks')],
                [State(f'group-by-{idx}', 'value'),
                 State(f'aggregate-{idx}', 'value'),
                 State(f'agg-func-{idx}', 'value')]
            )
            def update_table_aggregation(n_clicks, group_by, aggregate, agg_func, table_idx=idx):
                print(f"DEBUG: Aggregation callback triggered for table {table_idx}")
                print(f"DEBUG: n_clicks={n_clicks}, group_by={group_by}, aggregate={aggregate}, agg_func={agg_func}")
                
                if not n_clicks:
                    # Initial load - return the original dataframe
                    print("DEBUG: Initial load, returning original data")
                    return self.data['results'][result_tables[table_idx]].to_dict('records')
                
                if not group_by or not aggregate or not agg_func:
                    print("DEBUG: Missing parameters for aggregation")
                    return self.data['results'][result_tables[table_idx]].to_dict('records')
                
                # Get the dataframe for the current table
                df = self.data['results'][result_tables[table_idx]]
                print(f"DEBUG: Original dataframe shape: {df.shape}")
                
                # Perform the aggregation
                try:
                    # Convert group_by and aggregate to lists if they're not already
                    if not isinstance(group_by, list):
                        group_by = [group_by]
                    if not isinstance(aggregate, list):
                        aggregate = [aggregate]
                    
                    print(f"DEBUG: Grouping by: {group_by}")
                    print(f"DEBUG: Aggregating: {aggregate}")
                    print(f"DEBUG: Using function: {agg_func}")
                    
                    # Create aggregation dictionary
                    agg_dict = {col: agg_func for col in aggregate}
                    
                    # Group by selected columns and apply the aggregation function
                    grouped = df.groupby(group_by, as_index=False).agg(agg_dict)
                    
                    # If the columns are now MultiIndex, flatten them
                    if isinstance(grouped.columns, pd.MultiIndex):
                        # Rename columns to indicate the aggregation function
                        # Format: column_aggregationFunction
                        grouped.columns = [f"{col[0]}_{col[1]}" if col[1] != '' else col[0] 
                                         for col in grouped.columns]
                    
                    print(f"DEBUG: Aggregated dataframe shape: {grouped.shape}")
                    print(f"DEBUG: Aggregated columns: {grouped.columns.tolist()}")
                    
                    return grouped.to_dict('records')
                except Exception as e:
                    print(f"DEBUG ERROR: Aggregation failed: {e}")
                    # Return the original data on error
                    return df.to_dict('records')
            
            # Make sure each callback uses a unique function by creating a closure
            update_table_aggregation.__name__ = f'update_table_aggregation_{idx}'
        
    def run_server(self, debug=True, port=8050):
        """
        Run the Dash server.
        
        Args:
            debug (bool): Whether to run in debug mode
            port (int): Port to run the server on
        """
        self.app.run(debug=debug, port=port)


def create_viz_from_files(input_file, results_file, title="Optimization Results Dashboard", port=8050):
    """
    Create and run a visualization dashboard from input and results files.
    
    Args:
        input_file (str): Path to the input file (Excel or JSON)
        results_file (str): Path to the results file (Excel or JSON)
        title (str): Title for the dashboard
        port (int): Port to run the server on
    """
    viz = PulpViz(input_file, results_file, title)
    viz.run_server(port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Solver Results Visualization Tool')
    parser.add_argument('--input', required=True, help='Path to the input file (Excel or JSON)')
    parser.add_argument('--results', required=True, help='Path to the results file (Excel or JSON)')
    parser.add_argument('--title', default='Solver Results Dashboard', help='Title for the dashboard')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the server on')
    
    args = parser.parse_args()
    
    create_viz_from_files(args.input, args.results, args.title, args.port)