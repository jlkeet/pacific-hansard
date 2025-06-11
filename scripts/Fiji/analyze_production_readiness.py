#!/usr/bin/env python3
"""
Analyze production readiness of processed Fiji hansards (2023-2024)
"""
import os
import re
from collections import defaultdict
from datetime import datetime
import json

def analyze_production_readiness():
    """Analyze the production readiness of processed hansards"""
    
    collections_base = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"
    
    if not os.path.exists(collections_base):
        print(f"Collections directory not found: {collections_base}")
        return
    
    # Data structures for analysis
    stats = {
        'total_files': 0,
        'files_by_year': defaultdict(int),
        'files_by_month': defaultdict(int),
        'parts_distribution': [],
        'speakers_per_file': [],
        'empty_parts': 0,
        'empty_metadata': 0,
        'missing_speakers': 0,
        'file_sizes': [],
        'part_sizes': [],
        'questions_found': 0,
        'quality_issues': [],
        'speaker_patterns': defaultdict(int),
        'all_speakers': set(),
        'dates_covered': set(),
        'missing_dates': [],
        'duplicate_speakers': []
    }
    
    print("Production Readiness Analysis - Fiji Hansards 2023-2024")
    print("=" * 70)
    
    # Walk through collections
    for year in os.listdir(collections_base):
        if year not in ['2023', '2024']:
            continue
            
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
                
                # Analyze this hansard
                stats['total_files'] += 1
                stats['files_by_year'][year] += 1
                stats['files_by_month'][f"{year}-{month}"] += 1
                
                date_str = f"{day} {month} {year}"
                stats['dates_covered'].add(date_str)
                
                # Count parts and analyze content
                parts = 0
                file_speakers = set()
                hansard_issues = []
                total_file_size = 0
                
                files_in_day = os.listdir(day_path)
                
                for file in files_in_day:
                    file_path = os.path.join(day_path, file)
                    
                    if file.startswith('part') and file.endswith('.html'):
                        parts += 1
                        
                        # Check file size
                        file_size = os.path.getsize(file_path)
                        stats['part_sizes'].append(file_size)
                        total_file_size += file_size
                        
                        # Check if empty
                        if file_size < 100:
                            stats['empty_parts'] += 1
                            hansard_issues.append(f"Empty part: {file}")
                        
                        # Analyze content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Check for proper HTML structure
                            if not content.strip().startswith('<!DOCTYPE html>'):
                                hansard_issues.append(f"Missing DOCTYPE in {file}")
                            
                            # Look for speaker patterns
                            speaker_patterns = [
                                r'HON\.\s+[A-Z]',
                                r'MR\.?\s+SPEAKER',
                                r'MADAM\s+SPEAKER',
                                r'DEPUTY\s+SPEAKER'
                            ]
                            
                            for pattern in speaker_patterns:
                                if re.search(pattern, content):
                                    stats['speaker_patterns'][pattern] += 1
                    
                    elif file.endswith('_metadata.txt'):
                        # Analyze metadata
                        with open(file_path, 'r', encoding='utf-8') as f:
                            metadata = f.read()
                            
                            if len(metadata.strip()) < 20:
                                stats['empty_metadata'] += 1
                                hansard_issues.append(f"Empty metadata: {file}")
                            
                            # Extract speakers
                            speaker_matches = re.findall(r'Speaker \d+: (.+)', metadata)
                            for speaker in speaker_matches:
                                if speaker != "No speakers identified":
                                    file_speakers.add(speaker)
                                    stats['all_speakers'].add(speaker)
                
                # Record statistics
                stats['parts_distribution'].append(parts)
                stats['speakers_per_file'].append(len(file_speakers))
                stats['file_sizes'].append(total_file_size)
                
                if len(file_speakers) == 0:
                    stats['missing_speakers'] += 1
                    hansard_issues.append("No speakers extracted")
                
                # Check for duplicate speakers (different formats of same name)
                speaker_list = list(file_speakers)
                for i in range(len(speaker_list)):
                    for j in range(i+1, len(speaker_list)):
                        if speaker_list[i].replace('.', '').replace(' ', '') == \
                           speaker_list[j].replace('.', '').replace(' ', ''):
                            stats['duplicate_speakers'].append((speaker_list[i], speaker_list[j]))
                
                if hansard_issues:
                    stats['quality_issues'].append({
                        'date': date_str,
                        'issues': hansard_issues
                    })
    
    # Analysis Results
    print("\n1. COVERAGE ANALYSIS")
    print("-" * 40)
    print(f"Total files processed: {stats['total_files']}")
    print(f"Date range: {min(stats['dates_covered'])} to {max(stats['dates_covered'])}")
    print(f"\nFiles by year:")
    for year in sorted(stats['files_by_year'].keys()):
        print(f"  {year}: {stats['files_by_year'][year]} files")
    
    print(f"\n2. CONTENT QUALITY")
    print("-" * 40)
    avg_parts = sum(stats['parts_distribution']) / len(stats['parts_distribution']) if stats['parts_distribution'] else 0
    print(f"Average parts per hansard: {avg_parts:.1f}")
    print(f"Min/Max parts: {min(stats['parts_distribution'])}/{max(stats['parts_distribution'])}")
    
    avg_file_size = sum(stats['file_sizes']) / len(stats['file_sizes']) if stats['file_sizes'] else 0
    print(f"\nAverage file size: {avg_file_size/1024:.1f} KB")
    print(f"Total content size: {sum(stats['file_sizes'])/1024/1024:.1f} MB")
    
    print(f"\n3. SPEAKER EXTRACTION")
    print("-" * 40)
    print(f"Total unique speakers: {len(stats['all_speakers'])}")
    avg_speakers = sum(stats['speakers_per_file']) / len(stats['speakers_per_file']) if stats['speakers_per_file'] else 0
    print(f"Average speakers per file: {avg_speakers:.1f}")
    print(f"Files with no speakers: {stats['missing_speakers']} ({stats['missing_speakers']/stats['total_files']*100:.1f}%)")
    
    print(f"\n4. DATA QUALITY ISSUES")
    print("-" * 40)
    print(f"Empty parts found: {stats['empty_parts']}")
    print(f"Empty metadata files: {stats['empty_metadata']}")
    print(f"Files with quality issues: {len(stats['quality_issues'])}")
    
    if stats['duplicate_speakers']:
        print(f"\nDuplicate speaker names found: {len(stats['duplicate_speakers'])}")
        for dup in stats['duplicate_speakers'][:5]:
            print(f"  - '{dup[0]}' vs '{dup[1]}'")
    
    print(f"\n5. PRODUCTION READINESS SCORE")
    print("-" * 40)
    
    # Calculate readiness score
    scores = {
        'coverage': min(100, (stats['total_files'] / 50) * 100),  # Assuming 50 files is good coverage
        'content_quality': max(0, 100 - (stats['empty_parts'] + stats['empty_metadata']) * 5),
        'speaker_extraction': max(0, 100 - (stats['missing_speakers'] / stats['total_files'] * 100)),
        'data_consistency': max(0, 100 - len(stats['quality_issues']) * 2)
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
    for metric, score in scores.items():
        status = "✓" if score >= 80 else "⚠" if score >= 60 else "✗"
        print(f"{status} {metric.replace('_', ' ').title()}: {score:.0f}%")
    
    print(f"\nOverall Production Readiness: {overall_score:.0f}%")
    
    if overall_score >= 80:
        print("\n✓ FILES ARE PRODUCTION READY")
    elif overall_score >= 60:
        print("\n⚠ FILES NEED MINOR IMPROVEMENTS")
    else:
        print("\n✗ FILES NEED SIGNIFICANT WORK")
    
    # Recommendations
    print(f"\n6. RECOMMENDATIONS")
    print("-" * 40)
    
    recommendations = []
    
    if stats['missing_speakers'] > stats['total_files'] * 0.1:
        recommendations.append("- Improve speaker extraction patterns")
    
    if stats['empty_parts'] > 0:
        recommendations.append("- Remove or fix empty part files")
    
    if stats['duplicate_speakers']:
        recommendations.append("- Standardize speaker name formats")
    
    if len(stats['all_speakers']) < 50:
        recommendations.append("- Verify speaker extraction is capturing all speakers")
    
    if not recommendations:
        recommendations.append("- Files are ready for production indexing")
        recommendations.append("- Consider adding question extraction for 2023-2024 files")
    
    for rec in recommendations:
        print(rec)
    
    # Save detailed report
    report = {
        'analysis_date': datetime.now().isoformat(),
        'stats': dict(stats),
        'scores': scores,
        'overall_score': overall_score,
        'recommendations': recommendations
    }
    
    with open('production_readiness_report.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print("\n[Detailed report saved to production_readiness_report.json]")

if __name__ == "__main__":
    analyze_production_readiness()