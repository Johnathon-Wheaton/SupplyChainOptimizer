# Supply Chain Optimizer

This supply chain optimizer is a mixed integer linear program generalized to handle a broad range of network flow use cases. It is purpose-built for practitioners of operations research, allowing users to easily configure the network, constraints, parameters, scenarios, and objectives using an excel input file. For developers, json inputs are also accepted to allow the model to interface with other programs.

## 🚀 Features

- **Mutli-Scenario**: Configure and run multiple scenarios for easy side-by-side comparison of strategies
- **Multi-Objective Goal Programming**: Configure multiple objectives to be solved for concurrently
- **Multi-Stage Objectives**: Configure multiple objectives to be solved sequentially
- **Multi-Modal**: Configure different transportation modes and types of resources, each with their own constraints and parameters
- **Multi-Echelon**: Configure origin, destination, and intermediate nodes to create multiple echelon networks
- **Heirarchical capacity and demand**: Configure capacity and demand hierarchies to apply constraints to (e.g. solve for volume of small and large packages with constraints on total package count)
- **Soft constraints**: Allow constraints to be violated with a high penalty to more easily identify sources of infeasibility
- **Temporal constraints**: Configure and solve for period-over-period costs and constraints (e.g. minimize network changes over time)

## 🔧 Installation

Follow these steps to get your development environment set up:

```bash
# Clone the repository
git clone https://github.com/Johnathon-Wheaton/SupplyChainOptimizer.git

# Change into the project directory
cd SupplyChainOptimizer

# Install dependencies
pip install -r requirements.txt
```

## 💻 Usage

Here's how to use this project after installation:

```bash
python src/main.py src/examples/demo_inputs_transportation_facility_location.json -o src/examples/demo_inputs_transportation_facility_location_results.xlsx
```

## 🌟 Examples

Examples by use-case are coming soon!

## 📖 Documentation

Full documentation coming soon!

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
