#!/usr/bin/env python3
"""
Enhanced PNG PDF to HTML Converter
Combines and improves the existing PNG OCR scripts with preprocessing and fallback methods
"""

import os
import sys
import logging
from datetime import datetime
import argparse

# OCR libraries
import pytesseract
from pdf2image import convert_from_path
import pdfplumber
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import html

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class PNGPDFConverter:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def preprocess_image(self, img):
        """Preprocess image to enhance text readability for OCR"""
        try:
            # Convert PIL image to numpy array for OpenCV
            img_array = np.array(img)
            
            # Convert to grayscale
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array
            
            # Apply Gaussian Blur to reduce noise
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply threshold to binarize the image
            _, threshold_img = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Convert back to PIL Image
            return Image.fromarray(threshold_img)
            
        except Exception as e:
            self.logger.warning(f"Preprocessing failed, using original image: {e}")
            return img
    
    def enhance_image(self, img):
        """Apply additional image enhancements"""
        try:
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.5)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(2.0)
            
            return img
            
        except Exception as e:
            self.logger.warning(f"Enhancement failed, using original image: {e}")
            return img
    
    def extract_text_with_pdfplumber(self, pdf_file):
        """Extract text using pdfplumber (faster, but may miss scanned content)"""
        try:
            self.logger.info("Attempting text extraction with pdfplumber...")
            extracted_text = ""
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text and text.strip():
                        extracted_text += f"Page {page_num + 1}:\n{text}\n\n"
                    else:
                        self.logger.debug(f"No text found on page {page_num + 1} with pdfplumber")
            
            # Check if we got meaningful content
            if len(extracted_text.strip()) > 100:  # Arbitrary threshold
                self.logger.info("Successfully extracted text with pdfplumber")
                return extracted_text
            else:
                self.logger.info("pdfplumber extraction insufficient, will try OCR")
                return None
                
        except Exception as e:
            self.logger.warning(f"pdfplumber extraction failed: {e}")
            return None
    
    def extract_text_with_ocr(self, pdf_file, preprocess=True, enhance=True):
        """Extract text using OCR with optional preprocessing"""
        try:
            self.logger.info("Extracting text with OCR...")
            extracted_text = ""
            
            # Convert PDF to images
            pages = convert_from_path(pdf_file, dpi=300)  # Higher DPI for better OCR
            
            for page_num, page in enumerate(pages):
                self.logger.debug(f"Processing page {page_num + 1} with OCR")
                
                # Apply enhancements if requested
                processed_image = page
                if enhance:
                    processed_image = self.enhance_image(processed_image)
                if preprocess:
                    processed_image = self.preprocess_image(processed_image)
                
                # Perform OCR with custom config for better accuracy
                custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
                text = pytesseract.image_to_string(processed_image, config=custom_config)
                
                if text.strip():
                    extracted_text += f"Page {page_num + 1}:\n{text}\n\n"
                else:
                    self.logger.warning(f"No text extracted from page {page_num + 1}")
            
            return extracted_text
            
        except Exception as e:
            self.logger.error(f"OCR extraction failed: {e}")
            return None
    
    def convert_to_html(self, text_content, title="PNG Hansard Document"):
        """Convert extracted text to properly formatted HTML"""
        if not text_content:
            return None
        
        # Escape HTML characters
        escaped_content = html.escape(text_content)
        
        # Convert line breaks to HTML
        html_content = escaped_content.replace('\n', '<br>\n')
        
        # Wrap in HTML structure
        html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            padding: 20px;
            max-width: 800px;
            margin: 0 auto;
        }}
        h2 {{
            color: #333;
            border-bottom: 2px solid #ccc;
            padding-bottom: 10px;
        }}
        .page-content {{
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="content">
        {html_content}
    </div>
    <footer>
        <p><em>Converted on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </footer>
</body>
</html>"""
        
        return html_document
    
    def convert_pdf(self, pdf_file, output_file=None, method='auto'):
        """
        Convert PDF to HTML using specified method
        
        Args:
            pdf_file: Path to input PDF file
            output_file: Path to output HTML file (optional)
            method: 'auto', 'pdfplumber', 'ocr', or 'ocr_enhanced'
        """
        if not os.path.exists(pdf_file):
            self.logger.error(f"PDF file not found: {pdf_file}")
            return None
        
        self.logger.info(f"Converting {pdf_file} using method: {method}")
        
        # Generate output filename if not provided
        if not output_file:
            base_name = os.path.splitext(os.path.basename(pdf_file))[0]
            output_file = f"{base_name}.html"
        
        extracted_text = None
        
        # Try different extraction methods based on the specified method
        if method == 'auto':
            # Try pdfplumber first, fall back to OCR if needed
            extracted_text = self.extract_text_with_pdfplumber(pdf_file)
            if not extracted_text:
                extracted_text = self.extract_text_with_ocr(pdf_file, preprocess=True, enhance=True)
        
        elif method == 'pdfplumber':
            extracted_text = self.extract_text_with_pdfplumber(pdf_file)
        
        elif method == 'ocr':
            extracted_text = self.extract_text_with_ocr(pdf_file, preprocess=False, enhance=False)
        
        elif method == 'ocr_enhanced':
            extracted_text = self.extract_text_with_ocr(pdf_file, preprocess=True, enhance=True)
        
        else:
            self.logger.error(f"Unknown method: {method}")
            return None
        
        if not extracted_text:
            self.logger.error("Failed to extract text from PDF")
            return None
        
        # Convert to HTML
        title = f"PNG Hansard - {os.path.basename(pdf_file)}"
        html_content = self.convert_to_html(extracted_text, title)
        
        if not html_content:
            self.logger.error("Failed to convert text to HTML")
            return None
        
        # Save HTML file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            self.logger.info(f"Successfully converted {pdf_file} to {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"Failed to save HTML file: {e}")
            return None

def main():
    parser = argparse.ArgumentParser(description='Convert PNG PDF hansards to HTML')
    parser.add_argument('pdf_file', help='Input PDF file path')
    parser.add_argument('-o', '--output', help='Output HTML file path')
    parser.add_argument('-m', '--method', 
                       choices=['auto', 'pdfplumber', 'ocr', 'ocr_enhanced'],
                       default='auto',
                       help='Extraction method (default: auto)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    converter = PNGPDFConverter()
    result = converter.convert_pdf(args.pdf_file, args.output, args.method)
    
    if result:
        print(f"Conversion successful: {result}")
        sys.exit(0)
    else:
        print("Conversion failed")
        sys.exit(1)

if __name__ == "__main__":
    main()