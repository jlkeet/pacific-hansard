#!/usr/bin/env python3

import os
from datetime import datetime

def get_source_from_path(file_path):
    # Assuming that the structure is /app/collections/{source}/...
    parts = file_path.split(os.sep)
    try:
        # Look for collections in the path and get the next part
        collections_index = -1
        for i, part in enumerate(parts):
            if part == "collections":
                collections_index = i
                break
        
        if collections_index >= 0 and collections_index + 1 < len(parts):
            source = parts[collections_index + 1]
            # Handle "Papua New Guinea" as a single source name
            if source == "Papua" and collections_index + 2 < len(parts) and parts[collections_index + 2] == "Guinea":
                source = "Papua New Guinea"
            return source
        else:
            # Fallback to original logic
            source = parts[3]  # Index 3 assumes /app/collections/{source}/...
            return source
    except IndexError:
        return "Unknown Source"

def extract_date_from_path(file_path):
    # Split the path and extract relevant parts
    path_parts = file_path.split(os.sep)
    try:
        # Debug: print path structure if we get index error
        if len(path_parts) < 4:
            print(f"Path too short: {file_path} has only {len(path_parts)} parts: {path_parts}")
            return None
            
        year = int(path_parts[-4])  # Assuming year is 4 levels up from the filename
        month = path_parts[-3]  # Month name
        day = int(path_parts[-2])  # Day of the month
        
        # Convert month name to number - handle both full and abbreviated month names
        month_mappings = {
            'January': 1, 'Jan': 1,
            'February': 2, 'Feb': 2,
            'March': 3, 'Mar': 3,
            'April': 4, 'Apr': 4,
            'May': 5,
            'June': 6, 'Jun': 6,
            'July': 7, 'Jul': 7,
            'August': 8, 'Aug': 8,
            'September': 9, 'Sep': 9, 'Sept': 9,
            'October': 10, 'Oct': 10,
            'November': 11, 'Nov': 11,
            'December': 12, 'Dec': 12
        }
        
        month_num = month_mappings.get(month)
        if month_num is None:
            # Try parsing with strptime as fallback
            month_num = datetime.strptime(month, '%B').month
        
        # Create a date object
        date = datetime(year, month_num, day)
        
        # Return formatted date string
        return date.strftime('%Y-%m-%d')
    except (ValueError, IndexError, KeyError) as e:
        print(f"Could not extract date from path: {file_path} - Error: {str(e)}")
        return None

# Test PNG file path
test_file = "/Users/jacksonkeet/Pacific Hansard Development/collections/Papua New Guinea/2025/August/19/part6.html"

print("=== Testing PNG Path Parsing ===")
print(f"Test file: {test_file}")
print(f"Path parts: {test_file.split(os.sep)}")

# Test source extraction
source = get_source_from_path(test_file)
print(f"Extracted source: '{source}'")

# Test date extraction  
date = extract_date_from_path(test_file)
print(f"Extracted date: '{date}'")

# Test Railway path (this is what would be used in production)
railway_test_file = "/app/collections/Papua New Guinea/2025/August/19/part6.html"
print(f"\n=== Testing Railway Path ===")
print(f"Railway file: {railway_test_file}")
print(f"Railway path parts: {railway_test_file.split(os.sep)}")

railway_source = get_source_from_path(railway_test_file)
print(f"Railway extracted source: '{railway_source}'")

railway_date = extract_date_from_path(railway_test_file)
print(f"Railway extracted date: '{railway_date}'")