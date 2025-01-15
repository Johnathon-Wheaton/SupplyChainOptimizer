from typing import Dict, Any, List
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

@dataclass
class AnalysisMetrics:
    """Container for solution analysis metrics."""
    total_cost: float
    transportation_costs: float
    operating_costs: float
    capacity_utilization: float
    service_level: float
    avg_transit_time: float
    total_volume: float

class SolutionAnalyzer:
    """Analyzes optimization results and generates insights."""
    
    def __init__(self, results: Dict[str, pd.DataFrame], sets: Dict[str, List],
                 parameters: Dict[str, Any]):
        self.results = results
        self.sets = sets
        self.parameters = parameters
        self.logger = logging.getLogger(__name__)

    def analyze_solution(self) -> Dict[str, Any]:
        """Performs comprehensive solution analysis."""
        try:
            metrics = self._calculate_key_metrics()
            insights = {
                'metrics': metrics,
                'utilization': self._analyze_utilization(),
                'bottlenecks': self._identify_bottlenecks(),
                'cost_breakdown': self._analyze_costs(),
                'service_analysis': self._analyze_service_levels(),
                'network_stats': self._analyze_network_structure()
            }
            return insights
            
        except Exception as e:
            self.logger.error(f"Error analyzing solution: {str(e)}")
            raise

    def _calculate_key_metrics(self) -> AnalysisMetrics:
        """Calculates key performance metrics."""
        try:
            departed_df = self.results.get('departed_product', pd.DataFrame())
            transport_cost_df = self.results.get('transport_cost', pd.DataFrame())
            operating_cost_df = self.results.get('operating_cost', pd.DataFrame())
            
            total_volume = departed_df['Value'].sum() if not departed_df.empty else 0
            total_transport_cost = transport_cost_df['Value'].sum() if not transport_cost_df.empty else 0
            total_operating_cost = operating_cost_df['Value'].sum() if not operating_cost_df.empty else 0
            
            return AnalysisMetrics(
                total_cost=total_transport_cost + total_operating_cost,
                transportation_costs=total_transport_cost,
                operating_costs=total_operating_cost,
                capacity_utilization=self._calculate_utilization(),
                service_level=self._calculate_service_level(),
                avg_transit_time=self._calculate_avg_transit_time(),
                total_volume=total_volume
            )
            
        except Exception as e:
            self.logger.error(f"Error calculating metrics: {str(e)}")
            raise

    def _analyze_utilization(self) -> pd.DataFrame:
        """Analyzes capacity utilization across nodes and time periods."""
        try:
            util_df = pd.DataFrame()
            
            if 'processed_product' in self.results and 'capacity' in self.results:
                proc_df = self.results['processed_product']
                cap_df = self.results['capacity']
                
                # Calculate utilization by node and period
                util_df = proc_df.merge(cap_df, on=['Node', 'Period'])
                util_df['Utilization'] = util_df['Value_x'] / util_df['Value_y']
                
                # Add summary statistics
                util_df = util_df.groupby(['Node', 'Period'])['Utilization'].agg([
                    'mean', 'min', 'max', 'std'
                ]).reset_index()
                
            return util_df
            
        except Exception as e:
            self.logger.error(f"Error analyzing utilization: {str(e)}")
            raise

    def _identify_bottlenecks(self) -> Dict[str, List[str]]:
        """Identifies system bottlenecks."""
        try:
            bottlenecks = {
                'capacity_constraints': [],
                'transportation_constraints': [],
                'service_constraints': []
            }
            
            # Check capacity bottlenecks
            util_df = self._analyze_utilization()
            if not util_df.empty:
                high_util = util_df[util_df['mean'] > 0.9]
                bottlenecks['capacity_constraints'].extend(
                    high_util['Node'].unique().tolist()
                )
            
            # Check transportation bottlenecks
            if 'route_active' in self.results:
                route_df = self.results['route_active']
                saturated_routes = route_df[route_df['Value'] > 0.9]
                bottlenecks['transportation_constraints'].extend([
                    f"{row['Origin']}-{row['Destination']}"
                    for _, row in saturated_routes.iterrows()
                ])
            
            return bottlenecks
            
        except Exception as e:
            self.logger.error(f"Error identifying bottlenecks: {str(e)}")
            raise

    def _analyze_costs(self) -> pd.DataFrame:
        """Provides detailed cost breakdown analysis."""
        try:
            cost_components = {
                'Transportation': self.results.get('transport_cost', pd.DataFrame()),
                'Operating': self.results.get('operating_cost', pd.DataFrame()),
                'Inventory': self.results.get('inventory_cost', pd.DataFrame()),
                'Capacity': self.results.get('expansion_cost', pd.DataFrame())
            }
            
            cost_analysis = pd.DataFrame()
            
            for cost_type, df in cost_components.items():
                if not df.empty:
                    total_cost = df['Value'].sum()
                    cost_by_period = df.groupby('Period')['Value'].sum()
                    
                    analysis_row = {
                        'Cost_Type': cost_type,
                        'Total_Cost': total_cost,
                        'Avg_Cost_Per_Period': cost_by_period.mean(),
                        'Cost_Std_Dev': cost_by_period.std(),
                        'Min_Period_Cost': cost_by_period.min(),
                        'Max_Period_Cost': cost_by_period.max()
                    }
                    
                    cost_analysis = pd.concat([
                        cost_analysis,
                        pd.DataFrame([analysis_row])
                    ])
                    
            return cost_analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing costs: {str(e)}")
            raise