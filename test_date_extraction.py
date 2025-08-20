#!/usr/bin/env python3

import os
from datetime import datetime

def extract_date_from_path(file_path):
    # Split the path and extract relevant parts
    path_parts = file_path.split(os.sep)
    try:
        # Debug: print path structure if we get index error
        if len(path_parts) < 4:
            print(f"Path too short: {file_path} has only {len(path_parts)} parts: {path_parts}")
            return None
        
        # Find year, month, day by looking for patterns in the path
        year, month, day = None, None, None
        
        # Look for 4-digit year pattern
        for i, part in enumerate(path_parts):
            if part.isdigit() and len(part) == 4 and 2000 <= int(part) <= 2030:
                year = int(part)
                # Month should be next part
                if i + 1 < len(path_parts):
                    month = path_parts[i + 1]
                # Day should be after month
                if i + 2 < len(path_parts) and path_parts[i + 2].isdigit():
                    day = int(path_parts[i + 2])
                break
        
        if not all([year, month, day]):
            print(f"Could not find year/month/day pattern in path: {file_path}")
            return None
        
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

# Test cases
test_paths = [
    "/app/collections/Papua New Guinea/2023/March/15/part3_questions/oral_question_180.html",
    "/app/collections/Papua New Guinea/2023/March/15/part4.html",
    "/app/collections/Fiji/2023/December/5/part1.html"
]

for path in test_paths:
    result = extract_date_from_path(path)
    print(f"Path: {path}")
    print(f"Date: {result}")
    print()