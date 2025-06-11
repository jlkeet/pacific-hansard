import pytesseract
from pdf2image import convert_from_path
import html

# Convert PDF pages to images
pdf_path = 'H-11-20230314-M06-D01.pdf'
pages = convert_from_path(pdf_path)

# Use pytesseract to do OCR on each page
text_pages = [pytesseract.image_to_string(page) for page in pages]

# Combine text from all pages into a single HTML document
html_content = "<html>\n<head>\n<title>Transcribed PDF</title>\n</head>\n<body>\n"
for page_number, text in enumerate(text_pages, start=1):
    escaped_text = html.escape(text).replace('\n', '<br>')
    html_content += f"<h2>Page {page_number}</h2>\n<p>{escaped_text}</p>\n"

html_content += "</body>\n</html>"

# Save HTML content to a file
output_html_path = 'H-11-20230314-M06-D01.html'
with open(output_html_path, 'w') as html_file:
    html_file.write(html_content)

print(f"HTML file saved to {output_html_path}")