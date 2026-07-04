"""
Regenera el diagrama entidad-relación (static/erd-viewer.html) por introspección
de los modelos actuales de la app `core`. Mantiene la UI del viewer y solo
reemplaza los bloques `const ENTITIES = [...]` y `const RELATIONS = [...]`.

Uso:
    python manage.py update_erd
"""
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

ERD_PATH = Path(settings.BASE_DIR) / 'static' / 'erd-viewer.html'

# Modelo → dominio (para color/columna en el viewer). Dominios ya definidos en el HTML.
DOMAIN = {
    'Faculty': 'catalog', 'AcademicTitle': 'catalog',
    'User': 'admin', 'AccessRequest': 'admin', 'AuditLog': 'admin',
    'Participant': 'public', 'ParticipantToken': 'public', 'PasswordResetToken': 'public',
    'Program': 'events', 'Event': 'events', 'Speaker': 'events',
    'Attendance': 'events', 'Enrollment': 'events',
    'CertificateBatch': 'certs', 'Certificate': 'certs', 'Signature': 'certs', 'GlobalDesign': 'certs',
    'SessionSummary': 'ai', 'QuizAttempt': 'ai', 'Evaluation': 'ai',
    'Question': 'ai', 'EvaluationAttempt': 'ai', 'EvaluationGrant': 'ai',
    'GoogleCredential': 'email',
    'AIProviderCredential': 'config', 'AIPrompt': 'config', 'AIConfig': 'config', 'UIDesignTokens': 'config',
}
COLUMN_ORDER = ['catalog', 'admin', 'public', 'events', 'certs', 'ai', 'email', 'config']

# Relaciones lógicas curadas (no son FK reales, reflejan uso/dependencia).
# Solo se agregan si ambos extremos existen. Formato: (from, to, label, card).
LOGICAL_LINKS = [
    ('SessionSummary', 'AIConfig',        'generado con IA',   'N:1'),
    ('SessionSummary', 'GoogleCredential', 'transcript Drive',  'N:1'),
    ('Event',          'GoogleCredential', 'Meet / Calendar',   'N:1'),
    ('Evaluation',     'AIConfig',         'preguntas con IA',  'N:1'),
    ('CertificateBatch', 'GlobalDesign',   'hereda diseño',     'N:1'),
    ('AIProviderCredential', 'AIConfig',   'credencial activa', 'N:1'),
    ('AIPrompt',       'AIConfig',         'prompts del sistema', 'N:1'),
]

ENC_HINTS = ('password', 'api_key', 'access_token', 'refresh_token', 'client_secret', 'code_hash', 'token', 'key')

TYPE_MAP = {
    'AutoField': 'int', 'BigAutoField': 'int', 'IntegerField': 'int',
    'PositiveIntegerField': 'int', 'PositiveSmallIntegerField': 'int', 'SmallIntegerField': 'int',
    'CharField': 'varchar', 'SlugField': 'varchar', 'TextField': 'text', 'BooleanField': 'bool',
    'DateTimeField': 'datetime', 'DateField': 'date', 'TimeField': 'time',
    'EmailField': 'varchar', 'URLField': 'url', 'UUIDField': 'uuid', 'JSONField': 'json',
    'FloatField': 'float', 'DecimalField': 'decimal', 'ImageField': 'image', 'FileField': 'file',
    'GenericIPAddressField': 'ip', 'DurationField': 'duration',
}


def _short_type(field):
    if field.is_relation and (field.many_to_one or field.one_to_one):
        return f'FK→{field.related_model.__name__}'
    return TYPE_MAP.get(field.get_internal_type(), field.get_internal_type().replace('Field', '').lower())


def _flags(field):
    flags = []
    if field.primary_key:
        flags.append('PK')
    if field.is_relation and (field.many_to_one or field.one_to_one):
        flags.append('FK')
    if getattr(field, 'unique', False) and not field.primary_key:
        flags.append('UK')
    if any(h in field.name for h in ENC_HINTS) and not field.is_relation:
        flags.append('ENC')
    return flags


def _kind(model):
    return (model._meta.verbose_name or model.__name__).title()[:26]


def _desc(model):
    doc = (model.__doc__ or '').strip().split('\n')[0].strip()
    return doc[:140] if doc and not doc.startswith(model.__name__) else f'Modelo {model.__name__}.'


class Command(BaseCommand):
    help = 'Regenera static/erd-viewer.html desde los modelos actuales.'

    def handle(self, *args, **options):
        if not ERD_PATH.exists():
            raise CommandError(f'No existe {ERD_PATH}')

        models = list(apps.get_app_config('core').get_models())
        by_domain = {d: [] for d in COLUMN_ORDER}
        for m in models:
            by_domain.setdefault(DOMAIN.get(m.__name__, 'config'), []).append(m)

        entities, relations = [], []
        for col, dom in enumerate(COLUMN_ORDER):
            x = 60 + col * 340
            y = 60
            for m in by_domain.get(dom, []):
                fields, nfields = [], 0
                for f in m._meta.local_fields:
                    fl = _flags(f)
                    fields.append((f.name, _short_type(f), fl))
                    nfields += 1
                    if 'FK' in fl:
                        card = '1:1' if f.one_to_one else 'N:1'
                        relations.append((m.__name__, f.related_model.__name__, 'fk', f.name, card))
                    # Relaciones lógicas (no son FK reales, pero referencian catálogos):
                    elif f.name == 'faculty' and f.get_internal_type() in ('CharField', 'SlugField'):
                        relations.append((m.__name__, 'Faculty', 'logical', 'faculty (code)', 'N:1'))
                    elif m.__name__ == 'Speaker' and f.name == 'title':
                        relations.append(('Speaker', 'AcademicTitle', 'logical', 'title (abbrev)', 'N:1'))
                entities.append({
                    'name': m.__name__, 'domain': dom, 'kind': _kind(m),
                    'desc': _desc(m), 'fields': fields, 'pos': (x, y),
                })
                y += 90 + nfields * 22 + 40

        # Relaciones lógicas curadas (solo si ambos modelos existen).
        model_names = {m.__name__ for m in models}
        for frm, to, label, card in LOGICAL_LINKS:
            if frm in model_names and to in model_names:
                relations.append((frm, to, 'logical', label, card))

        js_entities = self._render_entities(entities)
        js_relations = self._render_relations(relations)

        html = ERD_PATH.read_text(encoding='utf-8')
        html = self._replace_block(html, 'const ENTITIES = [', js_entities)
        html = self._replace_block(html, 'const RELATIONS = [', js_relations)
        ERD_PATH.write_text(html, encoding='utf-8')

        self.stdout.write(self.style.SUCCESS(
            f'ERD actualizado: {len(entities)} entidades, {len(relations)} relaciones → {ERD_PATH}'
        ))

    @staticmethod
    def _js_str(s):
        return "'" + str(s).replace('\\', '\\\\').replace("'", "\\'") + "'"

    def _render_entities(self, entities):
        lines = ['const ENTITIES = [']
        for e in entities:
            lines.append('  {')
            lines.append(f"    name: {self._js_str(e['name'])}, domain: {self._js_str(e['domain'])}, kind: {self._js_str(e['kind'])},")
            lines.append(f"    desc: {self._js_str(e['desc'])},")
            lines.append('    fields: [')
            for name, typ, flags in e['fields']:
                fl = '[' + ', '.join(self._js_str(x) for x in flags) + ']'
                lines.append(f"      [{self._js_str(name)}, {self._js_str(typ)}, {fl}],")
            lines.append('    ],')
            lines.append(f"    pos: {{ x: {e['pos'][0]}, y: {e['pos'][1]} }},")
            lines.append('  },')
        lines.append('];')
        return '\n'.join(lines)

    def _render_relations(self, relations):
        lines = ['const RELATIONS = [']
        for frm, to, typ, label, card in relations:
            lines.append(f"  [{self._js_str(frm)}, {self._js_str(to)}, {self._js_str(typ)}, {self._js_str(label)}, {self._js_str(card)}],")
        lines.append('];')
        return '\n'.join(lines)

    @staticmethod
    def _replace_block(html, start_marker, new_block):
        """Reemplaza desde `start_marker` hasta el primer `\\n];` inclusive."""
        idx = html.find(start_marker)
        if idx == -1:
            raise CommandError(f'No se encontró el marcador: {start_marker}')
        end = html.find('\n];', idx)
        if end == -1:
            raise CommandError(f'No se encontró el fin del bloque para: {start_marker}')
        end += len('\n];')
        return html[:idx] + new_block + html[end:]
