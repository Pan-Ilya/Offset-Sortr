import pypdf

def resize_pdf_mm(input_path, output_path, target_width_mm, target_height_mm):
    # Conversion factor: 1 mm = 2.83464567 points
    MM_TO_PT = 72 / 25.4
    
    # Convert target dimensions from mm to points
    target_width_pt = target_width_mm * MM_TO_PT
    target_height_pt = target_height_mm * MM_TO_PT

    reader = pypdf.PdfReader(input_path)
    writer = pypdf.PdfWriter()

    for page in reader.pages:
        # Get current dimensions in points
        current_width = float(page.mediabox.width)
        current_height = float(page.mediabox.height)

        # Calculate scale factors
        scale_x = target_width_pt / current_width
        scale_y = target_height_pt / current_height

        # Scale the page content
        page.scale(scale_x, scale_y)

        # Update page boundaries
        page.mediabox.left = 0
        page.mediabox.bottom = 0
        page.mediabox.right = target_width_pt
        page.mediabox.top = target_height_pt

        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)

# Example Usage: Resize to standard A4 in millimeters (210mm x 297mm)
resize_pdf_mm("TEST/1.pdf", "TEST/2.pdf", 53, 90)