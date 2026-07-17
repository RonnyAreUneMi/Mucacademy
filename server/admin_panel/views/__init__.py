"""Re-export de views que aún contienen lógica (forms, uploads, PDF).

Las pantallas que eran puras shells (dashboard, usuarios, participantes)
ahora se sirven con TemplateView desde `admin_panel/urls.py`.
"""
from ._shared import _is_admin, _is_superadmin, _log_audit  # noqa: F401
from .auth import (  # noqa: F401
    CustomLoginView,
    register,
    solicitud_pendiente,
    mi_estado,
    solicitudes_pendientes,
    aprobar_solicitud,
    rechazar_solicitud,
)
from .batch import (  # noqa: F401
    list_batches,
    create_batch,
    process_batch_mapping,
    batch_detail,
    configure_batch,
)
from .certificate import add_certificate  # noqa: F401
from .design import (  # noqa: F401
    design_global,
    design_save_firma_pos,
    design_global_preview,
)
from .design_system import design_system_edit, design_system_reset  # noqa: F401
from .academic_titles import (  # noqa: F401
    titulos_list,
    titulos_create,
    titulos_update,
    titulos_delete,
)
from .leaders import (  # noqa: F401
    lideres_list,
    lideres_add_manual,
    lideres_upload_excel,
    lideres_process_mapping,
)
from .session import (  # noqa: F401
    session_list,
    session_create,
    session_edit,
    session_generate_batch,
    session_qr_display,
)
from .program import program_list, program_create, program_detail, program_certificate_design  # noqa: F401
from .impersonate import (  # noqa: F401
    impersonate_participant, stop_impersonation,
    impersonate_user, stop_user_impersonation,
)
