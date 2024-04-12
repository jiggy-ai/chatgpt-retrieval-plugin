import pytesseract
from pdf2image import convert_from_path
from PIL import Image
from loguru import logger

# Function to perform OCR on all pages of a PDF file
def pdf_to_text(pdf_path):
    # Path to the tesseract executable
    pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"  

    # Convert PDF to images (one image per page)
    images = convert_from_path(pdf_path)

    text = ''
    for i, image in enumerate(images):
        # Perform OCR using tesseract
        page_text = pytesseract.image_to_string(image)
        text += page_text
        logger.info(f"Processed page {i+1}")        

    return text
