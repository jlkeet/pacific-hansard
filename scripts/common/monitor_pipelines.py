#!/usr/bin/env python3
"""
Pipeline monitoring dashboard for Pacific Hansard data processing.
Analyzes logs and provides status reports.
"""

import os
import json
import glob
from datetime import datetime, timedelta
import argparse
from collections import defaultdict


def get_log_files(log_dir, days_back=7):
    """Get log files from the past N days"""
    cutoff_date = datetime.now() - timedelta(days=days_back)
    log_files = {
        'errors': [],
        'stats': [],
        'general': []
    }
    
    # Get error logs
    for error_file in glob.glob(os.path.join(log_dir, 'error_*.json')):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(error_file))
            if mtime >= cutoff_date:
                log_files['errors'].append(error_file)
        except:
            pass
    
    # Get pipeline stats
    for stats_file in glob.glob(os.path.join(log_dir, 'pipeline_stats_*.json')):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(stats_file))
            if mtime >= cutoff_date:
                log_files['stats'].append(stats_file)
        except:
            pass
    
    # Get general logs
    for log_file in ['pipeline_errors.log', 'pipeline_general.log']:
        full_path = os.path.join(log_dir, log_file)
        if os.path.exists(full_path):
            log_files['general'].append(full_path)
    
    return log_files


def analyze_errors(error_files):
    """Analyze error patterns"""
    error_summary = defaultdict(lambda: {'count': 0, 'files': []})
    
    for error_file in error_files:
        try:
            with open(error_file, 'r') as f:
                error_data = json.load(f)
                
            error_type = error_data.get('error_type', 'Unknown')
            error_summary[error_type]['count'] += 1
            error_summary[error_type]['files'].append({
                'file': error_file,
                'message': error_data.get('error_message', ''),
                'timestamp': error_data.get('timestamp', ''),
                'context': error_data.get('context', {})
            })
        except Exception as e:
            print(f"Error reading {error_file}: {e}")
    
    return dict(error_summary)


def analyze_pipeline_stats(stats_files):
    """Analyze pipeline performance statistics"""
    pipeline_summary = defaultdict(lambda: {
        'runs': 0,
        'total_processed': 0,
        'total_failed': 0,
        'total_skipped': 0,
        'avg_duration': 0,
        'success_rate': 0
    })
    
    for stats_file in stats_files:
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            # Extract pipeline name from filename
            filename = os.path.basename(stats_file)
            parts = filename.split('_')
            if len(parts) >= 3:
                pipeline_name = parts[2]
            else:
                pipeline_name = 'unknown'
            
            summary = pipeline_summary[pipeline_name]
            summary['runs'] += 1
            summary['total_processed'] += stats.get('processed', 0)
            summary['total_failed'] += stats.get('failed', 0)
            summary['total_skipped'] += stats.get('skipped', 0)
            
            # Update average duration
            duration = stats.get('duration_seconds', 0)
            prev_avg = summary['avg_duration']
            summary['avg_duration'] = (prev_avg * (summary['runs'] - 1) + duration) / summary['runs']
            
        except Exception as e:
            print(f"Error reading {stats_file}: {e}")
    
    # Calculate success rates
    for pipeline, summary in pipeline_summary.items():
        total = summary['total_processed'] + summary['total_failed']
        if total > 0:
            summary['success_rate'] = (summary['total_processed'] / total) * 100
    
    return dict(pipeline_summary)


def print_report(error_summary, pipeline_summary, days_back):
    """Print formatted monitoring report"""
    print("\n" + "="*60)
    print(f"PACIFIC HANSARD PIPELINE MONITORING REPORT")
    print(f"Report Period: Last {days_back} days")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Pipeline Summary
    print("\n## PIPELINE PERFORMANCE ##")
    print("-"*60)
    
    if pipeline_summary:
        print(f"{'Pipeline':<20} {'Runs':<6} {'Success Rate':<12} {'Avg Duration':<12} {'Processed':<10} {'Failed':<8}")
        print("-"*60)
        
        for pipeline, stats in sorted(pipeline_summary.items()):
            print(f"{pipeline:<20} {stats['runs']:<6} {stats['success_rate']:>10.1f}% "
                  f"{stats['avg_duration']:>10.1f}s {stats['total_processed']:<10} {stats['total_failed']:<8}")
    else:
        print("No pipeline runs found in the specified period.")
    
    # Error Summary
    print("\n## ERROR SUMMARY ##")
    print("-"*60)
    
    if error_summary:
        print(f"{'Error Type':<30} {'Count':<10} {'Recent Examples'}")
        print("-"*60)
        
        for error_type, info in sorted(error_summary.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"{error_type:<30} {info['count']:<10}")
            
            # Show recent examples
            recent = sorted(info['files'], key=lambda x: x['timestamp'], reverse=True)[:2]
            for example in recent:
                print(f"  - {example['timestamp']}: {example['message'][:50]}...")
    else:
        print("No errors found in the specified period.")
    
    # Recommendations
    print("\n## RECOMMENDATIONS ##")
    print("-"*60)
    
    recommendations = []
    
    # Check for high error rates
    for pipeline, stats in pipeline_summary.items():
        if stats['success_rate'] < 90 and stats['runs'] > 0:
            recommendations.append(
                f"- Pipeline '{pipeline}' has low success rate ({stats['success_rate']:.1f}%). "
                f"Review error logs for common issues."
            )
    
    # Check for specific error types
    for error_type, info in error_summary.items():
        if info['count'] > 5:
            if 'Connection' in error_type:
                recommendations.append(
                    f"- Multiple {error_type} errors detected. Check database/Solr connectivity."
                )
            elif 'Validation' in error_type:
                recommendations.append(
                    f"- Data validation errors occurring. Review input data quality."
                )
    
    if recommendations:
        for rec in recommendations:
            print(rec)
    else:
        print("No specific recommendations. Pipelines running smoothly.")
    
    print("\n" + "="*60 + "\n")


def export_json_report(error_summary, pipeline_summary, output_file):
    """Export report as JSON"""
    report = {
        'generated_at': datetime.now().isoformat(),
        'pipeline_summary': pipeline_summary,
        'error_summary': error_summary
    }
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"JSON report exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Monitor Pacific Hansard data pipelines')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--log-dir', default='../logs', help='Log directory path')
    parser.add_argument('--export-json', help='Export report as JSON to specified file')
    
    args = parser.parse_args()
    
    # Resolve log directory path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(script_dir, args.log_dir)
    
    if not os.path.exists(log_dir):
        print(f"Log directory not found: {log_dir}")
        print("Have the pipelines been run yet?")
        return
    
    # Get log files
    log_files = get_log_files(log_dir, args.days)
    
    print(f"Found {len(log_files['errors'])} error logs and {len(log_files['stats'])} pipeline stats")
    
    # Analyze data
    error_summary = analyze_errors(log_files['errors'])
    pipeline_summary = analyze_pipeline_stats(log_files['stats'])
    
    # Print report
    print_report(error_summary, pipeline_summary, args.days)
    
    # Export JSON if requested
    if args.export_json:
        export_json_report(error_summary, pipeline_summary, args.export_json)


if __name__ == "__main__":
    main()