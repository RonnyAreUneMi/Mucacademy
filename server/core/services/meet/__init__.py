"""Servicios para integración Google Workspace (Meet/Calendar/Drive/Docs).

Estructura:
- oauth.py        — Flow OAuth, persistir y refrescar tokens.
- calendar_client — (Fase 2) Crear eventos con Meet link.
- drive_client    — (Fase 3) Listar y descargar transcripts.
- transcript_parser — (Fase 3) Parsear formato Meet.
- ai_pipeline     — (Fase 4) Resumen / timeline / Q&A con Claude.
"""
