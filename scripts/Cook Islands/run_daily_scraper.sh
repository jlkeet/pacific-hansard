#!/bin/bash
# Daily scraper runner for Cook Islands Hansard

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/daily_scraper_$(date +%Y-%m-%d).log"

# Create logs directory if it doesn't exist
mkdir -p "${LOG_DIR}"

# Navigate to the script directory
cd "${SCRIPT_DIR}"

echo "$(date): Starting Cook Islands Hansard daily scraper" | tee -a "${LOG_FILE}"

# Check for a Python virtual environment
if [ -d "${SCRIPT_DIR}/../env" ]; then
    echo "$(date): Activating virtual environment" | tee -a "${LOG_FILE}"
    source "${SCRIPT_DIR}/../env/bin/activate"
fi

# Check that required packages are installed without reinstalling
echo "$(date): Checking requirements" | tee -a "${LOG_FILE}"
# Use --no-deps to avoid dependency resolution which can be slow
# python3 -m pip install --no-deps --quiet --exists-action=w -r ../../requirements.txt 2>&1 | tee -a "${LOG_FILE}"

# Check for additional dependencies needed for scraping
echo "$(date): Checking additional dependencies" | tee -a "${LOG_FILE}"
for pkg in requests beautifulsoup4 pdfminer.six; do
    if ! python3 -c "import $pkg" &>/dev/null; then
        echo "$(date): Installing $pkg" | tee -a "${LOG_FILE}"
        python3 -m pip install --quiet "$pkg" 2>&1 | tee -a "${LOG_FILE}"
    else
        echo "$(date): $pkg already installed" | tee -a "${LOG_FILE}"
    fi
done

# Run the scraper with timeout to prevent hanging
echo "$(date): Running the scraper" | tee -a "${LOG_FILE}"

# Define a timeout (30 minutes)
TIMEOUT=1800

# Function to run the scraper with timeout
run_with_timeout() {
    echo "$(date): Running script $1 with ${TIMEOUT}s timeout" | tee -a "${LOG_FILE}"
    
    # Use timeout command if available
    if command -v timeout &> /dev/null; then
        timeout ${TIMEOUT} python3 "$1" 2>&1 | tee -a "${LOG_FILE}"
        return $?
    else
        # Fallback if timeout command isn't available (e.g., on macOS)
        echo "$(date): Warning - 'timeout' command not available, running without timeout" | tee -a "${LOG_FILE}"
        python3 "$1" 2>&1 | tee -a "${LOG_FILE}"
        return $?
    fi
}

# Use the daily checker for efficient processing
if [ -f "daily_checker.py" ]; then
    echo "$(date): Using daily_checker.py for efficient processing" | tee -a "${LOG_FILE}"
    run_with_timeout "daily_checker.py"
    STATUS=$?
elif [ -f "CI-hansard-scraper.py" ]; then
    echo "$(date): Warning - daily_checker.py not found, using full scraper" | tee -a "${LOG_FILE}"
    run_with_timeout "CI-hansard-scraper.py"
    STATUS=$?
else
    echo "$(date): ERROR - Scraper script not found!" | tee -a "${LOG_FILE}"
    exit 1
fi

# Check exit status
if [ $STATUS -eq 0 ]; then
    echo "$(date): Scraper completed successfully" | tee -a "${LOG_FILE}"
elif [ $STATUS -eq 124 ]; then
    echo "$(date): ERROR - Scraper timed out after ${TIMEOUT} seconds" | tee -a "${LOG_FILE}"
    exit 124
else
    echo "$(date): ERROR - Scraper failed with exit code $STATUS" | tee -a "${LOG_FILE}"
    exit $STATUS
fi

# If using a virtual environment, deactivate it
if [ -d "${SCRIPT_DIR}/../env" ]; then
    echo "$(date): Deactivating virtual environment" | tee -a "${LOG_FILE}"
    deactivate
fi

echo "$(date): Daily scraper run completed" | tee -a "${LOG_FILE}"