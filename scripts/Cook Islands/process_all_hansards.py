#!/usr/bin/env python3
"""
Process all Cook Islands hansards and generate summary statistics
"""
import os
import glob
import subprocess
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hansard_processing.log'),
        logging.StreamHandler()
    ]
)

def process_all_hansards():
    """Process all HTML hansards in the html_hansards directory"""
    html_files = glob.glob('html_hansards/*.html')
    
    if not html_files:
        logging.error("No HTML files found in html_hansards directory")
        return
    
    logging.info(f"Found {len(html_files)} hansard files to process")
    
    results = []
    
    for i, html_file in enumerate(html_files, 1):
        logging.info(f"Processing {i}/{len(html_files)}: {os.path.basename(html_file)}")
        
        try:
            # Run the converter
            result = subprocess.run(
                ['python3', 'CI-hansard-converter.py', html_file],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logging.error(f"Error processing {html_file}: {result.stderr}")
                continue
            
            # Find the created directory (last line of output usually contains it)
            output_lines = result.stdout.strip().split('\n')
            for line in reversed(output_lines):
                if 'Processing' in line and '->' in line:
                    output_dir = line.split('->')[-1].strip()
                    break
            else:
                # Try to find it by pattern
                base_name = os.path.splitext(os.path.basename(html_file))[0]
                pattern = f"{base_name}.html_*"
                dirs = glob.glob(pattern)
                if dirs:
                    output_dir = max(dirs)  # Get the most recent
                else:
                    logging.error(f"Could not find output directory for {html_file}")
                    continue
            
            # Read validation report
            validation_file = os.path.join(output_dir, 'validation_report.json')
            if os.path.exists(validation_file):
                with open(validation_file, 'r') as f:
                    validation_data = json.load(f)
                
                # Read metadata
                metadata_file = os.path.join(output_dir, 'metadata.json')
                metadata = {}
                if os.path.exists(metadata_file):
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                
                result_data = {
                    'file': os.path.basename(html_file),
                    'output_dir': output_dir,
                    'date': metadata.get('date', 'Unknown'),
                    'parliament': metadata.get('parliament', 'Unknown'),
                    'total_parts': validation_data['total_parts'],
                    'parts_with_speakers': validation_data['parts_with_speakers'],
                    'speaker_coverage': f"{validation_data['parts_with_speakers']}/{validation_data['total_parts']} ({validation_data['parts_with_speakers']/validation_data['total_parts']*100:.1f}%)",
                    'unique_speakers': len(validation_data['total_speakers']),
                    'questions_extracted': validation_data['questions_extracted'],
                    'issues': len(validation_data['issues'])
                }
                
                results.append(result_data)
                logging.info(f"Successfully processed: {result_data['unique_speakers']} speakers, {result_data['questions_extracted']} questions")
            
        except Exception as e:
            logging.error(f"Exception processing {html_file}: {str(e)}")
            continue
    
    # Generate summary report
    generate_summary_report(results)
    
    return results

def generate_summary_report(results):
    """Generate a summary report of all processing results"""
    
    if not results:
        logging.error("No results to summarize")
        return
    
    # Calculate aggregate statistics
    total_files = len(results)
    total_speakers = sum(r['unique_speakers'] for r in results)
    total_questions = sum(r['questions_extracted'] for r in results)
    avg_speakers = total_speakers / total_files if total_files > 0 else 0
    avg_questions = total_questions / total_files if total_files > 0 else 0
    
    # Files with questions
    files_with_questions = sum(1 for r in results if r['questions_extracted'] > 0)
    
    # Modern vs older hansards
    modern_hansards = [r for r in results if 'DAY-' in r['file']]
    older_hansards = [r for r in results if 'DAY-' not in r['file']]
    
    report = f"""
# Cook Islands Hansard Processing Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overall Statistics
- Total hansards processed: {total_files}
- Total unique speakers identified: {total_speakers}
- Total questions extracted: {total_questions}
- Average speakers per hansard: {avg_speakers:.1f}
- Average questions per hansard: {avg_questions:.1f}
- Hansards with questions: {files_with_questions}/{total_files} ({files_with_questions/total_files*100:.1f}%)

## Format Analysis
- Modern format (DAY-XX): {len(modern_hansards)} files
- Older format: {len(older_hansards)} files
"""

    if modern_hansards:
        modern_questions = sum(r['questions_extracted'] for r in modern_hansards)
        modern_speakers = sum(r['unique_speakers'] for r in modern_hansards)
        report += f"""
### Modern Format Performance:
- Average questions: {modern_questions/len(modern_hansards):.1f}
- Average speakers: {modern_speakers/len(modern_hansards):.1f}
"""

    if older_hansards:
        older_questions = sum(r['questions_extracted'] for r in older_hansards)
        older_speakers = sum(r['unique_speakers'] for r in older_hansards)
        report += f"""
### Older Format Performance:
- Average questions: {older_questions/len(older_hansards):.1f}
- Average speakers: {older_speakers/len(older_hansards):.1f}
"""

    # Add detailed results table
    report += """
## Detailed Results by File

| File | Date | Parliament | Speakers | Questions | Coverage |
|------|------|------------|----------|-----------|----------|
"""
    
    for r in sorted(results, key=lambda x: x['file']):
        report += f"| {r['file']} | {r['date']} | {r['parliament']} | {r['unique_speakers']} | {r['questions_extracted']} | {r['speaker_coverage']} |\n"
    
    # Identify best and worst performing files
    best_speakers = max(results, key=lambda x: x['unique_speakers'])
    best_questions = max(results, key=lambda x: x['questions_extracted'])
    worst_speakers = min(results, key=lambda x: x['unique_speakers'])
    
    report += f"""
## Notable Results
- Most speakers identified: {best_speakers['file']} ({best_speakers['unique_speakers']} speakers)
- Most questions extracted: {best_questions['file']} ({best_questions['questions_extracted']} questions)
- Fewest speakers identified: {worst_speakers['file']} ({worst_speakers['unique_speakers']} speakers)
"""
    
    # Save report
    report_file = f"processing_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    logging.info(f"Summary report saved to {report_file}")
    
    # Also save raw results as JSON
    json_file = f"processing_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logging.info(f"Raw results saved to {json_file}")
    
    # Print summary to console
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Processed: {total_files} hansards")
    print(f"Total speakers: {total_speakers}")
    print(f"Total questions: {total_questions}")
    print(f"Reports saved: {report_file}, {json_file}")
    print("="*60)

if __name__ == "__main__":
    process_all_hansards()