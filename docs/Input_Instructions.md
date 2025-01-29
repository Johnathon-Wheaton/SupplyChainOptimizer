# Network Optimizer Input Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Special Notation](#special-notation)
3. [Required Sheets](#required-sheets)
4. [Sheet Details](#sheet-details)
5. [Data Types and Validation](#data-types-and-validation)
6. [Examples](#examples)

## Introduction

This document describes the input data structure for the Network Optimizer. The optimizer accepts inputs in either Excel (.xlsx) or JSON format. Each section below details the required fields and their purposes.

## Special Notation

### Wildcards
The system supports two special wildcard characters for input data:
- `*`: Represents "all" or "any" in a given field. For example, in Node Groups, using `*` in the Group field means the rule applies to all groups.
- `@`: Used as a global wildcard in hierarchical relationships. Unlike `*` which matches within a category, `@` represents a global match across categories.

### Using Wildcards
- When multiple rules exist, more specific rules (without wildcards) take precedence over wildcard rules.
- Wildcards can be used in most reference fields (Node, Group, Period, etc.) but not in measurement or value fields.
- When using wildcards, ensure that default values are provided using `*` or `@` to handle any unspecified cases.

## Required Sheets

The following sheets are required in the input file:
1. Parameters
2. Scenarios
3. Objectives
4. Periods
5. Products
6. Nodes
7. Node Types
8. Node Groups

All other sheets are optional but may be required for specific functionality.

## Sheet Details

### Parameters
Controls global optimization parameters.

| Column    | Type    | Description                   | Example |
|-----------|---------|-------------------------------|---------|
| Parameter | string  | Parameter name                | Max Run Time |
| Value     | numeric | Parameter value               | 3600    |

Required Parameters:
- Max Run Time: Maximum solver runtime in seconds
- Gap Limit: Optimality gap limit (0-1)

### Scenarios
Defines optimization scenarios.

| Column   | Type   | Description    | Required |
|----------|--------|----------------|----------|
| Scenario | string | Scenario name  | Yes      |

### Objectives
Defines optimization objectives and their priorities.

| Column     | Type   | Description              | Required |
|------------|--------|--------------------------|----------|
| Scenario   | string | Scenario name            | Yes      |
| Priority   | int    | Objective priority (1-n) | Yes      |
| Objective  | string | Objective name           | Yes      |
| Relaxation | float  | Relaxation factor (0-1)  | Yes      |

Available Objectives:
- Minimize Cost
- Minimize Maximum Transit Distance
- Minimize Maximum Age
- Maximize Capacity
- Minimize Maximum Utilization
- Minimize Plan-Over-Plan Change
- Minimize Dropped Volume
- Minimize Carried Over Volume

### Periods
Defines time periods for the optimization.

| Column  | Type    | Description                  | Required |
|---------|---------|------------------------------|----------|
| Period  | int     | Period identifier            | Yes      |
| Weight  | float   | Period importance weight     | Yes      |

### Products
Defines products and their measurements.

| Column  | Type    | Description                | Required |
|---------|---------|----------------------------|----------|
| Product | string  | Product identifier         | Yes      |
| Measure | string  | Measurement type           | Yes      |
| Value   | float   | Measurement value          | Yes      |

### Nodes
Defines network nodes and their properties.

| Column                    | Type    | Description                           | Required |
|--------------------------|---------|---------------------------------------|----------|
| Name                     | string  | Node identifier                       | Yes      |
| Node Type                | string  | Type of node                          | Yes      |
| Origin Node              | string  | "X" if origin, blank otherwise        | Yes      |
| Destination Node         | string  | "X" if destination, blank otherwise   | Yes      |
| Intermediate Node        | string  | "X" if intermediate, blank otherwise  | Yes      |
| Receive from Origins     | string  | "X" if can receive from origins      | Yes      |
| Receive from Intermediates| string | "X" if can receive from intermediates | Yes      |
| Send to Destinations     | string  | "X" if can send to destinations      | Yes      |
| Send to Intermediates    | string  | "X" if can send to intermediates     | Yes      |
| Min Launches             | int     | Minimum number of launches            | Yes      |
| Max Launches             | int     | Maximum number of launches            | Yes      |
| Min Operating Duration   | int     | Minimum operating periods            | Yes      |
| Max Operating Duration   | int     | Maximum operating periods            | Yes      |
| Min Shutdowns           | int     | Minimum number of shutdowns          | Yes      |
| Max Shutdowns           | int     | Maximum number of shutdowns          | Yes      |
| Min Shutdown Duration   | int     | Minimum shutdown periods             | Yes      |
| Max Shutdown Duration   | int     | Maximum shutdown periods             | Yes      |

### Node Types
Defines constraints for different node types.

| Column    | Type   | Description              | Required |
|-----------|--------|--------------------------|----------|
| Period    | int    | Time period              | Yes      |
| Node Type | string | Type of node             | Yes      |
| Min Count | int    | Minimum nodes of type    | Yes      |
| Max Count | int    | Maximum nodes of type    | Yes      |

### Flow
Defines flow constraints between nodes.

| Column         | Type   | Description                    | Required |
|---------------|--------|--------------------------------|----------|
| Node          | string | Origin node                    | Yes      |
| Node Group    | string | Origin node group              | Yes      |
| Downstream Node| string | Destination node               | Yes      |
| Downstream Node Group| string | Destination node group   | Yes      |
| Product       | string | Product identifier             | Yes      |
| Period        | int    | Time period                    | Yes      |
| Mode          | string | Transportation mode            | Yes      |
| Container     | string | Container type                 | Yes      |
| Measure       | string | Measurement type               | Yes      |
| Min           | float  | Minimum flow                   | Yes      |
| Max           | float  | Maximum flow                   | Yes      |
| Min Pct of OB | float  | Min percent of outbound flow   | No       |
| Max Pct of OB | float  | Max percent of outbound flow   | No       |
| Min Pct of IB | float  | Min percent of inbound flow    | No       |
| Max Pct of IB | float  | Max percent of inbound flow    | No       |
| Min Connections| int   | Minimum connection count       | No       |
| Max Connections| int   | Maximum connection count       | No       |

[Previous sections remain the same...]

### Transportation Costs
Defines transportation costs between nodes.

| Column                           | Type   | Description                               | Required |
|----------------------------------|--------|-------------------------------------------|----------|
| Period                           | int    | Time period                               | Yes      |
| Origin                           | string | Origin node                               | Yes      |
| Origin Node Group                | string | Origin node group                         | Yes      |
| Destination                      | string | Destination node                          | Yes      |
| Destination Node Group           | string | Destination node group                    | Yes      |
| Mode                            | string | Transportation mode                       | Yes      |
| Container                        | string | Container type                            | Yes      |
| Measure                         | string | Measurement type                          | Yes      |
| Fixed Cost                       | float  | Fixed cost per shipment                   | Yes      |
| Cost per Unit of Distance        | float  | Variable cost per distance unit           | Yes      |
| Cost per Unit of Time            | float  | Variable cost per time unit               | Yes      |
| Minimum Cost Regardless of Distance| float | Minimum cost floor                        | Yes      |

### Transportation Constraints
Defines capacity constraints for transportation.

| Column                | Type   | Description                    | Required |
|----------------------|--------|--------------------------------|----------|
| Period               | int    | Time period                    | Yes      |
| Origin               | string | Origin node                    | Yes      |
| Origin Node Group    | string | Origin node group              | Yes      |
| Destination         | string | Destination node               | Yes      |
| Destination Node Group| string| Destination node group         | Yes      |
| Mode                 | string | Transportation mode            | Yes      |
| Container            | string | Container type                 | Yes      |
| Measure              | string | Measurement type               | Yes      |
| Min                  | float  | Minimum transportation capacity| Yes      |
| Max                  | float  | Maximum transportation capacity| Yes      |

### Transportation Expansions
Defines options for expanding transportation capacity.

| Column                  | Type   | Description                      | Required |
|------------------------|--------|----------------------------------|----------|
| Period                 | int    | Time period                      | Yes      |
| Origin                 | string | Origin node                      | Yes      |
| Destination           | string | Destination node                 | Yes      |
| Incremental Capacity Label| string | Expansion identifier          | Yes      |
| Cost                   | float  | One-time expansion cost          | Yes      |
| Persisting Cost        | float  | Ongoing cost per period          | Yes      |
| Min                    | int    | Minimum expansion units          | Yes      |
| Max                    | int    | Maximum expansion units          | Yes      |

### Transportation Expansion Capacities
Defines capacity increases from expansions.

| Column                  | Type   | Description                   | Required |
|------------------------|--------|-------------------------------|----------|
| Incremental Capacity Label| string | Expansion identifier       | Yes      |
| Mode                   | string | Transportation mode           | Yes      |
| Container              | string | Container type                | Yes      |
| Measure                | string | Measurement type              | Yes      |
| Incremental Capacity   | float  | Added capacity per unit       | Yes      |

### Resource Capacities
Defines resource-based processing capacities.

| Column              | Type   | Description                    | Required |
|--------------------|--------|--------------------------------|----------|
| Period             | int    | Time period                    | Yes      |
| Resource           | string | Resource identifier            | Yes      |
| Node               | string | Node identifier                | Yes      |
| Node Group         | string | Node group                     | Yes      |
| Capacity Type      | string | Type of capacity               | Yes      |
| Capacity per Resource| float | Capacity provided per resource | Yes      |

### Resource Capacity Types
Defines hierarchy of capacity types.

| Column             | Type   | Description                      | Required |
|-------------------|--------|----------------------------------|----------|
| Capacity Type     | string | Capacity type identifier         | Yes      |
| Parent Capacity Type| string| Parent capacity type (if any)    | No       |
| Relative Rate     | float  | Conversion rate to parent capacity| No       |

### Resource Capacity Consumption
Defines how products consume resource capacity.

| Column                        | Type   | Description                          | Required |
|------------------------------|--------|--------------------------------------|----------|
| Product                      | string | Product identifier                   | Yes      |
| Period                       | int    | Time period                          | Yes      |
| Node Group                   | string | Node group                           | Yes      |
| Node                        | string | Node identifier                      | Yes      |
| Capacity Type               | string | Type of capacity consumed            | Yes      |
| Capacity Required per Unit   | float  | Capacity units needed per product    | Yes      |
| Periods of Capacity Consumption| int   | Number of periods capacity is used   | Yes      |

### Resource Costs
Defines costs associated with resources.

| Column                     | Type   | Description                           | Required |
|---------------------------|--------|---------------------------------------|----------|
| Period                    | int    | Time period                           | Yes      |
| Resource                  | string | Resource identifier                   | Yes      |
| Node                      | string | Node identifier                       | Yes      |
| Node Group                | string | Node group                           | Yes      |
| Fixed Cost to Add Resource| float  | One-time cost to add resource        | Yes      |
| Resource Cost per Time Unit| float | Ongoing cost per period              | Yes      |
| Fixed Cost to Remove Resource| float| One-time cost to remove resource     | Yes      |
| Add Resources in Units of | int    | Minimum increment for adding         | Yes      |
| Remove Resources in Units of| int   | Minimum increment for removing       | Yes      |

### Resource Attributes
Defines resource attributes and their consumption.

| Column                | Type   | Description                        | Required |
|----------------------|--------|-----------------------------------|----------|
| Resource Attribute   | string | Attribute identifier              | Yes      |
| Period               | int    | Time period                       | Yes      |
| Value per Resource   | float  | Attribute value per resource unit | Yes      |

### Resource Initial Counts
Defines initial resource assignments.

| Column        | Type   | Description                | Required |
|--------------|--------|----------------------------|----------|
| Resource     | string | Resource identifier        | Yes      |
| Node         | string | Node identifier            | Yes      |
| Node Group   | string | Node group                 | Yes      |
| Initial Count| int    | Starting number of resources| Yes      |

### Demand
Defines product demand at destinations.

| Column      | Type   | Description            | Required |
|------------|--------|------------------------|----------|
| Period     | int    | Time period            | Yes      |
| Product    | string | Product identifier     | Yes      |
| Destination| string | Destination node       | Yes      |
| Demand     | float  | Quantity demanded      | Yes      |

### Carrying Capacity
Defines storage capacity at nodes.

| Column           | Type   | Description                 | Required |
|-----------------|--------|-----------------------------|----------|
| Period          | int    | Time period                 | Yes      |
| Node            | string | Node identifier             | Yes      |
| Node Group      | string | Node group                  | Yes      |
| Measure         | string | Measurement type            | Yes      |
| Inbound Capacity | float  | Incoming storage capacity   | Yes      |
| Outbound Capacity| float  | Outgoing storage capacity   | Yes      |

### Carrying or Missed Demand Cost
Defines costs for storing or missing demand.

| Column               | Type   | Description                    | Required |
|---------------------|--------|--------------------------------|----------|
| Period              | int    | Time period                    | Yes      |
| Product             | string | Product identifier             | Yes      |
| Node                | string | Node identifier                | Yes      |
| Node Group          | string | Node group                     | Yes      |
| Inbound Carrying Cost| float  | Cost per unit stored incoming  | Yes      |
| Outbound Carrying Cost| float | Cost per unit stored outgoing  | Yes      |
| Drop Cost           | float  | Cost per unit of missed demand | Yes      |

### OD Distances and Transit Times
Defines distances and transit times between nodes.

| Column       | Type   | Description                    | Required |
|-------------|--------|--------------------------------|----------|
| Origin      | string | Origin node                    | Yes      |
| Destination | string | Destination node               | Yes      |
| Mode        | string | Transportation mode            | Yes      |
| Distance    | float  | Distance units                 | Yes      |
| Transit Time| float  | Time units                     | Yes      |
| Periods     | int    | Number of periods for transit  | Yes      |

### Age Constraints
Defines age-related constraints for products.

| Column                 | Type   | Description                         | Required |
|-----------------------|--------|-------------------------------------|----------|
| Period                | int    | Time period                         | Yes      |
| Product               | string | Product identifier                  | Yes      |
| Destination          | string | Destination node                    | Yes      |
| Age                   | int    | Product age in periods              | Yes      |
| Destination Node Group| string | Destination node group              | Yes      |
| Max Volume            | float  | Maximum volume at this age          | Yes      |
| Cost per Unit to Violate| float | Penalty cost for age violation     | Yes      |

### Processing Assembly Constraints
Defines product assembly requirements during processing.

| Column      | Type   | Description                     | Required |
|------------|--------|---------------------------------|----------|
| Period     | int    | Time period                     | Yes      |
| Product 1  | string | First product identifier        | Yes      |
| Product 2  | string | Second product identifier       | Yes      |
| Node       | string | Node identifier                 | Yes      |
| Node Group | string | Node group                      | Yes      |
| Product 1 Qty| float | Required quantity of Product 1  | Yes      |
| Product 2 Qty| float | Required quantity of Product 2  | Yes      |

### Shipping Assembly Constraints
Defines product assembly requirements during shipping.

| Column        | Type   | Description                     | Required |
|--------------|--------|---------------------------------|----------|
| Period       | int    | Time period                     | Yes      |
| Product 1    | string | First product identifier        | Yes      |
| Product 2    | string | Second product identifier       | Yes      |
| Origin       | string | Origin node                     | Yes      |
| Destination  | string | Destination node                | Yes      |
| Origin Node Group| string | Origin node group           | Yes      |
| Destination Node Group| string | Destination node group | Yes      |
| Product 1 Qty  | float | Required quantity of Product 1  | Yes      |
| Product 2 Qty  | float | Required quantity of Product 2  | Yes      |

## Data Types and Validation

### Numeric Values
- Integers: Used for counts, periods, and discrete measures
- Floats: Used for costs, capacities, and continuous measures
- Percentages: Expressed as decimals (0-1) unless otherwise noted

### String Values
- Case-sensitive
- No special characters except underscores
- Maximum length: 255 characters

### Boolean Values
- Use "X" for true/yes
- Leave blank for false/no

## Examples

### Using Wildcards in Node Groups
| Node    | Group  | Value |
|---------------|--------|----------|
| Node1   | *      | 100    # Applies to all groups for Node1 |
| Node 1  | @ | 200     # Applies to the aggregate of all groups for Node 1 |
| Node 1  | Group1 | 50     # Applies to all nodes in Group1 |

### Priority and Relaxation Example
| Scenario | Priority | Objective                  | Relaxation |
|----------|----------|----------------------------|------------|
| Base     | 1        | Minimize Cost              | 0          |
| Base     | 2        | Minimize Maximum Distance  | 0.1        |