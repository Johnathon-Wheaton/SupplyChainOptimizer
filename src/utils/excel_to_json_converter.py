import pandas as pd
import json
from pathlib import Path
from typing import Dict, Any
import argparse
import logging
from .logging_utils import NetworkOptimizerLogger

class ExcelToJSONConverter:
    """Converts network optimizer Excel files to JSON format"""
    
    def __init__(self, logger: logging.Logger = None):
        """Initialize converter
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)

    def convert(self, excel_path: str, json_path: str = None) -> None:
        """Convert Excel file to JSON
        
        Args:
            excel_path: Path to input Excel file
            json_path: Optional path for output JSON file. If not provided,
                      will use same name as Excel file with .json extension
        """
        excel_path = Path(excel_path)
        if not excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
            
        if json_path is None:
            json_path = excel_path.with_suffix('.json')
        else:
            json_path = Path(json_path)

        self.logger.info(f"Converting {excel_path} to {json_path}")

        # Read all sheets
        excel_data = {}
        xls = pd.ExcelFile(excel_path)
        
        for sheet_name in xls.sheet_names:
            self.logger.debug(f"Processing sheet: {sheet_name}")
            
            # Handle Parameters sheet differently due to its transposed nature
            if sheet_name == 'Parameters':
                df = pd.read_excel(excel_path, sheet_name=sheet_name, header=None, index_col=None)
                df.columns = ['parameter', 'value']
                df = df[1:]
                excel_data[sheet_name] = {
                    'columns': ['Parameter', 'Value'],
                    'data': df.values.tolist()
                }
            else:
                df = pd.read_excel(excel_path, sheet_name=sheet_name)
                excel_data[sheet_name] = {
                    'columns': df.columns.tolist(),
                    'data': df.values.tolist()
                }

        # Convert numeric values and handle NaN
        self._clean_data(excel_data)

        # Write to JSON
        with open(json_path, 'w') as f:
            json.dump(excel_data, f, indent=2)

        self.logger.info(f"Conversion complete. JSON file saved to: {json_path}")

    def _clean_data(self, data: Dict[str, Any]) -> None:
        """Clean data before JSON conversion
        
        Args:
            data: Dictionary of sheet data to clean
        """
        for sheet_name, sheet_data in data.items():
            cleaned_data = []
            for row in sheet_data['data']:
                cleaned_row = []
                for value in row:
                    # Handle NaN and None
                    if pd.isna(value):
                        cleaned_row.append(None)
                    # Handle numpy numeric types
                    elif pd.api.types.is_number(value):
                        cleaned_row.append(float(value) if pd.api.types.is_float(value) else int(value))
                    # Convert numpy strings to python strings
                    elif isinstance(value, (pd.Timestamp, pd.Timedelta)):
                        cleaned_row.append(str(value))
                    else:
                        cleaned_row.append(value)
                cleaned_data.append(cleaned_row)
            data[sheet_name]['data'] = cleaned_data

def main():
    """Command line interface for converter"""
    parser = argparse.ArgumentParser(description='Convert network optimizer Excel file to JSON')
    parser.add_argument('excel_file', help='Path to input Excel file')
    parser.add_argument('--output', '-o', help='Path to output JSON file (optional)')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='Set the logging level')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=args.log_level)
    logger = logging.getLogger('excel_to_json_converter')
    
    # Run conversion
    try:
        converter = ExcelToJSONConverter(logger)
        converter.convert(args.excel_file, args.output)
    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}")
        raise

if __name__ == '__main__':
    main()