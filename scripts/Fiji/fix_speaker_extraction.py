#!/usr/bin/env python3
"""
Fix speaker extraction for Fiji hansards by re-processing metadata files
"""
import os
import re
import logging
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def normalize_name(name):
    """Remove all spaces and convert to uppercase for comparison"""
    return ''.join(name.split()).upper()

def extract_speakers_improved(content):
    """Extract speakers with improved patterns for Fiji hansards"""
    speakers = []
    seen = set()
    
    # Improved patterns for Fiji format
    patterns = [
        # HON. NAME.- format (with period-dash)
        r'HON\.\s+([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*)\.?-',
        # HON. TITLE.- format 
        r'HON\.\s+((?:PRIME MINISTER|MINISTER|LEADER|ATTORNEY-GENERAL|SPEAKER|DEPUTY SPEAKER)[A-Z\s\'-]*)\.?-',
        # MR/MRS/MS SPEAKER format
        r'(MR\.?|MRS\.?|MS\.?|MADAM)\s+SPEAKER\.?-',
        # Simple NAME.- format at start of paragraph
        r'^\s*([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*)\.?-',
        # HON. with colon (old format)
        r'HON\.\s+([A-Z][A-Z.\s\'-]+(?:\s[A-Z][a-z]+)*):',
    ]
    
    # Split content into lines for better matching
    lines = content.split('\n')
    
    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue
            
        for pattern in patterns:
            matches = re.findall(pattern, line, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    name = ' '.join(m for m in match if m).strip()
                else:
                    name = match.strip()
                
                # Clean up the name
                name = name.rstrip('.-:').strip()
                
                # Handle special cases
                if 'SPEAKER' in name and not any(title in name for title in ['DEPUTY', 'ASSISTANT']):
                    name = 'MR SPEAKER'
                elif name == 'SPEAKER':
                    name = 'MR SPEAKER'
                
                normalized = normalize_name(name)
                
                # Filter out noise
                if (normalized and 
                    normalized not in seen and 
                    len(normalized) > 2 and
                    not normalized.isdigit() and
                    not all(c in '.,!?;:-' for c in normalized)):
                    seen.add(normalized)
                    speakers.append(name)
    
    return sorted(speakers)

def process_hansard_directory(hansard_dir):
    """Process a single hansard directory and update metadata"""
    updated_count = 0
    
    # Find all part HTML files
    part_files = [f for f in os.listdir(hansard_dir) if f.startswith('part') and f.endswith('.html')]
    
    for part_file in part_files:
        part_num = re.search(r'part(\d+)', part_file)
        if not part_num:
            continue
            
        part_num = part_num.group(1)
        html_path = os.path.join(hansard_dir, part_file)
        metadata_path = os.path.join(hansard_dir, f'part{part_num}_metadata.txt')
        
        # Read HTML content
        with open(html_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract speakers
        speakers = extract_speakers_improved(content)
        
        # Update metadata
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write(f"Part {part_num} Speakers:\n")
            if speakers:
                for i, speaker in enumerate(speakers, 1):
                    f.write(f"Speaker {i}: {speaker}\n")
                updated_count += 1
            else:
                f.write("Speaker 1: No speakers identified\n")
            f.write("\n")
    
    return updated_count

def fix_all_speaker_metadata():
    """Fix speaker metadata for all 2023-2024 Fiji hansards"""
    collections_base = "/Users/jacksonkeet/Pacific Hansard Development/collections/Fiji"
    
    total_updated = 0
    total_hansards = 0
    all_speakers = set()
    
    logging.info("Starting speaker extraction fix...")
    
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
                
                logging.info(f"Processing {year}/{month}/{day}")
                updated = process_hansard_directory(day_path)
                total_updated += updated
                total_hansards += 1
                
                # Collect all speakers for summary
                for file in os.listdir(day_path):
                    if file.endswith('_metadata.txt'):
                        with open(os.path.join(day_path, file), 'r') as f:
                            content = f.read()
                            speakers = re.findall(r'Speaker \d+: (.+)', content)
                            for speaker in speakers:
                                if speaker != "No speakers identified":
                                    all_speakers.add(speaker)
    
    logging.info(f"\nSpeaker extraction fix complete!")
    logging.info(f"Total hansards processed: {total_hansards}")
    logging.info(f"Parts with speakers updated: {total_updated}")
    logging.info(f"Total unique speakers found: {len(all_speakers)}")
    
    if all_speakers:
        logging.info("\nSample speakers found:")
        for speaker in sorted(list(all_speakers))[:20]:
            logging.info(f"  - {speaker}")

if __name__ == "__main__":
    fix_all_speaker_metadata()