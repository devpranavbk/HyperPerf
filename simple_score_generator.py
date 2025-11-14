import json
import os
from datetime import datetime

# --- Configuration ---
PR_FILE_NAME = "artillery_report.json"
BASELINE_FILE_NAME = "baseline_report.json"
OUTPUT_HTML_NAME = "load_test_report.html"

# --- Internal Keys (Artillery Report Path) ---
# This path is specific to extracting the p90 latency for the /api/login endpoint
TIMER_KEY = "plugins.metrics-by-endpoint.response_time./api/login"
PERCENTILE_KEY = "p90"
METRIC_TITLE = "Login API (P90 Response Time)"

# Simple Scoring Parameters
PENALTY_FACTOR = 0.5 
# SCORE_THRESHOLD = 85 # Required score for merge (Kept for internal logic, but not displayed)

def load_data(file_path):
    """Loads and returns JSON data from a local file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # Custom error for missing files
        raise FileNotFoundError(f"Error: Required file '{file_path}' not found. Please ensure both PR and Baseline files are present.")
    except json.JSONDecodeError:
        # Custom error for malformed JSON
        raise ValueError(f"Error: Failed to parse JSON content from '{file_path}'.")

def extract_metric(data):
    """
    Safely extracts the p90 response time in milliseconds (assuming input is ms).
    It uses the confirmed path inside 'aggregate.summaries'.
    """
    try:
        # 1. Navigate through the structure
        aggregate = data["aggregate"]
        summaries = aggregate["summaries"]
        timer_metrics = summaries[TIMER_KEY]
        
        # 2. Extract the percentile value
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
    
    # Status is based on whether there is any latency increase (regression > 0)
    if regression <= 0:
        penalty = 0.0
        status = "PASS (Improvement)"
        status_class = "good"
    else:
        # Calculate penalty only if there is an increase
        penalty = regression * PENALTY_FACTOR
        status = "FAIL (Latency Increase)"
        status_class = "poor"
        
    # Score cannot go below zero
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
        # 1. Load Data - Both are loaded locally
        pr_data = load_data(PR_FILE_NAME)
        baseline_data = load_data(BASELINE_FILE_NAME)
        
        # 2. Extract Metric Values 
        pr_value = extract_metric(pr_data)
        baseline_value = extract_metric(baseline_data)
        
        # 3. Calculate Score
        score_results = calculate_simple_score(pr_value, baseline_value)
        final_score = score_results["score"]
        
    except (FileNotFoundError, ValueError, KeyError) as e:
        error_message = str(e)
        # Ensure default structure for error reporting if score calculation fails
        score_results = {"regression": "N/A", "penalty": 0.0, "penalty_factor": PENALTY_FACTOR, "status_class": "poor"}
        final_score = 0.0 # Set score to 0 on critical error

        return final_score
    
    
    # 4. Determine Merge Status (Kept for internal logic, but not displayed in HTML)
    # This status logic is still used for score coloring below.
    # if error_message:
    #     merge_status_text = "REPORT ERROR 🚨"
    #     merge_status_class = "bg-red-500"
    # else:
    #     # Uses the SCORE_THRESHOLD internally
    #     merge_status_text = "MERGE BLOCKED 🛑" if final_score < SCORE_THRESHOLD else "MERGE ALLOWED ✅"
    #     merge_status_class = "bg-red-500" if final_score < SCORE_THRESHOLD else "bg-green-500"

    # Define color classes for score
    score_color_class = "text-green-600" if score_results["status_class"] == "good" else "text-red-600"
    
    # Get current date and time for the report header
    report_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 5. Compile HTML (Tailwind CSS based)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Load Performance Scorecard</title>
    <!-- Load Tailwind CSS via CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Custom font */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        body {{ font-family: 'Inter', sans-serif; }}
        /* Specific coloring utilities */
        .good-text {{ color: #10B981; }}
        .poor-text {{ color: #EF4444; }}
        .good-bg {{ background-color: #D1FAE5; }}
        .poor-bg {{ background-color: #FEE2E2; }}
    </style>
</head>
<body class="bg-gray-100 text-gray-800 p-4 sm:p-8">

    <div class="max-w-4xl mx-auto">
        
        <!-- Header -->
        <header class="mb-8 p-6 bg-white shadow-lg rounded-xl">
            <h1 class="text-3xl font-extrabold text-indigo-700">Performance Report</h1>
            <p class="text-gray-500 mt-1 text-sm">Generated on: {report_date}</p>
            <p class="text-gray-500 mt-2">Comparison of PR against Baseline for Critical API Latency</p>
        </header>

        <!-- Main Score -->
        <div class="grid grid-cols-1 mb-10">
            
            <!-- PQI Score -->
            <div class="bg-white p-6 rounded-xl shadow-md text-center border-b-4 border-indigo-500">
                <p class="text-sm text-gray-500 font-semibold uppercase">Performance Quality Index (PQI)</p>
                <div class="{score_color_class} text-6xl font-extrabold my-2">{final_score:.2f}</div>
            </div>
            
        </div>

        <!-- Metric Values Table -->
        <h2 class="text-2xl font-bold text-gray-700 mb-4 border-b pb-2">Metric Comparison</h2>
        <div class="bg-white rounded-xl shadow-md overflow-hidden mb-10">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Metric</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Previous Value</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latest Value</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Latency Increase (Δ)</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{METRIC_TITLE}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{baseline_value:.2f} ms</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{pr_value:.2f} ms</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-bold {score_results.get('status_class', 'poor')}-text">{score_results.get('regression', 'N/A')} ms</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Score Calculation Breakdown -->
        <h2 class="text-2xl font-bold text-gray-700 mb-4 border-b pb-2">Score Calculation Breakdown</h2>
        <div class="bg-white rounded-xl shadow-md overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Step</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Calculation</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Points Change</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-200">
                    
                    <tr class="good-bg">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Base Score</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">Start Value</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-green-700">+100</td>
                    </tr>
                    
                    <tr>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Latency Increase</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{baseline_value:.2f} ms &rarr; {pr_value:.2f} ms</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{score_results.get('regression', 'N/A')} ms</td>
                    </tr>
                    
                    <tr class="poor-bg">
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">Penalty</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700">Latency Increase &times; Penalty Factor ({score_results.get('penalty_factor', 0.0)})</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-red-700">-{score_results.get('penalty', 0.0):.2f}</td>
                    </tr>

                    <tr class="bg-indigo-50 font-bold">
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-indigo-700">FINAL PQI SCORE</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-indigo-700">100 - {score_results.get('penalty', 0.0):.2f}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-lg {score_color_class}">{final_score:.2f}</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- Error Message (if any) -->
        {f'<div class="p-4 mt-6 rounded-lg bg-red-100 border border-red-400 text-red-800 text-center font-medium shadow-sm"><p>{error_message}</p><p>Please check if the files "{PR_FILE_NAME}" and "{BASELINE_FILE_NAME}" exist and contain the path: aggregate.summaries.{TIMER_KEY}.{PERCENTILE_KEY}</p></div>' if error_message else ''}

    </div>
</body>
</html>
"""
    # 6. Save HTML File
    with open(OUTPUT_HTML_NAME, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ Success: Load performance report saved as '{OUTPUT_HTML_NAME}'")
    if not error_message:
        print(f"   Final PQI Score: {final_score:.2f}")
    else:
        print(f"   ❌ Execution Failed: {error_message}")
    
    return final_score   # ← REQUIRED


if __name__ == "__main__":
    final_score = generate_report()   # Capture returned score
    with open("score_output.json", "w") as f:
            json.dump({"pqi_score": final_score}, f)