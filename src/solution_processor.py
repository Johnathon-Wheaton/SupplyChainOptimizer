import pandas as pd
from typing import Dict, Any
import logging

class SolutionProcessor:
    """Handles processing and export of optimization results."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def process_results(self, model_output: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """
        Processes optimization results into DataFrames.
        
        Args:
            model_output: Dictionary containing optimization results
            
        Returns:
            Dictionary of processed DataFrames
        """
        try:
            results = {}
            
            # Process each variable type
            for var_name, variable in model_output['variables'].items():
                if len(model_output['dimensions'][var_name]) > 0:
                    results[var_name] = self._variable_to_dataframe(
                        variable,
                        model_output['dimensions'][var_name],
                        model_output['sets']
                    )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing results: {str(e)}")
            raise

    def _variable_to_dataframe(self, variable: Dict, dimensions: List[str], 
                             sets: Dict[str, List]) -> pd.DataFrame:
        """Converts optimization variable to DataFrame."""
        try:
            # Convert variable values to DataFrame
            data = []
            for indices, var in variable.items():
                if isinstance(indices, tuple):
                    row = list(indices) + [var.value()]
                else:
                    row = [indices, var.value()]
                data.append(row)
                
            columns = dimensions + [var_name]
            df = pd.DataFrame(data, columns=columns)
            
            # Filter out zero values
            df = df[df[var_name] != 0]
            
            return df
            
        except Exception as e:
            self.logger.error(f"Error converting variable to DataFrame: {str(e)}")
            raise

    def export_results(self, results: Dict[str, pd.DataFrame], 
                      output_file: str):
        """Exports results to Excel file."""
        try:
            with pd.ExcelWriter(output_file) as writer:
                for sheet_name, df in results.items():
                    if len(sheet_name) > 31:
                        # Excel has 31 character limit for sheet names
                        sheet_name = f"{sheet_name[:26]}_{hash(sheet_name)%1000}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    
        except Exception as e:
            self.logger.error(f"Error exporting results: {str(e)}")
            raise