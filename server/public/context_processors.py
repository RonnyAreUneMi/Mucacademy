"""Context processors del público — inyectan el participante autenticado."""
from public.services.auth import get_current_participant


def participante(request):
    """Disponible como `{{ participante }}` en todos los templates públicos."""
    return {'participante': get_current_participant(request)}
