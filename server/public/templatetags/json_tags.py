"""Template filters para serializar datos como JSON dentro de atributos HTML."""
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name='ponentes_json')
def ponentes_json(qs):
    """Serializa una queryset de Ponente a JSON listo para meter en data-attr.

    Devuelve un string HTML-escaped seguro (Django auto-escapa el output del filter
    en un atributo, así que devolvemos JSON plano y dejamos que el template lo
    escape al insertarlo en `data-...`).
    """
    items = []
    for p in qs:
        items.append({
            'name': p.name or '',
            'title': p.title or '',
            'affiliation': p.affiliation or '',
            'bio': p.bio or '',
        })
    return json.dumps(items, ensure_ascii=False)
