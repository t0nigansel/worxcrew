import os
from pdfminer.high_level import extract_text
from PyPDF2 import PdfReader

TEMPLATE_PATH = 'agents/cv/template/CV_template.pdf'
CV_PATH = 'agents/cv/result/cv.pdf'

def extract_pdf_features(pdf_path):
    # Extract text
    text = extract_text(pdf_path)
    # Extract metadata and page layout info
    reader = PdfReader(pdf_path)
    metadata = reader.metadata
    num_pages = len(reader.pages)
    # Optionally, extract section headers (simple heuristic: lines in ALL CAPS or bold)
    headers = [line for line in text.split('\n') if line.isupper() and len(line) > 2]
    return {
        'text': text,
        'headers': headers,
        'metadata': metadata,
        'num_pages': num_pages
    }

def compare_features(template_features, cv_features):
    differences = []
    # Compare headers
    template_headers = set(template_features['headers'])
    cv_headers = set(cv_features['headers'])
    missing_headers = template_headers - cv_headers
    extra_headers = cv_headers - template_headers
    if missing_headers:
        differences.append(f"Missing headers in CV: {missing_headers}")
    if extra_headers:
        differences.append(f"Extra headers in CV: {extra_headers}")
    # Compare number of pages
    if template_features['num_pages'] != cv_features['num_pages']:
        differences.append(f"Page count differs: Template={template_features['num_pages']}, CV={cv_features['num_pages']}")
    # Compare metadata
    if template_features['metadata'] != cv_features['metadata']:
        differences.append("Metadata differs.")
    # Compare text content (simple diff)
    if template_features['text'] != cv_features['text']:
        differences.append("Text content differs.")
    return differences

def main():
    template_features = extract_pdf_features(TEMPLATE_PATH)
    cv_features = extract_pdf_features(CV_PATH)
    differences = compare_features(template_features, cv_features)
    print("Differences between template and CV:")
    for diff in differences:
        print(diff)

if __name__ == '__main__':
    main()
