from pathlib import Path
from typing import Union
from .base_reader import BaseReader
from .excel_reader import ExcelReader
from .json_reader import JSONReader

def create_reader(file_path: Union[str, Path]) -> BaseReader:
    """Create appropriate reader based on file extension
    
    Args:
        file_path: Path to input file
        
    Returns:
        Appropriate reader instance
        
    Raises:
        ValueError: If file type is not supported
    """
    file_path = Path(file_path)
    extension = file_path.suffix.lower()
    
    if extension in ['.xlsx', '.xls']:
        return ExcelReader(file_path)
    elif extension == '.json':
        return JSONReader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")