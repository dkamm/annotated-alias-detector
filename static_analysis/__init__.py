
import os
import ast
import importlib
from pathlib import Path

builtin_modules = [
    "os",
    "importlib",
    "typing"
]

def get_module_from_path(path: Path, level: int):
    assert level >= 1, "level must be >= 1"

    if path.name == '__init__.py':
        path = path.parent

    parts = []
    for _ in range(level):
        part = path.name
        if part.endswith(".py"):
            part = part.replace(".py", "")
        parts.append(part)
        path = path.parent

    return ".".join(reversed(parts))

def get_path_for_relative_import(cwd: Path, module_name: str, level: int):
    assert level >= 1, "level must be >= 1"

    base_path = cwd
    for l in range(level-1):
        base_path = cwd.parent

    parts = module_name.split(".")
    dirs, module_name = parts[:-1], parts[-1]

    for d in dirs:
        base_path = base_path / d

    package_path = base_path / module_name / "__init__.py"
    module_path = base_path / f"{module_name}.py"

    if package_path.exists():
        return package_path
    elif module_path.exists():
        return module_path
    else:
        raise FileNotFoundError(f"Could not find module {module_name} at level {level} from {cwd}")


def parse_module(module_path):
    if os.path.isdir(module_path):
        module_ast = ast.parse('')
        for filename in os.listdir(module_path):
            file_path = os.path.join(module_path, filename)
            file_ast = parse_module(file_path)
            module_ast.body.extend(file_ast.body)
    else:
        with open(module_path, 'r') as f:
            module_code = f.read()
        module_ast = ast.parse(module_code, module_path)

    return module_ast


class AnnotatedAliasDetector(ast.NodeVisitor):
    """Detects all annotated aliases in full module import graph"""

    def __init__(self):
        self.current_dir = Path(os.getcwd())
        self.current_module = None
        self.visited_modules = set()
        self.annotated_aliases = set()
        self.symbol_import_graph = {}

    def get_origin_name(self, name):
        while name:
            prev_name = name
            name = self.symbol_import_graph.get(name)
        return prev_name

    def visit_module(self, module, level):
        """Return the full module name

        ..foo.bar - module="foo.bar", level=2, self.current_module="module_a"
        
        """

        if level >= 1:
            # relative import

            # do some filesys checking to find the module path
            module_path = get_path_for_relative_import(
                cwd=self.current_dir,
                module_name=module,
                level=level)

            code = module_path.read_text()
            module_node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)
            old_current_dir = self.current_dir
            old_current_module = self.current_module

            rel_module = get_module_from_path(module_path, level)
            current_module = f"{self.current_module}.{rel_module}"
            self.current_module = current_module
            self.visit(module_node)
            self.current_dir = old_current_dir
            self.current_module = old_current_module
            return current_module
        else:
            # absolute import
            if module in builtin_modules:
                return module

            # use importlib to find the module path
            module_path = importlib.util.find_spec(module).origin
            code = Path(module_path).read_text()

            module_node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)
            old_current_module = self.current_module
            old_current_dir = self.current_dir
            self.current_dir = Path(module_path).parent
            self.current_module = module
            self.visit(module_node)
            self.current_dir = old_current_dir
            self.current_module = old_current_module
            return module

    def visit_Import(self, node):

        self.visit_module(node.module, node.level)

    def visit_ImportFrom(self, node):
        full_module = self.visit_module(node.module, node.level)
        base_module = full_module.split(".")[0]
        if base_module in builtin_modules:
            return
        for name in node.names:
            sym_name = name.name 
            if self.current_module:
                sym_name = f"{self.current_module}.{name.name}"
            full_name = f"{full_module}.{name.name}"
            self.symbol_import_graph[sym_name] = full_name
            self.visit(name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        target_name = node.targets[0].id
        target_full_name = f"{self.current_module}.{target_name}"
        self.symbol_import_graph[target_full_name] = None
        if isinstance(node.value, ast.Subscript):
            if isinstance(node.value.value, ast.Name):
                value_name = node.value.value.id
                if value_name == "Annotated":
                    print(f"Found new annotated alias {target_full_name}")
                    self.annotated_aliases.add(target_full_name)
        else:
            if isinstance(node.value, ast.Name):
                value_name = node.value.id
                value_full_name = f"{self.current_module}.{value_name}"
                value_origin_name = self.get_origin_name(value_full_name)
                if value_origin_name in self.annotated_aliases:
                    print(f"Found new annotated alias {target_full_name}")
                    self.annotated_aliases.add(target_full_name)

                    

