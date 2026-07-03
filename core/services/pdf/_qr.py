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


def _border_geometric(c, width, height, pri, sec):
    """Esquinas triangulares + barras (estilo geométrico)."""
    def corner(origin_x, origin_y, rotation, main_col, acc_col):
        c.saveState(); c.translate(origin_x, origin_y); c.rotate(rotation)
        c.setFillColor(main_col)
        p1 = c.beginPath()
        p1.moveTo(0, 0); p1.lineTo(5.0*cm, 0); p1.lineTo(4.0*cm, 1.8*cm)
        p1.lineTo(1.8*cm, 1.8*cm); p1.lineTo(0, 5.0*cm); p1.close()
        c.drawPath(p1, fill=1, stroke=0)
        c.setFillColor(acc_col); c.setStrokeColor(white); c.setLineWidth(2)
        p2 = c.beginPath()
        p2.moveTo(0, 0); p2.lineTo(3.0*cm, 0); p2.lineTo(0, 3.0*cm); p2.close()
        c.drawPath(p2, fill=1, stroke=1)
        c.restoreState()
    corner(0, 0, 0, pri, sec)
    corner(width, height, 180, sec, pri)
    c.setFillColor(pri); c.rect(0, 0, width*0.4, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(sec); c.rect(width*0.4, 0, width*0.6, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(sec); c.rect(0, height-0.3*cm, width*0.6, 0.3*cm, fill=1, stroke=0)
    c.setFillColor(pri); c.rect(width*0.6, height-0.3*cm, width*0.4, 0.3*cm, fill=1, stroke=0)


def _border_classic(c, width, height, pri, sec):
    """Marco doble redondeado + diamantes en las esquinas (estilo clásico)."""
    c.saveState()
    mf = 10*mm
    c.setStrokeColor(pri, alpha=0.55); c.setLineWidth(3)
    c.roundRect(mf, mf, width-2*mf, height-2*mf, 3*mm, fill=0, stroke=1)
    mi = 16*mm
    c.setStrokeColor(sec, alpha=0.7); c.setLineWidth(1.5)
    c.roundRect(mi, mi, width-2*mi, height-2*mi, 2.5*mm, fill=0, stroke=1)
    d = 4*mm
    for cx, cy in [(mi, mi), (width-mi, mi), (mi, height-mi), (width-mi, height-mi)]:
        c.setFillColor(sec)
        p = c.beginPath(); p.moveTo(cx, cy+d); p.lineTo(cx+d, cy); p.lineTo(cx, cy-d); p.lineTo(cx-d, cy); p.close()
        c.drawPath(p, fill=1, stroke=0)
        di = d*0.5; c.setFillColor(pri)
        p2 = c.beginPath(); p2.moveTo(cx, cy+di); p2.lineTo(cx+di, cy); p2.lineTo(cx, cy-di); p2.lineTo(cx-di, cy); p2.close()
        c.drawPath(p2, fill=1, stroke=0)
    c.restoreState()


def _border_modern(c, width, height, pri, sec):
    """Barra lateral navy + acento dorado (estilo moderno)."""
    c.saveState()
    c.setFillColor(pri); c.rect(0, 0, 3.5*cm, height, fill=1, stroke=0)
    c.saveState(); c.translate(0, height); c.rotate(-45)
    c.roundRect(-2*cm, -5*cm, 10*cm, 10*cm, 1*cm, fill=1, stroke=0); c.restoreState()
    c.setFillColor(sec); c.rect(3.5*cm, 0, 0.18*cm, height, fill=1, stroke=0)
    c.restoreState()


def _draw_verification_page(c, certificado, width, height, pri, sec, template='geometric'):
    """
    Segunda página: verificación con QR, con el borde del diseño elegido.
    Sin logos, sin nombre. Minimalista para que un empleador escanee.
    """
    lote = certificado.batch

    # Borde según la plantilla (cada diseño mantiene su estilo).
    if template in ('classic', 'program'):
        _border_classic(c, width, height, pri, sec)
    elif template == 'modern':
        _border_modern(c, width, height, pri, sec)
    else:
        _border_geometric(c, width, height, pri, sec)

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


# Compat: nombre anterior (borde geométrico por defecto).
def _draw_geometric_verification_page(c, certificado, width, height, pri, sec):
    _draw_verification_page(c, certificado, width, height, pri, sec, template='geometric')


