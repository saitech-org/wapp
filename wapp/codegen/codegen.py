import os
from typing import Type

from wapp.codegen.generate_endpoints import generate_endpoints
from wapp.codegen.generate_models import generate_models
from wapp.codegen.generate_types import generate_types
from wapp.wapp import Wapp


# Utility to get all Wapp subclasses

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_wapp_classes():
    # Import all known wapp modules to ensure registration
    # (add more as needed)
    return Wapp.REGISTERED_WAPPS.items()

def write_stub(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_typescript_for_wapp(wapp_cls:Type[Wapp], out_dir):
    app_name = wapp_cls.__name__.lower()
    app_dir = os.path.join(out_dir, app_name)
    ensure_dir(app_dir)
    # Models
    models = getattr(wapp_cls, 'Models', None)
    write_stub(os.path.join(app_dir, 'models.ts'), generate_models(wapp_cls))
    # Types
    types = getattr(wapp_cls, 'Types', None)
    write_stub(os.path.join(app_dir, 'types.ts'), generate_types(wapp_cls))
    # Endpoints
    endpoints = getattr(wapp_cls, 'Endpoints', None)
    write_stub(os.path.join(app_dir, 'endpoints.ts'), generate_endpoints(wapp_cls))

def main(path=None):
    out_dir = path or os.environ.get('WAPP_CODEGEN_DIR', 'generated')
    wapps = get_wapp_classes()

    for wapp_label, wapp_cls in wapps:
        generate_typescript_for_wapp(wapp_cls, out_dir)
    print(f"Codegen complete. Output in {out_dir}/<app_name>/.")

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
