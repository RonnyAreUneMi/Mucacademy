import os
# Force Reload Fix for Function Signature Update
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
from datetime import datetime
from io import BytesIO
import base64


# --- FONTS ---
_fonts_registered = False

def draw_smart_logos(c, lote, x_start, y_start, max_w, max_h, align='center'):
    """
    Draws up to 3 logos (Lote or Defaults) in the given area.
    Smartly distributes them based on count and alignment.
    """
    # 1. Identify Sources
    # We want to force defaults if custom ones are missing, to ensure standard look
    # (Unless user specifically wants NO logo, but typically certificates need them)
    
    logos = []
    
    # helper to check and get path
    def get_path(field, default_name):
        path = None
        # Check custom
        if field:
             if hasattr(field, 'path'): path = field.path
             elif isinstance(field, str): path = field
        
        # Check default if no custom
        if not path or not os.path.exists(path):
            path = os.path.join(settings.BASE_DIR, 'static', 'img', default_name)
        
        if path and os.path.exists(path):
            return path
        return None

    # Load 3 slots
    l1 = get_path(lote.header_logo_1, 'muc.png')
    l2 = get_path(lote.header_logo_2, 'logo-unemi-removebg-preview.png')
    l3 = get_path(lote.header_logo_3, 'feue.png')
    
    # Filter valid ones
    active_logos = [l for l in [l1, l2, l3] if l]
    count = len(active_logos)
    
    if count == 0: return # Nothing to draw
    
    # 2. Calculate Positions
    logo_w = max_h * 1.8 # aspect ratio roughly
    # If logos are squarish, this might be too wide, but standard headers are usually wide.
    # Let's verify per image aspect ratio? For now fixed box is safer.
    
    # Spacing
    # If Center: Start from center of max_w
    # If Right: Start from right edge
    
    # Effective width needed
    gap = 1*cm
    total_w = (count * logo_w) + ((count - 1) * gap)
    
    start_x = x_start
    
    if align == 'center':
        start_x = x_start + (max_w - total_w) / 2
    elif align == 'right':
        start_x = x_start + max_w - total_w
    elif align == 'left':
        start_x = x_start
        
    # Draw
    current_x = start_x
    for path in active_logos:
        try:
            c.drawImage(path, current_x, y_start, width=logo_w, height=max_h, mask='auto', preserveAspectRatio=True)
        except: pass
        current_x += (logo_w + gap)


