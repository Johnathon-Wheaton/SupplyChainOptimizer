# Supply Chain Optimizer

This supply chain optimizer is a mixed integer linear program generalized to handle a broad range of network flow use cases. It is purpose-built for practitioners of operations research, allowing users to easily configure the network, constraints, parameters, scenarios, and objectives using an excel input file. For developers, json inputs are also accepted to allow the model to interface with other programs.

## 🚀 Features

- **Mutli-Scenario**
- **Multi-Objective Goal Programming**
- **Multi-Stage Objectives**
- **Multi-Modal**
- **Multi-Echelon**
- **Heirarchical capacity and demand**
- **Soft constraints**
- **Temporal constraints**

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
python src/main.py src/examples/demo_inputs_transportation_facility_location.json -o src/examples/demo_inputs_transportation_facility_location_results.xlsx'
```

## 🌟 Examples

Examples by use-case are coming soon!

## 📖 Documentation

[Click here](docs/Input_Instructions.md) to read the input file documentation.

## 📝 License

This project is licensed under the MIT License.
