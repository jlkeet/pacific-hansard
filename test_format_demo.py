#!/usr/bin/env python3
import sys
sys.path.append('/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji')
from improve_fiji_formatting import enhance_fiji_html

# Read a sample file
test_file = "/Users/jacksonkeet/Pacific Hansard Development/scripts/Fiji/Hansard_10th-February-2021/part10_questions/oral_question_1.html"

with open(test_file, 'r', encoding='utf-8') as f:
    original = f.read()

# Process it
enhanced = enhance_fiji_html(original)

# Save to a demo file
with open("fiji_format_demo.html", 'w', encoding='utf-8') as f:
    f.write(enhanced)

print("Demo file created: fiji_format_demo.html")
print("\nFirst 2000 characters of improved HTML:")
print(enhanced[:2000])