from typing import Dict, Any, List
import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

class ScenarioComparator:
    """Compares results across different scenarios."""
    
    def __init__(self, scenario_results: Dict[str, Dict[str, pd.DataFrame]]):
        self.scenario_results = scenario_results
        self.logger = logging.getLogger(__name__)

    def compare_scenarios(self) -> Dict[str, pd.DataFrame]:
        """Performs comparative analysis across scenarios."""
        try:
            comparisons = {
                'cost_comparison': self._compare_costs(),
                'service_comparison': self._compare_service_levels(),
                'utilization_comparison': self._compare_utilization(),
                'network_comparison': self._compare_network_structure()
            }
            return comparisons
            
        except Exception as e:
            self.logger.error(f"Error comparing scenarios: {str(e)}")
            raise

    def _compare_costs(self) -> pd.DataFrame:
        """Compares cost metrics across scenarios."""
        cost_comparison = pd.DataFrame()
        
        for scenario, results in self.scenario_results.items():
            analyzer = SolutionAnalyzer(results)
            metrics = analyzer._calculate_key_metrics()
            
            scenario_costs = {
                'Scenario': scenario,
                'Total_Cost': metrics.total_cost,
                'Transport_Cost': metrics.transportation_costs,
                'Operating_Cost': metrics.operating_costs,
                'Cost_Per_Unit': metrics.total_cost / metrics.total_volume
                if metrics.total_volume > 0 else 0
            }
            
            cost_comparison = pd.concat([
                cost_comparison,
                pd.DataFrame([scenario_costs])
            ])
            
        return cost_comparison

    def _compare_service_levels(self) -> pd.DataFrame:
        """Compares service level metrics across scenarios."""
        service_comparison = pd.DataFrame()
        
        for scenario, results in self.scenario_results.items():
            if 'demand_satisfaction' in results:
                service_df = results['demand_satisfaction']
                
                service_metrics = {
                    'Scenario': scenario,
                    'Avg_Service_Level': service_df['Service_Level'].mean(),
                    'Min_Service_Level': service_df['Service_Level'].min(),
                    'Service_Level_StdDev': service_df['Service_Level'].std(),
                    'Periods_Below_Target': len(
                        service_df[service_df['Service_Level'] < 0.95]
                    )
                }
                
                service_comparison = pd.concat([
                    service_comparison,
                    pd.DataFrame([service_metrics])
                ])
                
        return service_comparison

    def generate_summary_report(self) -> str:
        """Generates a textual summary report of scenario comparisons."""
        try:
            cost_comparison = self._compare_costs()
            service_comparison = self._compare_service_levels()
            
            report = []
            report.append("=== Scenario Comparison Summary ===\n")
            
            # Cost summary
            report.append("Cost Comparison:")
            for _, row in cost_comparison.iterrows():
                report.append(f"\nScenario: {row['Scenario']}")
                report.append(f"Total Cost: ${row['Total_Cost']:,.2f}")
                report.append(f"Cost Per Unit: ${row['Cost_Per_Unit']:,.2f}")
            
            # Service level summary
            report.append("\nService Level Comparison:")
            for _, row in service_comparison.iterrows():
                report.append(f"\nScenario: {row['Scenario']}")
                report.append(f"Average Service Level: {row['Avg_Service_Level']:.2%}")
                report.append(f"Periods Below Target: {row['Periods_Below_Target']}")
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating summary report: {str(e)}")
            raise