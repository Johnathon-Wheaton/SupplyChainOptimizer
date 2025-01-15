from typing import Dict, Any
import pulp
import logging
from datetime import datetime

class SupplyChainOptimizer:
    """Main class coordinating the optimization process."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self):
        """Configures logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

    def optimize(self, input_file: str, output_file: str = None) -> Dict[str, Any]:
        """
        Runs the complete optimization process.
        
        Args:
            input_file: Path to input Excel file
            output_file: Optional path for output Excel file
            
        Returns:
            Dictionary containing optimization results
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"Starting optimization process for {input_file}")

            # Load and preprocess data
            data_loader = DataLoader(input_file)
            input_data = data_loader.load_input_data()
            processed_data = data_loader.preprocess_data(input_data)

            # Build and solve model
            model_builder = ModelBuilder(processed_data)
            model_output = model_builder.build_model()
            
            # Process solution
            processor = SolutionProcessor()
            results = processor.process_results(model_output)
            
            if output_file:
                processor.export_results(results, output_file)

            total_time = (datetime.now() - start_time).seconds
            self.logger.info(f"Optimization completed in {total_time} seconds")
            
            return results

        except Exception as e:
            self.logger.error(f"Optimization failed: {str(e)}")
            raise
