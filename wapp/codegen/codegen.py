import os
import importlib
from wapp.wapp import Wapp

# Utility to get all Wapp subclasses

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def get_wapp_classes():
    # Import all known wapp modules to ensure registration
    # (add more as needed)
    return Wapp.REGISTERED_WAPPS

def write_stub(filename, content):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_typescript_for_wapp(wapp_cls, out_dir):
    app_name = wapp_cls.__name__.lower()
    app_dir = os.path.join(out_dir, app_name)
    ensure_dir(app_dir)
    # Models
    models = getattr(wapp_cls, 'Models', None)
    model_lines = []
    if models:
        for name, model in models.__dict__.items():
            if name.startswith('__'):
                continue
            model_lines.append(f'// Model: {name}\nexport interface {name.capitalize()} {{}}\n')
    write_stub(os.path.join(app_dir, 'models.ts'), '\n'.join(model_lines))
    # Types
    types = getattr(wapp_cls, 'Types', None)
    type_lines = []
    if types:
        for name, typ in types.__dict__.items():
            if name.startswith('__'):
                continue
            type_lines.append(f'// Type: {name}\nexport type {name} = any;\n')
    write_stub(os.path.join(app_dir, 'types.ts'), '\n'.join(type_lines))
    # Endpoints
    endpoints = getattr(wapp_cls, 'Endpoints', None)
    endpoint_lines = []
    if endpoints:
        for name, view in endpoints.__dict__.items():
            if name.startswith('__'):
                continue
            meta = getattr(view, '_wapp_endpoint_metadata', None)
            if meta:
                endpoint_lines.append(f'// Endpoint: {meta.name}\nexport const {meta.name} = "{meta.pattern}";\n')
    write_stub(os.path.join(app_dir, 'endpoints.ts'), '\n'.join(endpoint_lines))

def main(path=None):
    out_dir = path or os.environ.get('WAPP_CODEGEN_DIR', 'generated')
    wapps = get_wapp_classes()
    for wapp_cls in wapps:
        generate_typescript_for_wapp(wapp_cls, out_dir)
    print(f"Codegen complete. Output in {out_dir}/<app_name>/.")

if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)

