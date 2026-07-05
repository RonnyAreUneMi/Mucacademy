"""Registry of PDF design strategies.

To add a new design: create `designs/<name>.py` with a
`draw_<name>_wow(c, certificado, width, height, pri, sec, ter, txt)`
function and register it below.
"""
from .classic import draw_classic_wow
from .modern import draw_modern_wow
from .geometric import draw_geometric_wow
from .program import draw_program_wow

DESIGN_REGISTRY = {
    'classic': draw_classic_wow,
    'modern': draw_modern_wow,
    'geometric': draw_geometric_wow,
    'program': draw_program_wow,
}

def get_design(template: str):
    """Returns the drawing function for a template, falling back to classic."""
    return DESIGN_REGISTRY.get(template, draw_classic_wow)

__all__ = ['DESIGN_REGISTRY', 'get_design', 'draw_classic_wow',
           'draw_modern_wow', 'draw_geometric_wow', 'draw_program_wow']
