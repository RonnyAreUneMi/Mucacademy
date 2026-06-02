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

from ._helpers import hex2rgb

def _draw_geometric_verification_page(c, certificado, width, height, pri, sec):
    """
    Segunda página: Solo verificación con QR.
    Sin logos, sin nombre. Minimalista para que un empleador escanee.
    """
    lote = certificado.batch

    # --- GEOMETRIC CORNERS (smaller version) ---
    def draw_corner_mini(origin_x, origin_y, rotation, main_col, acc_col):
        c.saveState()
        c.translate(origin_x, origin_y)
        c.rotate(rotation)
        
        c.setFillColor(main_col)
        p1 = c.beginPath()
        p1.moveTo(0, 0)
        p1.lineTo(5.0*cm, 0)
        p1.lineTo(4.0*cm, 1.8*cm)
        p1.lineTo(1.8*cm, 1.8*cm)
        p1.lineTo(0, 5.0*cm)
        p1.close()
        c.drawPath(p1, fill=1, stroke=0)
        
        c.setFillColor(acc_col)
        c.setStrokeColor(white)
        c.setLineWidth(2)
        p2 = c.beginPath()
        p2.moveTo(0, 0)
        p2.lineTo(3.0*cm, 0)
        p2.lineTo(0, 3.0*cm)
        p2.close()
        c.drawPath(p2, fill=1, stroke=1)
        
        c.restoreState()

    draw_corner_mini(0, 0, 0, pri, sec)
    draw_corner_mini(width, height, 180, sec, pri)
    
    # --- Top/Bottom bars ---
    c.setFillColor(pri)
    c.rect(0, 0, width * 0.4, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(sec)
    c.rect(width * 0.4, 0, width * 0.6, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(sec)
    c.rect(0, height - 0.3*cm, width * 0.6, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(pri)
    c.rect(width * 0.6, height - 0.3*cm, width * 0.4, 0.3*cm, fill=1, stroke=0)
    
    center_x = width / 2
    center_y = height / 2
    
    # --- QR CODE (centered, large) ---
    qr_size = 7.0*cm
    qr_drawn = False
    
    try:
        import qrcode
        from io import BytesIO as QRBytesIO
        
        base_url = getattr(settings, 'SITE_URL', 'https://certifai.up.railway.app')
        verify_url = f"{base_url}/verificar/{certificado.verification_hash}/"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=12,
            border=2,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        
        qr_img = qr.make_image(fill_color="#162054", back_color="white")
        
        qr_buffer = QRBytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        qr_reader = ImageReader(qr_buffer)
        qr_x = center_x - qr_size / 2
        qr_y = center_y - qr_size / 2 - 0.5*cm
        
        # QR background box with gold border
        c.saveState()
        c.setFillColor(HexColor('#FFFFFF'))
        c.setStrokeColor(sec)
        c.setLineWidth(2.5)
        padding = 0.5*cm
        c.roundRect(qr_x - padding, qr_y - padding, 
                    qr_size + 2*padding, qr_size + 2*padding, 
                    0.4*cm, fill=1, stroke=1)
        c.restoreState()
        
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size, mask='auto')
        qr_drawn = True
        
    except Exception:
        pass
    
    # --- Title above QR ---
    title_y = center_y + qr_size / 2 + 1.5*cm
    
    c.setFont("Times-Bold", 24)
    c.setFillColor(pri)
    c.drawCentredString(center_x, title_y + 1.2*cm, "VERIFICACIÓN DE CERTIFICADO")
    
    # Gold underline
    c.setStrokeColor(sec)
    c.setLineWidth(2)
    line_w = 12*cm
    c.line(center_x - line_w/2, title_y + 0.8*cm, center_x + line_w/2, title_y + 0.8*cm)
    
    # Subtitle
    c.setFont("Times-Roman", 12)
    c.setFillColor(HexColor('#555555'))
    c.drawCentredString(center_x, title_y, "Escanee el código QR para verificar la autenticidad de este certificado")
    
    # --- Text below QR ---
    info_y = center_y - qr_size / 2 - 1.8*cm
    
    c.setFont("Times-Roman", 11)
    c.setFillColor(HexColor('#444444'))
    c.drawCentredString(center_x, info_y, "Este código le redirigirá a una página segura donde podrá confirmar")
    c.drawCentredString(center_x, info_y - 0.5*cm, "que el titular participó en el evento o seminario certificado.")
    
    # Verification ID
    c.setFont("Helvetica", 8)
    c.setFillColor(HexColor('#999999'))
    c.drawCentredString(center_x, info_y - 1.5*cm, f"ID: {certificado.verification_hash}")
    
    # Footer text
    c.setFont("Times-Italic", 9)
    c.setFillColor(HexColor('#888888'))
    c.drawCentredString(center_x, 1.5*cm, "Documento generado electrónicamente — CertifAI / Universidad Estatal de Milagro")


