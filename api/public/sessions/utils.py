def sesion_payload(event):
    """Data del evento para respuestas tras inscripción."""
    return {
        'titulo': event.title or event.day_of_week,
        'fecha': event.date.strftime('%d/%m/%Y'),
        'horario': event.label,
        'lugar': event.location,
        'modalidad': event.modality,
        'plataforma': event.platform_display_safe if event.is_virtual else '',
        'enlace_virtual': event.meeting_url if event.is_virtual else '',
    }
