import json
import os
from datetime import datetime

# --- Configuration ---
PR_FILE_NAME = "artillery_report.json"
BASELINE_FILE_NAME = "baseline_report.json"
OUTPUT_HTML_NAME = "load_performance_simple_report.html"

# --- Internal Keys ---
TIMER_KEY = "plugins.metrics-by-endpoint.response_time./api/login"
PERCENTILE_KEY = "p90"
METRIC_TITLE = "Login API (p90 Response Time)"

# Simple Scoring Parameters
PENALTY_FACTOR = 0.5 
SCORE_THRESHOLD = 95 # Required score for merge

def load_data(file_path):
    """Loads and returns JSON data from a file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: Required file '{file_path}' not found. Please ensure both PR and Baseline files are present.")
    except json.JSONDecodeError:
        raise ValueError(f"Error: Failed to parse JSON content from '{file_path}'.")

def extract_metric(data):
    """
    Safely extracts the p90 response time from the Artillery report.
    This function uses explicit key names to avoid errors caused by the dot '.' in the endpoint path.
    """
    try:
        # 1. Get the 'aggregate' dictionary
        aggregate = data["aggregate"]
        
        # 2. Get the 'summaries' dictionary (Confirmed by user)
        summaries = aggregate["summaries"]

        # 3. Get the specific timer dictionary
        timer_metrics = summaries[TIMER_KEY]
        
        # 4. Get the percentile value
        value = timer_metrics[PERCENTILE_KEY]
        
        return float(value)
        
    except KeyError as e:
        # Provides a detailed error message if a specific key is missing
        if "aggregate" not in data:
             raise KeyError("Error: The top-level 'aggregate' key is missing in one report.")
        elif "summaries" not in aggregate:
             raise KeyError("Error: The 'summaries' key is missing under 'aggregate' in one report.")
        elif TIMER_KEY not in summaries:
             raise KeyError(f"Error: The timer key '{TIMER_KEY}' (for /api/login) is missing under 'summaries'.")
        else:
             raise KeyError(f"Error: The percentile key '{PERCENTILE_KEY}' is missing in the timer metrics.")
    except (TypeError, ValueError):
        raise ValueError("Error: The extracted p90 value is not a valid number.")

def calculate_simple_score(pr_value, baseline_value):
    """Calculates the score based on simple direct regression penalty."""
    
    regression = pr_value - baseline_value
    
    if regression <= 0:
        penalty = 0.0
        status = "Pass ✅ (Improvement)"
        status_class = "good"
    else:
        penalty = regression * PENALTY_FACTOR
        status = "Fail ❌ (Regression)"
        status_class = "poor"
        
    final_score = max(0, 100 - penalty)
    
    return {
        "score": round(final_score, 2),
        "regression": round(regression, 2),
        "status": status,
        "status_class": status_class,
        "penalty": round(penalty, 2),
        "penalty_factor": PENALTY_FACTOR
    }

def generate_report():
    """Main function to generate the HTML report."""
    
    pr_value = 0.0
    baseline_value = 0.0
    final_score = 0.0
    score_results = {}
    error_message = None

    try:
        # 1. Load Data
        pr_data = load_data(PR_FILE_NAME)
        baseline_data = load_data(BASELINE_FILE_NAME)
        
        # 2. Extract Metric Values (Must succeed to proceed)
        pr_value = extract_metric(pr_data)
        baseline_value = extract_metric(baseline_data)
        
        # 3. Calculate Score
        score_results = calculate_simple_score(pr_value, baseline_value)
        final_score = score_results["score"]
        
    except (FileNotFoundError, ValueError, KeyError) as e:
        error_message = str(e)
    
    
    # 4. Determine Merge Status (Only if no critical error occurred)
    if error_message:
        merge_status_text = "ERROR 🚨"
        merge_status_class = "status-poor"
    else:
        merge_status_text = "MERGE BLOCKED 🛑" if final_score < SCORE_THRESHOLD else "MERGE ALLOWED ✅"
        merge_status_class = "poor" if final_score < SCORE_THRESHOLD else "good"

    # 5. Compile HTML
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Load Performance Scorecard</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f7f6; color: #333; }}
        .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
        h1 {{ color: #007bff; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .score-card {{ text-align: center; margin: 30px 0; padding: 20px; border-radius: 10px; }}
        .score-card h2 {{ margin-top: 0; border: none; }}
        .final-score {{ font-size: 4.5em; font-weight: bold; margin-top: 0; line-height: 1; }}
        .good {{ color: #28a745; }}
        .poor {{ color: #dc3545; }}
        .status-box {{ padding: 10px; border-radius: 5px; font-weight: bold; }}
        .status-poor {{ background-color: #f8d7da; color: #721c24; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #007bff; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Simple Load Test Performance Gate Check</h1>
        
        <div class="score-card">
            <h2 class="{merge_status_class}">{merge_status_text}</h2>
            <p>Performance Quality Index (PQI)</p>
            <div class="final-score {score_results.get('status_class', 'poor')}">{final_score:.2f}</div>
            <p>Required Threshold: {SCORE_THRESHOLD}</p>
        </div>
        
        <h2>Scoring Breakdown</h2>
        <table>
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>p90 Value (ms)</th>
                    <th>Source</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>{METRIC_TITLE} (Baseline)</td>
                    <td>{baseline_value:.2f}</td>
                    <td>{BASELINE_FILE_NAME}</td>
                </tr>
                <tr>
                    <td>{METRIC_TITLE} (Pull Request)</td>
                    <td>{pr_value:.2f}</td>
                    <td>{PR_FILE_NAME}</td>
                </tr>
                <tr>
                    <th>Regression (&Delta;)</th>
                    <th colspan="2">{score_results.get('regression', 'N/A')} ms</th>
                </tr>
            </tbody>
        </table>
        
        <h2>Score Calculation</h2>
        <table>
            <thead>
                <tr>
                    <th>Step</th>
                    <th>Detail</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Base Score</td>
                    <td>Start at 100</td>
                    <td>100</td>
                </tr>
                <tr>
                    <td>Regression</td>
                    <td>{baseline_value:.2f} ms &rarr; {pr_value:.2f} ms</td>
                    <td>{score_results.get('regression', 'N/A')} ms</td>
                </tr>
                <tr>
                    <td>Penalty Calculation</td>
                    <td>Regression ms &times; {score_results.get('penalty_factor', PENALTY_FACTOR)}</td>
                    <th>-{score_results.get('penalty', 0.0):.2f} Points</th>
                </tr>
                <tr>
                    <th>Final Score</th>
                    <th>100 - {score_results.get('penalty', 0.0):.2f}</th>
                    <th class="{score_results.get('status_class', 'poor')}">{final_score:.2f}</th>
                </tr>
            </tbody>
        </table>
        
        {f'<p class="status-box status-poor" style="text-align: center; margin-top: 30px;">Error: {error_message}</p>' if error_message else ''}

    </div>
</body>
</html>
"""
    # 6. Save HTML File
    with open(OUTPUT_HTML_NAME, 'w') as f:
        f.write(html_content)

    print(f"\n✅ Success: Load performance report saved as '{OUTPUT_HTML_NAME}'")
    if not error_message:
        print(f"   Final PQI Score: {final_score:.2f}")
    else:
        print(f"   ❌ Execution Failed: {error_message}")

if __name__ == "__main__":
    generate_report()