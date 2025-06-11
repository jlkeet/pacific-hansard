import pdfplumber
import pytesseract
import cv2
import numpy as np

from PIL import Image, ImageEnhance, ImageFilter

# Preprocess image to enhance text readability for OCR
def preprocess_image(img):
    # Convert to grayscale
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    
    # Apply Gaussian Blur to reduce noise
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply threshold to binarize the image
    _, threshold_img = cv2.threshold(blur, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    return Image.fromarray(threshold_img)

# Extract text from a scanned PDF using Tesseract OCR
def extract_text_from_pdf(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        extracted_text = ""
        for page_num, page in enumerate(pdf.pages):
            # Convert the page to an image
            image = page.to_image()
            img = image.original

            # Preprocess the image
            preprocessed_img = preprocess_image(img)

            # Perform OCR on the preprocessed image
            text = pytesseract.image_to_string(preprocessed_img)

            extracted_text += f"Page {page_num + 1}:\n{text}\n\n"
    return extracted_text

# Main workflow
pdf_file = "H-11-20230314-M06-D01.pdf"
extracted_text = extract_text_from_pdf(pdf_file)

# Save the extracted text to a file
with open("test3.txt", "w", encoding="utf-8") as text_file:
    text_file.write(extracted_text)

print("OCR with preprocessing completed and saved to output.txt")