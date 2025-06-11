from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import StringIO

def pdf_to_html(pdf_path, html_path):
    """
    Convert a PDF file to HTML format.
    
    Args:
        pdf_path: Path to the input PDF file
        html_path: Path where the HTML output will be saved
    
    Returns:
        The path to the created HTML file
    """
    output_string = StringIO()
    with open(pdf_path, 'rb') as fin:
        extract_text_to_fp(fin, output_string, laparams=LAParams(), output_type='html', codec=None)
    
    with open(html_path, 'w', encoding='utf-8') as fout:
        fout.write(output_string.getvalue())
    
    return html_path

if __name__ == "__main__":
    # When run directly, process files specified as command line arguments
    import sys
    import os
    
    if len(sys.argv) > 1:
        # Process all PDF files provided as arguments
        for pdf_file in sys.argv[1:]:
            if not pdf_file.lower().endswith('.pdf'):
                print(f"Skipping {pdf_file} - not a PDF file")
                continue
                
            # Generate HTML filename from PDF filename
            html_file = os.path.splitext(pdf_file)[0] + '.html'
            print(f"Converting {pdf_file} to {html_file}...")
            pdf_to_html(pdf_file, html_file)
    else:
        print("Usage: python CI_gpt_hansard.py <pdf_file1> [pdf_file2] [...]")
        print("No files specified, no action taken.")