from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from dataclasses import dataclass
import logging

@dataclass
class ValidationRule:
    """Defines a validation rule for input data."""
    column: str
    rule_type: str  # one of: 'non_negative', 'positive', 'range', 'unique', 'required'
    min_value: float = None
    max_value: float = None
    allowed_values: List[Any] = None
    error_message: str = None

class DataValidator:
    """Validates input data for optimization model."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._setup_validation_rules()

    def _setup_validation_rules(self) -> Dict[str, List[ValidationRule]]:
        """Sets up validation rules for each input table."""
        return {
            'demand_input': [
                ValidationRule('Demand', 'non_negative', error_message='Demand must be non-negative'),
                ValidationRule('Period', 'required', error_message='Period is required'),
                ValidationRule('Product', 'required', error_message='Product is required')
            ],
            'capacity_input': [
                ValidationRule('Capacity', 'positive', error_message='Capacity must be positive'),
                ValidationRule('Node', 'required', error_message='Node is required')
            ],
            'cost_input': [
                ValidationRule('Cost', 'non_negative', error_message='Cost must be non-negative'),
                ValidationRule('Origin', 'required', error_message='Origin is required'),
                ValidationRule('Destination', 'required', error_message='Destination is required')
            ]
        }

    def validate_input_data(self, input_data: Dict[str, pd.DataFrame]) -> Tuple[bool, List[str]]:
        """
        Validates all input data against defined rules.
        
        Args:
            input_data: Dictionary of input DataFrames
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            errors = []
            
            # Validate data structure
            structure_errors = self._validate_data_structure(input_data)
            errors.extend(structure_errors)
            
            # Validate data content
            content_errors = self._validate_data_content(input_data)
            errors.extend(content_errors)
            
            # Validate relationships
            relationship_errors = self._validate_relationships(input_data)
            errors.extend(relationship_errors)
            
            return len(errors) == 0, errors
            
        except Exception as e:
            self.logger.error(f"Error during data validation: {str(e)}")
            raise

    def _validate_data_structure(self, input_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Validates basic data structure."""
        errors = []
        
        required_tables = [
            'demand_input', 'capacity_input', 'cost_input', 
            'nodes_input', 'products_input', 'periods_input'
        ]
        
        # Check for required tables
        for table in required_tables:
            if table not in input_data:
                errors.append(f"Missing required table: {table}")
                continue
                
            df = input_data[table]
            if df.empty:
                errors.append(f"Table {table} is empty")
                continue
                
            # Check for required columns based on validation rules
            if table in self.validation_rules:
                required_columns = [
                    rule.column for rule in self.validation_rules[table]
                    if rule.rule_type == 'required'
                ]
                
                for column in required_columns:
                    if column not in df.columns:
                        errors.append(f"Missing required column {column} in table {table}")
        
        return errors

    def _validate_data_content(self, input_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Validates data content against rules."""
        errors = []
        
        for table_name, df in input_data.items():
            if table_name not in self.validation_rules:
                continue
                
            rules = self.validation_rules[table_name]
            
            for rule in rules:
                if rule.column not in df.columns:
                    continue
                    
                column_data = df[rule.column]
                
                if rule.rule_type == 'non_negative':
                    invalid_rows = df[column_data < 0].index
                    if len(invalid_rows) > 0:
                        errors.append(
                            f"{rule.error_message} - Found {len(invalid_rows)} violations"
                        )
                
                elif rule.rule_type == 'positive':
                    invalid_rows = df[column_data <= 0].index
                    if len(invalid_rows) > 0:
                        errors.append(
                            f"{rule.error_message} - Found {len(invalid_rows)} violations"
                        )
                
                elif rule.rule_type == 'range':
                    invalid_rows = df[
                        (column_data < rule.min_value) | 
                        (column_data > rule.max_value)
                    ].index
                    if len(invalid_rows) > 0:
                        errors.append(
                            f"{rule.error_message} - Found {len(invalid_rows)} violations"
                        )
        
        return errors

    def _validate_relationships(self, input_data: Dict[str, pd.DataFrame]) -> List[str]:
        """Validates relationships between different tables."""
        errors = []
        
        try:
            # Validate node references
            if 'nodes_input' in input_data and 'capacity_input' in input_data:
                valid_nodes = set(input_data['nodes_input']['Name'])
                capacity_nodes = set(input_data['capacity_input']['Node'])
                
                invalid_nodes = capacity_nodes - valid_nodes
                if invalid_nodes:
                    errors.append(
                        f"Invalid node references in capacity_input: {invalid_nodes}"
                    )
            
            # Validate product references
            if 'products_input' in input_data and 'demand_input' in input_data:
                valid_products = set(input_data['products_input']['Product'])
                demand_products = set(input_data['demand_input']['Product'])
                
                invalid_products = demand_products - valid_products
                if invalid_products:
                    errors.append(
                        f"Invalid product references in demand_input: {invalid_products}"
                    )
            
            # Validate period references
            if 'periods_input' in input_data:
                valid_periods = set(input_data['periods_input']['Period'].astype(str))
                
                for table_name, df in input_data.items():
                    if 'Period' in df.columns:
                        periods_in_table = set(df['Period'].astype(str))
                        invalid_periods = periods_in_table - valid_periods
                        if invalid_periods:
                            errors.append(
                                f"Invalid period references in {table_name}: {invalid_periods}"
                            )
        
        except Exception as e:
            errors.append(f"Error validating relationships: {str(e)}")
            
        return errors
