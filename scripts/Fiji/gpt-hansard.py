from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams
from io import StringIO

def pdf_to_html(pdf_path, html_path):
    output_string = StringIO()
    with open(pdf_path, 'rb') as fin:
        extract_text_to_fp(fin, output_string, laparams=LAParams(), output_type='html', codec=None)
    
    with open(html_path, 'w', encoding='utf-8') as fout:
        fout.write(output_string.getvalue())

pdf_to_html('Final-DH-Tuesday-9th-February-2021v2.pdf', 'Final-DH-Tuesday-9th-February-2021v2.html')