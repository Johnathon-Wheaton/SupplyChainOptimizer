from typing import Dict, Any
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging
import json

@dataclass
class ReportSection:
    """Defines a section of the report."""
    title: str
    content: Any
    visualization_type: str = None
    description: str = None

class ReportGenerator:
    """Generates comprehensive reports from optimization results."""
    
    def __init__(self, results: Dict[str, Any], analysis_results: Dict[str, Any]):
        self.results = results
        self.analysis_results = analysis_results
        self.logger = logging.getLogger(__name__)

    def generate_executive_summary(self) -> Dict[str, Any]:
        """Generates executive summary report."""
        try:
            metrics = self.analysis_results['metrics']
            
            summary = {
                'title': 'Supply Chain Optimization Executive Summary',
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sections': [
                    ReportSection(
                        title='Key Performance Metrics',
                        content={
                            'Total Cost': f"${metrics.total_cost:,.2f}",
                            'Transportation Cost': f"${metrics.transportation_costs:,.2f}",
                            'Operating Cost': f"${metrics.operating_costs:,.2f}",
                            'Service Level': f"{metrics.service_level:.1%}",
                            'Capacity Utilization': f"{metrics.capacity_utilization:.1%}"
                        },
                        visualization_type='metrics_dashboard'
                    ),
                    ReportSection(
                        title='Network Utilization',
                        content=self.analysis_results['utilization'],
                        visualization_type='heatmap',
                        description='Capacity utilization across network nodes'
                    ),
                    ReportSection(
                        title='Cost Breakdown',
                        content=self.analysis_results['cost_breakdown'],
                        visualization_type='pie_chart',
                        description='Distribution of total cost by category'
                    ),
                    ReportSection(
                        title='Service Performance',
                        content=self.analysis_results['service_analysis'],
                        visualization_type='line_chart',
                        description='Service level trends over time'
                    )
                ]
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating executive summary: {str(e)}")
            raise

    def generate_detailed_report(self) -> Dict[str, Any]:
        """Generates detailed technical report."""
        try:
            report = {
                'title': 'Supply Chain Optimization Detailed Report',
                'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sections': [
                    # Network Flow Analysis
                    ReportSection(
                        title='Network Flow Analysis',
                        content=self._analyze_network_flows(),
                        visualization_type='sankey_diagram',
                        description='Detailed analysis of product flows'
                    ),
                    
                    # Capacity Analysis
                    ReportSection(
                        title='Capacity Analysis',
                        content=self._analyze_capacity(),
                        visualization_type='bar_chart',
                        description='Detailed capacity utilization analysis'
                    ),
                    
                    # Cost Analysis
                    ReportSection(
                        title='Cost Analysis',
                        content=self._analyze_costs(),
                        visualization_type='stacked_bar',
                        description='Detailed cost breakdown analysis'
                    ),
                    
                    # Service Level Analysis
                    ReportSection(
                        title='Service Level Analysis',
                        content=self._analyze_service(),
                        visualization_type='line_chart',
                        description='Detailed service level analysis'
                    ),
                    
                    # Bottleneck Analysis
                    ReportSection(
                        title='Bottleneck Analysis',
                        content=self.analysis_results['bottlenecks'],
                        visualization_type='network_diagram',
                        description='Analysis of system bottlenecks'
                    )
                ]
            }
            
            return report
            
        except Exception as e:
            self.logger.error(f"Error generating detailed report: {str(e)}")
            raise

    def _analyze_network_flows(self) -> Dict[str, Any]:
        """Analyzes network flows in detail."""
        try:
            flow_df = self.results.get('departed_product', pd.DataFrame())
            
            if flow_df.empty:
                return {}
                
            analysis = {
                'total_flow': flow_df['Value'].sum(),
                'flows_by_product': flow_df.groupby('Product')['Value'].sum().to_dict(),
                'flows_by_origin': flow_df.groupby('Origin')['Value'].sum().to_dict(),
                'flows_by_destination': flow_df.groupby('Destination')['Value'].sum().to_dict(),
                'peak_period': flow_df.groupby('Period')['Value'].sum().idxmax(),
                'top_routes': (
                    flow_df.groupby(['Origin', 'Destination'])['Value']
                    .sum()
                    .nlargest(10)
                    .to_dict()
                )
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing network flows: {str(e)}")
            raise

    def _analyze_capacity(self) -> Dict[str, Any]:
        """Analyzes capacity utilization in detail."""
        try:
            util_df = self.analysis_results['utilization']
            
            if util_df.empty:
                return {}
                
            analysis = {
                'average_utilization': util_df['mean'].mean(),
                'peak_utilization': util_df['max'].max(),
                'utilization_by_node': util_df.groupby('Node')['mean'].mean().to_dict(),
                'peak_periods': (
                    util_df[util_df['max'] > 0.9]
                    .groupby('Node')['Period']
                    .agg(list)
                    .to_dict()
                ),
                'underutilized_nodes': (
                    util_df[util_df['mean'] < 0.5]['Node']
                    .unique()
                    .tolist()
                )
            }
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing capacity: {str(e)}")
            raise

    def export_report(self, report: Dict[str, Any], format: str = 'excel') -> None:
        """Exports report in specified format."""
        try:
            if format == 'excel':
                self._export_to_excel(report)
            elif format == 'json':
                self._export_to_json(report)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting report: {str(e)}")
            raise

    def _export_to_excel(self, report: Dict[str, Any]) -> None:
        """Exports report to Excel format."""
        try:
            with pd.ExcelWriter('optimization_report.xlsx') as writer:
                # Write summary sheet
                summary_data = {
                    'Metric': [],
                    'Value': []
                }
                
                for section in report['sections']:
                    if isinstance(section.content, dict):
                        for metric, value in section.content.items():
                            summary_data['Metric'].append(metric)
                            summary_data['Value'].append(value)
                
                pd.DataFrame(summary_data).to_excel(
                    writer, 
                    sheet_name='Summary',
                    index=False
                )
                
                # Write detailed sheets
                for section in report['sections']:
                    if isinstance(section.content, pd.DataFrame):
                        sheet_name = section.title[:31]  # Excel sheet name length limit
                        section.content.to_excel(
                            writer,
                            sheet_name=sheet_name,
                            index=False
                        )
                        
        except Exception as e:
            self.logger.error(f"Error exporting to Excel: {str(e)}")
            raise

    def _export_to_json(self, report: Dict[str, Any]) -> None:
        """Exports report to JSON format."""
        try:
            # Convert any DataFrame content to dictionaries
            serializable_report = self._make_json_serializable(report)
            
            with open('optimization_report.json', 'w') as f:
                json.dump(serializable_report, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {str(e)}")
            raise

    def _make_json_serializable(self, obj: Any) -> Any:
        """Converts report objects to JSON serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(v) for v in obj]
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        elif isinstance(obj, ReportSection):
            return {
                'title': obj.title,
                'content': self._make_json_serializable(obj.content),
                'visualization_type': obj.visualization_type,
                'description': obj.description
            }
        else:
            return obj
