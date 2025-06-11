#!/usr/bin/env python3
"""
Analyze Fiji hansard processing results
"""
import os
import re
from collections import defaultdict

def analyze_fiji_hansards():
    """Analyze processed Fiji hansards"""
    
    collections_base = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"
    
    if not os.path.exists(collections_base):
        print(f"Collections directory not found: {collections_base}")
        return
    
    stats = {
        'total_files': 0,
        'total_parts': 0,
        'total_questions': 0,
        'oral_questions': 0,
        'written_questions': 0,
        'dates': set(),
        'speakers': set(),
        'files_by_year': defaultdict(int),
        'files_by_month': defaultdict(int),
        'parts_per_file': []
    }
    
    print("Analyzing Fiji Hansard Results")
    print("=" * 50)
    
    # Walk through the collections
    for year in os.listdir(collections_base):
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
                
                # This is a hansard directory
                stats['total_files'] += 1
                stats['files_by_year'][year] += 1
                stats['files_by_month'][f"{year}-{month}"] += 1
                date_str = f"{day} {month} {year}"
                stats['dates'].add(date_str)
                
                # Count parts and questions
                parts = 0
                files_in_day = os.listdir(day_path)
                
                for file in files_in_day:
                    if file.startswith('part') and file.endswith('.html'):
                        parts += 1
                        stats['total_parts'] += 1
                    elif 'oral_question' in file and file.endswith('.html'):
                        stats['oral_questions'] += 1
                        stats['total_questions'] += 1
                    elif 'written_question' in file and file.endswith('.html'):
                        stats['written_questions'] += 1
                        stats['total_questions'] += 1
                    elif file.endswith('_metadata.txt'):
                        # Read metadata to extract speakers
                        metadata_path = os.path.join(day_path, file)
                        try:
                            with open(metadata_path, 'r') as f:
                                content = f.read()
                                # Extract speakers
                                speaker_matches = re.findall(r'Speaker \d+: (.+)', content)
                                for speaker in speaker_matches:
                                    if speaker != "No speakers identified":
                                        stats['speakers'].add(speaker)
                        except:
                            pass
                
                stats['parts_per_file'].append(parts)
                
                print(f"\n{date_str}:")
                print(f"  Parts: {parts}")
                
                # Check for questions
                q_count = sum(1 for f in files_in_day if 'question' in f and f.endswith('.html'))
                if q_count > 0:
                    print(f"  Questions: {q_count}")
    
    # Summary statistics
    print("\n" + "=" * 50)
    print("SUMMARY STATISTICS")
    print("=" * 50)
    print(f"Total hansards processed: {stats['total_files']}")
    print(f"Total parts created: {stats['total_parts']}")
    print(f"Average parts per hansard: {stats['total_parts'] / stats['total_files'] if stats['total_files'] > 0 else 0:.1f}")
    print(f"\nQuestions:")
    print(f"  Total questions: {stats['total_questions']}")
    print(f"  Oral questions: {stats['oral_questions']}")
    print(f"  Written questions: {stats['written_questions']}")
    
    print(f"\nFiles by year:")
    for year in sorted(stats['files_by_year'].keys()):
        print(f"  {year}: {stats['files_by_year'][year]} files")
    
    print(f"\nUnique speakers found: {len(stats['speakers'])}")
    if len(stats['speakers']) == 0:
        print("  Note: Speaker extraction may need improvement")
    else:
        print("  Sample speakers:")
        for i, speaker in enumerate(sorted(list(stats['speakers']))[:10], 1):
            print(f"    {i}. {speaker}")
    
    # Check speaker extraction issue
    print("\n" + "=" * 50)
    print("SPEAKER EXTRACTION ANALYSIS")
    print("=" * 50)
    
    # Let's check one file to see why speakers aren't being extracted
    sample_file = None
    for year in os.listdir(collections_base):
        year_path = os.path.join(collections_base, year)
        if os.path.isdir(year_path):
            for month in os.listdir(year_path):
                month_path = os.path.join(year_path, month)
                if os.path.isdir(month_path):
                    for day in os.listdir(month_path):
                        day_path = os.path.join(year_path, month, day)
                        if os.path.isdir(day_path):
                            for file in os.listdir(day_path):
                                if file == 'part9.html':  # We know this has speakers
                                    sample_file = os.path.join(day_path, file)
                                    break
    
    if sample_file:
        print(f"Checking sample file: {sample_file}")
        with open(sample_file, 'r') as f:
            content = f.read()
            # Look for speaker patterns
            patterns = [
                r'HON\.\s+[A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*\s*[:-]',
                r'MR\s+SPEAKER\s*[:-]',
                r'HON\.\s+[A-Z]\.?[A-Z]\.?\s+[A-Z][A-Z\s\'-]+\s*[:-]'
            ]
            
            print("\nSpeakers found in content:")
            found_any = False
            for pattern in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    found_any = True
                    for match in matches[:5]:  # Show first 5
                        print(f"  - {match}")
            
            if not found_any:
                print("  No speakers found with current patterns")
                # Show a snippet to understand the format
                print("\nContent snippet:")
                print(content[1000:1500])

if __name__ == "__main__":
    analyze_fiji_hansards()