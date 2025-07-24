#!/usr/bin/env python3

import subprocess
import time
from datetime import datetime
import os
import certifi  # type: ignore

# Import your analysis logic
from StockAnalysis import analyze_nav_csv_and_generate_msg

# Fix SSL issues on macOS (useful if you ever re-enable Telegram or use HTTPS APIs)
os.environ['SSL_CERT_FILE'] = certifi.where()

JMETER_BIN = "/Users/swaraj.thummapudi/Downloads/apache-jmeter-5.6.3/bin/jmeter"
JMX_PATH = "/Users/swaraj.thummapudi/Documents/Personal/Stock/Holdings.jmx"
CSV_OUTPUT = "/Users/swaraj.thummapudi/Documents/Personal/Stock/results/Holdings.csv"

def run_jmeter():
    print("🚀 Running JMeter...")
    result = subprocess.run([
        JMETER_BIN,
        "-n", "-t", JMX_PATH,
        "-l", CSV_OUTPUT
    ])
    if result.returncode == 0:
        print("✅ JMeter completed successfully.")
    else:
        print("❌ JMeter execution failed with code", result.returncode)
    return result.returncode == 0

if __name__ == "__main__":
    # Step 1: Run JMeter
    if run_jmeter():
        # Step 2: Run your NAV analysis
        result = analyze_nav_csv_and_generate_msg()
        print("📊 Analysis Result:\n", result)
    else:
        print("⚠️ Skipping NAV analysis due to JMeter failure.")