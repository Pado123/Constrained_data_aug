# Constraint-Based Event Log Generation Framework

This repository contains the implementation of a **Constraint-based Event Log Generation Framework** described in the thesis "Augmentation of Event Logs under User-Defined Process Constraints". The framework generates synthetic event logs that conform to declarative process constraints while preserving statistical properties of the original logs.

## Overview

The framework enables the generation of synthetic event logs that:
- **Adhere to declarative process constraints** (e.g., precedence, response, existence constraints)
- **Preserve statistical properties** of the original log (activity frequencies, resource distributions, timestamps, etc.)
- **Support multiple generation scenarios** with different constraint application strategies

### Key Features

- **Declarative Constraint Support**: Implementations of common Declare constraints as Non-deterministic Finite Automata (NFAs)
- **Multiple Generation Scenarios**:
  - **Our Approach k=3**: Constraint-based sequence generation using constrained transition systems
  - **Our Approach k=∞**: Filter original log by constraints, then generate
  - **baseline k=3**: Generate sequences from filtered log
  - **baseline k=∞**: Generate sequences from filtered log
- **Conformance Checking**: CFLD (Conformance Checking based on Frequencies of Labeled Directly-follows Relations) metric computation
- **Experiment Management**: Organized constraint sets by case study and experiment

## Installation

### Requirements

- Python 3.7+
- Required packages (install via pip):
  ```bash
  pip install pm4py pandas numpy automata-lib tqdm
  ```

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Constrained_data_aug
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   (If no requirements.txt exists, install packages manually as listed above)

3. Download data files:
   - Data files are available at: [Google Drive Link](https://drive.google.com/drive/folders/1i6dlmlvRnXmL00meEVy9674uX8Z3uZ-t?usp=sharing)
   - Extract the `data` folder to the workspace root
   - Extract simulation results to `simulations/` if available

## Project Structure

```
Constrained_data_aug/
├── ConstraintBasedEventLogGenerator/    # Main framework code
│   ├── EventLogGenerator.py            # Core event log generation class
│   ├── run_framework.py                # Main script to run simulations
│   ├── constraints/                    # Constraint definitions and utilities
│   │   ├── constraints_automata.py    # NFA implementations of constraints
│   │   ├── constraints_per_log.py     # Case-study specific constraints
│   │   ├── constraints_per_log_restructured.py  # Experiment-organized constraints
│   │   └── framework_constraints.py   # Constraint filtering and application
│   ├── src/                           # Utility modules
│   │   ├── gen_seq_utils.py          # Sequence generation
│   │   ├── gen_time_utils.py         # Timestamp generation
│   │   ├── gen_res_utils.py          # Resource generation
│   │   └── gen_attr_utils.py         # Attribute generation
│   ├── generate_filtered_test_logs.py # Generate filtered test logs by experiment
│   ├── compute_cfld_all_scenarios.py  # Compute CFLD metrics
│   └── generate_cfld_latex_table.py   # Generate LaTeX tables from results
├── data/                              # Input event logs (XES format)
├── simulations/                       # Generated simulation logs (CSV format)
├── filtered_test_logs/                # Filtered test logs per experiment
└── README.md                          # This file
```

## Usage

### 1. Running Event Log Generation

The main script `run_framework.py` generates synthetic event logs for specified case studies:

```python
# Configure parameters in run_framework.py
case_studies = ['Production', 'Purchasing', ...]
N_SIM = 10  # Number of simulations per scenario
exp = 'exp1'  # Experiment identifier

# Run the framework
python run_framework.py
```

**Configuration:**
- `case_studies`: List of case studies to process
- `N_SIM`: Number of simulation runs per scenario
- `exp`: Experiment identifier (determines which constraints are used)
- `k`: Order of the k-gram model for sequence generation

**Output:**
- Generated logs saved in `simulations/{case_study}/{scenario}/{exp}/sim_*.csv`
- Execution times and statistics saved alongside logs

### 2. Generating Filtered Test Logs

To create filtered test logs for each experiment's constraint set:

```bash
cd ConstraintBasedEventLogGenerator
python generate_filtered_test_logs.py
```

**What it does:**
1. Loads original event logs from `data/`
2. Splits logs into train/test sets (80/20)
3. Filters test logs based on experiment-specific constraints
4. Saves filtered logs to `filtered_test_logs/{case_study}/test_log_{exp}.xes`

**Important:** Before running, ensure constraints are enabled in `constraints/constraints_per_log_restructured.py`. Constraints are organized by case study and experiment.

### 3. Computing CFLD Metrics

To compute CFLD (conformance) between generated logs and filtered test logs:

```bash
cd ConstraintBasedEventLogGenerator
python compute_cfld_all_scenarios.py
```

**What it does:**
1. Loads generated simulation logs from `simulations/`
2. Loads corresponding filtered test logs
3. Computes CFLD metric for each scenario
4. Saves results progressively to `cfld_results.csv`

**CFLD Metric:** Measures similarity between two logs based on directly-follows relation frequencies. Lower values indicate better conformance.

### 4. Generating LaTeX Tables

To create formatted LaTeX tables from CFLD results:

```bash
cd ConstraintBasedEventLogGenerator
python generate_cfld_latex_table.py
```

**Output:** `cfld_table.tex` - Formatted table with CFLD values organized by case study, experiment, and scenario.

## Constraint System

### Declarative Constraints

The framework supports standard Declare constraints implemented as NFAs:

- **Existence**: Activity must occur at least N times
- **Absence**: Activity must not occur
- **Init/Last**: Activity must be first/last
- **Precedence/Response**: Ordering constraints between activities
- **Chain Precedence/Response**: Immediate ordering constraints
- **Coexistence**: Activities must occur together
- **Choice/Exclusive Choice**: Alternative paths

### Defining Constraints

Constraints are defined per case study and experiment in `constraints/constraints_per_log_restructured.py`:

```python
'Production': {
    'exp1': [
        init_constraint('Turning & Milling_lc:start', alphabet),
        # ... more constraints
    ],
    'exp2': [
        chain_response_constraint('Final Inspection Q.C._lc:complete', 'Packing_lc:start', alphabet),
        # ... more constraints
    ],
}
```

### Constraint Functions

All constraint functions are in `constraints/constraints_automata.py`. Each returns an NFA that accepts conforming traces.

## Case Studies

The framework has been tested on multiple real-world event logs:

- **Production**: Manufacturing process log
- **Purchasing**: Procurement process log
- **Consulta**: Medical consultation process
- **BPI Challenges**: 
  - BPI12W, BPI12A, BPI12O (2012 variants)
  - BPI17W, BPI17O (2017 variants)
- **Hospital**: Hospital admission process

## Generation Scenarios

### Our Approach k=3: Constraint-Based Generation
- Uses constrained transition system (intersection of log's transition system with constraint NFAs)
- Generates sequences that satisfy constraints while preserving log statistics

### baseline k=3: Post-Filtering
- Filters original log by constraints first
- Then generates sequences from filtered log

### Our Approach k=∞: Filtered Log Generation
- Generates sequences directly from constraint-filtered log

### Scenario D: With Data Attributes
- Includes data attribute generation based on log statistics

### Scenario E: With Resource Constraints
- Includes resource allocation and calendar-based constraints

## Results and Outputs

### Simulation Logs
- Location: `simulations/{case_study}/{scenario}/{exp}/`
- Format: CSV files (`sim_0.csv`, `sim_1.csv`, ...)
- Each simulation contains generated traces with full event details

### Filtered Test Logs
- Location: `filtered_test_logs/{case_study}/`
- Format: XES files (`test_log_exp1.xes`, `test_log_exp2.xes`, ...)
- Contains traces from test set that satisfy experiment constraints

### CFLD Results
- Location: `ConstraintBasedEventLogGenerator/cfld_results.csv`
- Format: CSV with columns: `case_study`, `experiment`, `scenario`, `CFLD`
- LaTeX table: `ConstraintBasedEventLogGenerator/cfld_table.tex`

### Entropy Results
- Location: `ConstraintBasedEventLogGenerator/results/entropies/`
- Contains entropy analysis results for each case study

## Data Requirements

Event logs should be in **XES format** (eXtensible Event Stream) with:
- **Activities**: Event names in `concept:name`
- **Lifecycle transitions**: (Optional) as `_lc:start` and `_lc:complete` suffixes

## Citation

If you use this framework in your research, please cite:

```
[Your Thesis Citation]
"Augmentation of Event Logs under User-Defined Process Constraints"
```

## License

[Specify license if applicable]

## Contact

[Add contact information if needed]

## Acknowledgments

- Built using [pm4py](https://pm4py.fit.fraunhofer.de/) for process mining
- Uses [automata-lib](https://github.com/caleb531/automata) for NFA operations

---

**Note:** Data files and simulation results are available separately at the [Google Drive link](https://drive.google.com/drive/folders/1i6dlmlvRnXmL00meEVy9674uX8Z3uZ-t?usp=sharing) mentioned above.
