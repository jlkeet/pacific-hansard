#!/usr/bin/env python3
"""
Analyze Fiji hansards for question sections
"""
import os
import re
from collections import defaultdict

def search_for_questions():
    """Search for question patterns in all Fiji hansards"""
    
    collections_base = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"
    
    question_patterns = [
        r'ORAL QUESTIONS',
        r'WRITTEN QUESTIONS',
        r'QUESTIONS AND REPLIES',
        r'QUESTION TIME',
        r'QUESTIONS TO MINISTERS',
        r'Question No\.',
        r'Question \d+',
        r'QUESTION:',
        r'Q\d+:',
        r'SUPPLEMENTARY QUESTION',
        r'ORAL QUESTION',
        r'WRITTEN QUESTION'
    ]
    
    results = defaultdict(list)
    files_with_questions = []
    
    print("Searching for question sections in Fiji hansards...")
    print("=" * 60)
    
    for year in ['2023', '2024']:
        year_path = os.path.join(collections_base, year)
        if not os.path.isdir(year_path):
            continue
            
        for month in os.listdir(year_path):
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue
                
            for day in os.listdir(month_path):
                day_path = os.path.join(year_path, month, day)
                if not os.path.isdir(day_path):
                    continue
                
                date_str = f"{year}/{month}/{day}"
                found_questions = False
                
                # Search in HTML files
                for file in os.listdir(day_path):
                    if file.endswith('.html'):
                        file_path = os.path.join(day_path, file)
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            for pattern in question_patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                if matches:
                                    found_questions = True
                                    results[date_str].append({
                                        'file': file,
                                        'pattern': pattern,
                                        'matches': len(matches),
                                        'examples': matches[:3]
                                    })
                
                if found_questions:
                    files_with_questions.append(date_str)
    
    # Print results
    print(f"\nFound question sections in {len(files_with_questions)} hansards:")
    print("-" * 60)
    
    for date in sorted(files_with_questions):
        print(f"\n{date}:")
        for finding in results[date]:
            print(f"  File: {finding['file']}")
            print(f"  Pattern: {finding['pattern']}")
            print(f"  Matches: {finding['matches']}")
            if finding['examples']:
                print(f"  Examples: {finding['examples']}")
    
    # Let's also look at specific content samples
    print("\n" + "=" * 60)
    print("DETAILED CONTENT ANALYSIS")
    print("=" * 60)
    
    # Pick a few files to analyze in detail
    sample_files = files_with_questions[:5] if files_with_questions else []
    
    for date in sample_files:
        year, month, day = date.split('/')
        day_path = os.path.join(collections_base, year, month, day)
        
        print(f"\nAnalyzing {date} in detail:")
        
        # Look for the file with most question matches
        best_file = None
        max_matches = 0
        
        for finding in results[date]:
            if finding['matches'] > max_matches:
                max_matches = finding['matches']
                best_file = finding['file']
        
        if best_file:
            file_path = os.path.join(day_path, best_file)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract context around question patterns
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if any(re.search(pattern, line, re.IGNORECASE) for pattern in question_patterns):
                        # Print context
                        start = max(0, i-2)
                        end = min(len(lines), i+10)
                        print(f"\n  Context from {best_file}:")
                        for j in range(start, end):
                            if j == i:
                                print(f"  >>> {lines[j]}")
                            else:
                                print(f"      {lines[j]}")
                        break

if __name__ == "__main__":
    search_for_questions()