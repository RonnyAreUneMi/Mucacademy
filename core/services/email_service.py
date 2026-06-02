from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import threading

def send_certificate_email(certificate):
    """
    Sends an email notification to the user about their new certificate.
    Uses threading to avoid blocking the main thread (simple async).
    """
    try:
        if not certificate.email:
            return False

        subject = f"¡Felicidades {certificate.first_name}! Tu certificado está listo - MUC"

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8001').rstrip('/')
        search_url = f"{site_url}/buscar/"
        
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
                    <div style="text-align: center; margin-bottom: 20px;">
                        <h2 style="color: #162054;">¡Tu certificado está listo!</h2>
                    </div>
                    
                    <p>Hola <strong>{certificate.first_name} {certificate.last_name}</strong>,</p>

                    <p>En el <strong>Movimiento Universitario por el Cambio (MUC)</strong> estamos orgullosos de tu participación en el seminario: <strong>{certificate.course}</strong>.</p>
                    
                    <p>Sabemos que este es un paso más en tu crecimiento académico y profesional. ¡Sigue adelante!</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{search_url}" style="background-color: #D4AF37; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Descargar Certificado
                        </a>
                    </div>
                    
                    <p style="font-size: 12px; color: #777; margin-top: 30px; text-align: center;">
                        Si no puedes hacer clic en el botón, copia y pega este enlace en tu navegador:<br>
                        {search_url}
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    
                    <p style="text-align: center; font-size: 12px; color: #999;">
                        Este es un mensaje automático, por favor no respondas a este correo.<br>
                        &copy; 2026 Movimiento Universitario por el Cambio
                    </p>
                </div>
            </body>
        </html>
        """
        
        plain_message = strip_tags(html_message)
        from_email = settings.EMAIL_HOST_USER or 'noreply@muc.unemi.edu.ec'
        
        # Start thread
        email_thread = threading.Thread(
            target=send_mail,
            args=(subject, plain_message, from_email, [certificate.email]),
            kwargs={'html_message': html_message, 'fail_silently': False}
        )
        email_thread.start()
        
        return True
    except Exception as e:
        print(f"Error sending email to {certificate.email}: {e}")
        return False
