#!/usr/bin/env python3

import os
import glob
import subprocess
import sys

def find_png_pdfs():
    """Find all PNG PDF files"""
    pdf_files = glob.glob("./scripts/PNG/*.pdf")
    return sorted(pdf_files)

def run_converter(pdf_path):
    """Run the PNG converter on a single PDF"""
    try:
        print(f"Processing: {pdf_path}")
        result = subprocess.run([
            sys.executable, 
            "scripts/PNG/PNG-hansard-converter-integrated.py",
            pdf_path
        ], capture_output=True, text=True, check=True)
        
        print(f"✓ Successfully processed {pdf_path}")
        if result.stdout:
            print(f"Output: {result.stdout.strip()}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error processing {pdf_path}: {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def main():
    print("=== PNG PDF Batch Reprocessing ===")
    print("This will regenerate HTML files with fixed titles\n")
    
    # Find all PNG PDFs
    pdf_files = find_png_pdfs()
    
    if not pdf_files:
        print("No PNG PDF files found in scripts/PNG/")
        return
    
    print(f"Found {len(pdf_files)} PNG PDF files:")
    for pdf in pdf_files:
        print(f"  - {pdf}")
    
    print(f"\nProcessing {len(pdf_files)} files...")
    
    success_count = 0
    failed_count = 0
    
    for pdf_path in pdf_files:
        if run_converter(pdf_path):
            success_count += 1
        else:
            failed_count += 1
        print()  # Empty line between files
    
    print("=== Processing Complete ===")
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {failed_count}")
    print(f"Total: {len(pdf_files)}")
    
    if success_count > 0:
        print(f"\n{success_count} PDF files have been reprocessed with fixed titles.")
        print("HTML files in collections/ have been updated.")
        print("Next: Clear PNG tracking again and the indexing will pick up the new titles.")

if __name__ == "__main__":
    main()