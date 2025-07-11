import os
import ast
import importlib.util
import sys

repo_root = os.path.dirname(__file__)

missing = {}

for root, dirs, files in os.walk(repo_root):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as fh:
                try:
                    tree = ast.parse(fh.read(), filename=path)
                except Exception as e:
                    print(f'Error parsing {path}: {e}')
                    continue
            package = os.path.relpath(root, repo_root).replace(os.sep, '.')
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        try:
                            if importlib.util.find_spec(module) is None:
                                missing.setdefault(path, []).append(module)
                        except Exception:
                            missing.setdefault(path, []).append(module)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module = '.' * node.level + node.module
                    else:
                        module = '.' * node.level
                    try:
                        if node.level > 0:
                            # compute package path
                            rel_pkg = package.split('.')
                            mod_parts = module.lstrip('.').split('.') if node.module else []
                            while node.level > 0 and rel_pkg:
                                rel_pkg.pop()
                                node.level -= 1
                            full_module = '.'.join(rel_pkg + mod_parts)
                        else:
                            full_module = module
                        try:
                            if importlib.util.find_spec(full_module) is None:
                                missing.setdefault(path, []).append(full_module)
                        except Exception:
                            missing.setdefault(path, []).append(full_module)
                    except Exception:
                        missing.setdefault(path, []).append(full_module)

if missing:
    for path, modules in missing.items():
        uniq = sorted(set(modules))
        print(path)
        for m in uniq:
            print("  missing:", m)
        print()
else:
    print("No missing modules detected")
