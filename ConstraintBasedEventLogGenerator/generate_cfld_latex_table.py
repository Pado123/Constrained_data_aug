"""
Script to generate a LaTeX table from CFLD results in a specific format.

Creates a formatted LaTeX table with CFLD values organized by case study, experiment, and scenario.
"""

import pandas as pd
import os


def generate_latex_table_formatted(csv_file: str, output_file: str = 'cfld_table.tex'):
    """
    Generate a LaTeX table from CFLD results CSV in the requested format.
    
    Args:
        csv_file: Path to the CFLD results CSV file
        output_file: Path to output LaTeX file
    """
    # Load data
    df = pd.read_csv(csv_file)
    
    # Sort by case_study, experiment, scenario
    df = df.sort_values(['case_study', 'experiment', 'scenario']).reset_index(drop=True)
    
    # Get all unique scenarios
    all_scenarios = sorted(df['scenario'].unique())
    
    # Get case study mapping (use uppercase and map names)
    case_study_mapping = {
        'ds01': 'DS01',
        'ds02': 'DS02',
        'ds03': 'DS03',
        'ds04': 'DS04',
        'ds05': 'DS05',
        'ds06': 'DS06',
        'Purchasing': 'DS02',
        'Production': 'DS03',
        'Consulta': 'DS01',
        'bpi12': 'BPI12W',
        'bpi12a': 'BPI12A',
        'bpi12o': 'BPI12O',
        'bpi17': 'BPI17W',
        'bpi17o': 'BPI17O',
        'hospital': 'DS06',
        'hospital_italy': 'DS06',
    }
    
    # Create LaTeX table
    latex_lines = []
    latex_lines.append("\\begin{table*}[t!]")
    latex_lines.append("\\centering")
    latex_lines.append("")
    latex_lines.append("\\resizebox{\\textwidth}{!}{")
    
    # Build column specification
    num_scenario_cols = len(all_scenarios)
    col_spec = "|l|l|" + "c|" * num_scenario_cols
    latex_lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    latex_lines.append("\\toprule")
    
    # Header row: Use Case, Exp, then scenario names
    header = "\\textbf{Use Case} & \\textbf{Exp} "
    for scenario in all_scenarios:
        # Extract scenario letter (A, B, C, etc.)
        scenario_label = scenario.replace('scenario', '')
        header += f"& \\textbf{{{scenario_label}}} "
    header += "\\\\"
    latex_lines.append(header)
    latex_lines.append("\\midrule")
    
    current_case = None
    case_studies = sorted(df['case_study'].unique())
    
    for case_study in case_studies:
        case_display = case_study_mapping.get(case_study, case_study)
        case_df = df[df['case_study'] == case_study]
        experiments = sorted(case_df['experiment'].unique())
        
        for exp_idx, experiment in enumerate(experiments):
            exp_df = case_df[case_df['experiment'] == experiment]
            
            # Build row
            if exp_idx == 0:
                row_str = f"{case_display} & {experiment} "
            else:
                row_str = f" & {experiment} "
            
            # Add CFLD values for each scenario
            for scenario in all_scenarios:
                scenario_data = exp_df[exp_df['scenario'] == scenario]
                if not scenario_data.empty:
                    cfld_val = scenario_data.iloc[0]['CFLD']
                    row_str += f"& {cfld_val:.2f} "
                else:
                    row_str += "& -- "
            
            row_str += "\\\\"
            latex_lines.append(row_str)
        
        # Add midrule between case studies (except after last one)
        if case_study != case_studies[-1]:
            latex_lines.append("\\midrule")
    
    latex_lines.append("\\bottomrule")
    latex_lines.append("\\end{tabular}}")
    latex_lines.append("\\caption{CFLD values per use case and experiment.}")
    latex_lines.append("\\label{tab:cfld}")
    latex_lines.append("\\end{table*}")
    
    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(latex_lines))
    
    print(f"LaTeX table saved to: {output_file}")
    return output_file


def main():
    """Generate LaTeX table."""
    csv_file = 'cfld_results.csv'
    
    if not os.path.exists(csv_file):
        print(f"Error: CFLD results file not found: {csv_file}")
        return
    
    print("=" * 80)
    print("Generating Formatted LaTeX Table from CFLD Results")
    print("=" * 80)
    
    generate_latex_table_formatted(csv_file, 'cfld_table.tex')
    
    print("\n" + "=" * 80)
    print("LaTeX table generated successfully!")
    print("=" * 80)


if __name__ == '__main__':
    main()
