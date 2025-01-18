from typing import Dict
import pandas as pd
from .base_writer import BaseWriter

class ExcelWriter(BaseWriter):
    """Excel file writer implementation"""
    
    def write(self, results: Dict[str, pd.DataFrame]) -> None:
        """Write results to Excel file
        
        Args:
            results: Dictionary of pandas DataFrames containing optimization results
        """
        with pd.ExcelWriter(self.output_path, engine='xlsxwriter') as writer:
            # Iterate through the dictionary and write each DataFrame to a separate sheet
            count = 1
            for sheet_name, df in results.items():
                if len(sheet_name) > 31:
                    sheet_name = sheet_name[0:26] + " (" + str(count) + ")"
                    count += 1
                df.to_excel(writer, sheet_name=sheet_name, index=False)