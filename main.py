# main.py

import logging
from pathlib import Path
from datetime import datetime
import argparse

# Import core components
from src.data_loader import DataLoader
from src.optimizer import SupplyChainOptimizer
from src.model_builder import ModelBuilder
from src.solution_processor import SolutionProcessor

# Import analysis components
from src.analysis.solution_analyzer import SolutionAnalyzer
from src.analysis.result_visualizer import ResultVisualizer
from src.analysis.scenario_comparator import ScenarioComparator

# Import validation components
from src.validation.data_validator import DataValidator
from src.validation.consistency_checker import ConsistencyChecker

# Import reporting components
from src.reporting.report_generator import ReportGenerator

def setup_logging(log_file: str = 'optimization.log'):
    """Sets up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def run_optimization(input_file: str, output_dir: str = 'results', scenario: str = None):
    """
    Runs the complete optimization process.
    
    Args:
        input_file: Path to input Excel file
        output_dir: Directory for output files
        scenario: Optional specific scenario to run
    """
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting optimization process with input file: {input_file}")
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Load and validate data
        logger.info("Loading input data...")
        data_loader = DataLoader(input_file)
        input_data = data_loader.load_input_data()
        
        # Validate input data
        logger.info("Validating input data...")
        validator = DataValidator()
        is_valid, validation_errors = validator.validate_input_data(input_data)
        
        if not is_valid:
            for error in validation_errors:
                logger.error(f"Validation error: {error}")
            raise ValueError("Input data validation failed")

        # Process scenarios
        scenario_handler = ScenarioHandler(input_data)
        scenarios = [scenario] if scenario else scenario_handler.get_all_scenarios()
        
        all_results = {}
        for current_scenario in scenarios:
            logger.info(f"Processing scenario: {current_scenario}")
            
            # Prepare scenario data
            scenario_data = scenario_handler.prepare_scenario_data(current_scenario)
            
            # Build and optimize model
            optimizer = SupplyChainOptimizer()
            model_builder = ModelBuilder(scenario_data)
            model = model_builder.build_model()
            solution = optimizer.solve_model(model)
            
            # Process solution
            processor = SolutionProcessor()
            processed_results = processor.process_results(solution)
            
            # Store results
            all_results[current_scenario] = processed_results
        
        # Analyze results
        logger.info("Analyzing solutions...")
        analyzer = SolutionAnalyzer(all_results)
        analysis_results = analyzer.analyze_solutions()
        
        # Compare scenarios if multiple
        if len(scenarios) > 1:
            comparator = ScenarioComparator(all_results)
            comparison_results = comparator.compare_scenarios()
            
        # Generate visualizations
        visualizer = ResultVisualizer(all_results)
        visualization_data = visualizer.create_visualizations()
        
        # Generate reports
        logger.info("Generating reports...")
        report_gen = ReportGenerator(all_results, analysis_results)
        
        # Save reports
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_file = Path(output_dir) / f"optimization_results_{timestamp}.xlsx"
        report_gen.export_report(report_gen.generate_detailed_report(), excel_file)
        
        summary_file = Path(output_dir) / f"summary_report_{timestamp}.txt"
        report_gen.export_summary_report(summary_file)
        
        # Check solution consistency
        checker = ConsistencyChecker(all_results, input_data)
        is_consistent, consistency_issues = checker.check_solution_consistency()
        
        if not is_consistent:
            logger.warning("Solution consistency check found issues:")
            for issue in consistency_issues:
                logger.warning(f"- {issue}")
        
        total_time = (datetime.now() - start_time).seconds
        logger.info(f"Optimization completed in {total_time} seconds")
        logger.info(f"Results saved to {output_dir}")
        
        return {
            'status': 'success',
            'results': all_results,
            'analysis': analysis_results,
            'comparison': comparison_results if len(scenarios) > 1 else None,
            'excel_report': str(excel_file),
            'summary_report': str(summary_file)
        }
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise

if __name__ == "__main__":
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Supply Chain Optimization')
    parser.add_argument('input_file', help='Path to input Excel file')
    parser.add_argument('--output_dir', default='results', help='Directory for output files')
    parser.add_argument('--scenario', help='Specific scenario to run (optional)')
    parser.add_argument('--log_file', default='optimization.log', help='Log file path')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_file)
    
    # Run optimization
    try:
        results = run_optimization(
            args.input_file, 
            args.output_dir,
            args.scenario
        )
        print("\nOptimization completed successfully!")
        print(f"Results saved to {args.output_dir}")
        
    except Exception as e:
        print(f"\nOptimization failed: {str(e)}")