"""Búsqueda global del panel: eventos, programas y participantes por nombre."""
from django.db.models import Q
from rest_framework import permissions
from api.admin.permissions import HasModulePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Event, Program, Participant


class AdminSearchView(APIView):
    """GET /api/v1/admin/search/?q= → resultados por nombre (typeahead)."""
    permission_classes = [HasModulePermission]

    def get(self, request):
        q = (request.query_params.get('q') or '').strip()
        if len(q) < 2:
            return Response({'events': [], 'programs': [], 'participants': []})

        events = [{
            'id': e.id,
            'title': e.title or e.day_of_week,
            'date': e.date.strftime('%d/%m/%Y') if e.date else '',
            'url': f'/panel/sessions/{e.id}/edit/',
        } for e in Event.objects.filter(title__icontains=q).order_by('-date')[:6]]

        programs = [{
            'id': p.id, 'name': p.name, 'url': f'/panel/programas/{p.id}/',
        } for p in Program.objects.filter(name__icontains=q).order_by('name')[:6]]

        participants = [{
            'id': p.id,
            'name': f'{p.first_name} {p.last_name}'.strip() or p.email,
            'email': p.email,
            'url': f'/panel/participantes/?q={p.email}',
        } for p in Participant.objects.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q)
            | Q(email__icontains=q) | Q(national_id__icontains=q)
        ).order_by('first_name')[:6]]

        return Response({
            'events': events,
            'programs': programs,
            'participants': participants,
        })
