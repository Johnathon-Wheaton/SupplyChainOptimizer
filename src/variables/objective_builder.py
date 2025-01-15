class ObjectiveBuilder:
    """Handles construction of the objective function."""
    
    def __init__(self, model: pulp.LpProblem, vars: Dict[str, Any], 
                 params: Dict[str, Any]):
        self.model = model
        self.vars = vars
        self.params = params
        self.logger = logging.getLogger(__name__)

    def build_objective(self):
        """Builds the complete objective function."""
        try:
            objective_terms = []
            
            # Transportation costs
            objective_terms.append(self._get_transportation_costs())
            
            # Operating costs
            objective_terms.append(self._get_operating_costs())
            
            # Inventory costs
            objective_terms.append(self._get_inventory_costs())
            
            # Capacity expansion costs
            objective_terms.append(self._get_expansion_costs())
            
            # Set objective
            self.model += pulp.lpSum(objective_terms), "Total_Cost"
            
        except Exception as e:
            self.logger.error(f"Error building objective: {str(e)}")
            raise

    def _get_transportation_costs(self) -> pulp.LpExpression:
        """Calculates transportation cost component."""
        return pulp.lpSum(
            self.vars['transport_cost'][n_d, n_r, m, t]
            for n_d, n_r, m, t in product(
                self.sets['DEPARTING_NODES'],
                self.sets['RECEIVING_NODES'],
                self.sets['MODES'],
                self.sets['PERIODS']
            )
        )

    def _get_operating_costs(self) -> pulp.LpExpression:
        """Calculates operating cost component."""
        return pulp.lpSum(
            self.vars['operating_cost'][n, t]
            for n, t in product(
                self.sets['NODES'],
                self.sets['PERIODS']
            )
        )

    def _get_inventory_costs(self) -> pulp.LpExpression:
        """Calculates inventory cost component."""
        return pulp.lpSum(
            self.vars['inventory_cost'][n, p, t]
            for n, p, t in product(
                self.sets['NODES'],
                self.sets['PRODUCTS'],
                self.sets['PERIODS']
            )
        )

    def _get_expansion_costs(self) -> pulp.LpExpression:
        """Calculates capacity expansion cost component."""
        return pulp.lpSum(
            self.vars['capacity_expansion'][n, e, t] *
            self.params['expansion_cost'][e]
            for n, e, t in product(
                self.sets['NODES'],
                self.sets['CAPACITY_EXPANSIONS'],
                self.sets['PERIODS']
            )
        )