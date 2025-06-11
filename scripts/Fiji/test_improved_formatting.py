#!/usr/bin/env python3
"""Test the improved formatting on a single file"""

from improve_fiji_formatting import enhance_fiji_html
import os

# Test file
test_file = "/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji/Hansard_10th-February-2021/part10_questions/oral_question_1.html"

# Read the original
with open(test_file, 'r', encoding='utf-8') as f:
    original_content = f.read()

# Apply formatting
enhanced_content = enhance_fiji_html(original_content)

# Save to a test output file
output_file = test_file.replace('.html', '_improved.html')
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(enhanced_content)

print(f"Original file: {test_file}")
print(f"Improved version saved to: {output_file}")
print("\nYou can open both files in a browser to compare the formatting.")

# Also create a comparison file showing both
comparison_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Formatting Comparison</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ display: flex; gap: 20px; }}
        .column {{ flex: 1; border: 1px solid #ccc; padding: 20px; overflow: auto; max-height: 90vh; }}
        h2 {{ margin-top: 0; }}
    </style>
</head>
<body>
    <h1>Fiji Hansard Formatting Comparison</h1>
    <div class="container">
        <div class="column">
            <h2>Original</h2>
            <iframe src="{os.path.basename(test_file)}" style="width: 100%; height: 800px; border: none;"></iframe>
        </div>
        <div class="column">
            <h2>Improved</h2>
            <iframe src="{os.path.basename(output_file)}" style="width: 100%; height: 800px; border: none;"></iframe>
        </div>
    </div>
</body>
</html>
"""

comparison_file = os.path.join(os.path.dirname(test_file), 'formatting_comparison.html')
with open(comparison_file, 'w', encoding='utf-8') as f:
    f.write(comparison_html)

print(f"\nComparison page saved to: {comparison_file}")