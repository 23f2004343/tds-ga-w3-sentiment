import sys
import json
import fitz

def extract_boxes(pdf_path, search_term):
    doc = fitz.open(pdf_path)
    boxes = []
    
    for page in doc:
        # search_for returns a list of Rect objects
        rects = page.search_for(search_term)
        for rect in rects:
            # PyMuPDF Rect has structure (x0, y0, x1, y1)
            # converting to integers as requested
            box = [int(rect.x0), int(rect.y0), int(rect.x1), int(rect.y1)]
            boxes.append(box)
            
    print(json.dumps(boxes))

if __name__ == "__main__":
    extract_boxes("bounding_box_task.pdf", "text")
