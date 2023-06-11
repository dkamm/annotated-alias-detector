
import os
import ast
import sys
import pkgutil
import importlib
from pathlib import Path

builtin_modules = [
    'abc',
    'aifc',
    'argparse',
    'array',
    'ast',
    'asynchat',
    'asyncio',
    'asyncore',
    'atexit',
    'audioop',
    'base64',
    'bdb',
    'binascii',
    'binhex',
    'bisect',
    'builtins',
    'bz2',
    'cProfile',
    'calendar',
    'cgi',
    'cgitb',
    'chunk',
    'cmath',
    'cmd',
    'code',
    'codecs',
    'codeop',
    'collections',
    'colorsys',
    'compileall',
    'concurrent',
    'configparser',
    'contextlib',
    'copy',
    'copyreg',
    'crypt',
    'csv',
    'ctypes',
    'curses',
    'datetime',
    'dbm',
    'decimal',
    'difflib',
    'dis',
    'distutils',
    'doctest',
    'email',
    'encodings',
    'enum',
    'errno',
    'faulthandler',
    'fcntl',
    'filecmp',
    'fileinput',
    'fnmatch',
    'formatter',
    'fractions',
    'ftplib',
    'functools',
    'gc',
    'getopt',
    'getpass',
    'gettext',
    'glob',
    'grp',
    'gzip',
    'hashlib',
    'heapq',
    'hmac',
    'html',
    'http',
    'imaplib',
    'imghdr',
    'imp',
    'importlib',
    'inspect',
    'io',
    'ipaddress',
    'itertools',
    'json',
    'keyword',
    'lib2to3',
    'linecache',
    'locale',
    'logging',
    'lzma',
    'mailbox',
    'mailcap',
    'marshal',
    'math',
    'mimetypes',
    'mmap',
    'modulefinder',
    'msilib',
    'msvcrt',
    'multiprocessing',
    'netrc',
    'nis',
    'nntplib',
    'numbers',
    'operator',
    'optparse',
    'os',
    'ossaudiodev',
    'parser',
    'pathlib',
    'pdb',
    'pickle',
    'pickletools',
    'pipes',
    'pkgutil',
    'pkg_resources',
    'platform',
    'plistlib',
    'poplib',
    'posix',
    'pprint',
    'profile',
    'pstats',
    'pty',
    'pwd',
    'py_compile',
    'pyclbr',
    'pydoc',
    'queue',
    'quopri',
    'random',
    're',
    'readline',
    'reprlib',
    'resource',
    'rlcompleter',
    'runpy',
    'sched',
    'secrets',
    'select',
    'selectors',
    'setuptools',
    'shelve',
    'shlex',
    'shutil',
    'signal',
    'site',
    'smtpd',
    'smtplib',
    'sndhdr',
    'socket',
    'socketserver',
    'spwd',
    'sqlite3',
    'ssl',
    'stat',
    'statistics',
    'string',
    'stringprep',
    'struct',
    'subprocess',
    'sunau',
    'symbol',
    'symtable',
    'sys',
    'sysconfig',
    'syslog',
    'tabnanny',
    'tarfile',
    'telnetlib',
    'tempfile',
    'termios',
    'test',
    'textwrap',
    'threading',
    'time',
    'timeit',
    'tkinter',
    'token',
    'tokenize',
    'trace',
    'traceback',
    'tracemalloc',
    'tty',
    'turtle',
    'turtledemo',
    'types',
    'typing',
    'unicodedata',
    'unittest',
    'urllib',
    'uu',
    'uuid',
    'venv',
    'warnings',
    'wave',
    'weakref',
    'webbrowser',
    'winreg',
    'winsound',
    'wsgiref',
    'xdrlib',
    'xml',
    'xmlrpc',
    'zipapp',
    'zipfile',
    'zipimport',
    'zlib'
]

def get_module_from_path(path: Path, level: int):
    """Extracts module name from path up to level
    
    Examples:

    Suppose path is "module_a/foo/__init__.py"
    if level is 1, then returns "foo"
    if level is 2, then returns "module_a.foo"
    """
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

def get_abs_module(current_module: str, module: str, level: int) -> str:
    assert level >= 1, "level must be >= 1"

    parts = current_module.split(".")
    if level > 1:
        parts = parts[:-(level-1)]
    parts.append(module)
    return ".".join(parts)


def get_path_for_relative_import(cwd: Path, module_name: str, level: int) -> Path:
    """Returns the path for a relative import given the current directory

    Suppose we are processing the line

    `from .types import FooType` in module_a/__init__.py

    Then we would have
    cwd = "module_a"
    module_name = "types"
    level = 1

    and return "module_a/types.py"
    """
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

class AnnotatedAliasDetector(ast.NodeVisitor):
    """Recursively detects all annotated aliases in full module import graph
    
    The detector builds a directed graph where symbol names are nodes and edges are imports.

    Example:

    Suppose we had files like

    module_a/types.py:
        FooType = ...

    module_a/__init__.py:
        from .types import FooType

    main.py:
        from module_a import FooType

    The graph would contain path FooType -> module_a.FooType -> module_a.types.FooType 
    """

    def __init__(self):
        self.current_dir = Path(os.getcwd())
        self.current_module = None
        self.visited_modules = set()
        self.annotated_aliases = set()
        self.symbol_def_graph = {}

    def get_root_name(self, name: str) -> str:
        """Returns the source name of name by walking up the symbol definition graph"""
        while name:
            prev_name = name
            name = self.symbol_def_graph.get(name)
        return prev_name

    def visit_module(self, module: str, level: int) -> str:
        """Recursively visits the module to detect Annotated aliases.

        The module is treated as a relative import if level >= 1

        Returns the module's full name which may not be known beforehand because of relative imports
        """
        base_module = module.split(".")[0]
        if level >= 1:
            # relative import

            # convert rel import into absolute
            abs_module = get_abs_module(self.current_module, module, level)

            if abs_module in self.visited_modules:
                # already visited
                return abs_module

            self.visited_modules.add(abs_module)

            # use importlib to find the module path
            try:
                module_spec = importlib.util.find_spec(abs_module)
            except ModuleNotFoundError:
                # trying to import a module from nonexistant package like "nonexistant_package.module"
                return abs_module

            if not module_spec:
                # could not find module
                return abs_module

            module_path = Path(module_spec.origin)
            if not str(module_path).endswith(".py"):
                # could be a shared object or something
                return abs_module
            code = module_path.read_text()

            ## do some filesys checking to find the module path
            #try:
                #module_path = get_path_for_relative_import(
                    #cwd=self.current_dir,
                    #module_name=module,
                    #level=level)
            #except FileNotFoundError:
                ## TODO: This is happening for numpy _multiarray_umath. not sure why yet
                #return module

            #code = module_path.read_text()
            module_node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)
            old_current_dir = self.current_dir
            old_current_module = self.current_module
            self.current_module = abs_module
            self.current_dir = module_path.parent
            self.visit(module_node)
            self.current_dir = old_current_dir
            self.current_module = old_current_module
            return abs_module
        else:
            # absolute import

            # in builtins
            if base_module in builtin_modules:
                return module

            # already visited
            if module in self.visited_modules:
                return module

            # use importlib to find the module path
            try:
                module_spec = importlib.util.find_spec(module)
            except ModuleNotFoundError:
                # trying to import a module from nonexistant package like "nonexistant_package.module"
                return module

            if not module_spec:
                # could not find module
                return module

            module_path = Path(module_spec.origin)
            if not str(module_path).endswith(".py"):
                # could be a shared object or something
                return module
            code = module_path.read_text()

            module_node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)
            old_current_module = self.current_module
            old_current_dir = self.current_dir
            self.current_dir = module_path.parent
            self.current_module = module
            self.visited_modules.add(module)
            self.visit(module_node)
            self.current_dir = old_current_dir
            self.current_module = old_current_module
            return module

    def visit_Import(self, node):
        for name in node.names:
            module = name.name
            base_module = module.split(".")[0]
            if base_module in builtin_modules:
                continue
            self.visit_module(module, level=0)
        if hasattr(node, "module") and hasattr(node, "level"):
            self.visit_module(node.module, node.level)

    def visit_ImportFrom(self, node):
        if not node.module:
            # can sometimes be None apparently?
            return
        full_module = self.visit_module(node.module, node.level)
        base_module = full_module.split(".")[0]
        if base_module != "typing" and base_module in builtin_modules:
            return
        for name in node.names:
            # TODO: process * imports correctly

            if base_module == "typing" and name.name != "Annotated":
                # don't bother with non-Annotated stuff
                continue

            sym_name = name.name
            if self.current_module:
                sym_name = f"{self.current_module}.{sym_name}"
            import_sym_name = f"{full_module}.{name.name}"

            if import_sym_name in self.annotated_aliases or import_sym_name == "typing.Annotated":
                self.annotated_aliases.add(sym_name)

            if name.asname:
                # handle import as case
                alias_name = name.asname
                if self.current_module:
                    alias_name = f"{self.current_module}.{alias_name}"

                if sym_name in self.annotated_aliases:
                    self.annotated_aliases.add(alias_name)

            self.visit(name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        # TODO: handle multiple targets, values
        if not isinstance(node.targets[0], ast.Name):
            return

        target_name = node.targets[0].id
        if self.current_module:
            target_name = f"{self.current_module}.{target_name}"
        if isinstance(node.value, ast.Name):
            value_name = node.value.id
            if self.current_module:
                value_name = f"{self.current_module}.{value_name}"
            if value_name in self.annotated_aliases:
                self.annotated_aliases.add(target_name)
            else:
                # was assigned to something else
                self.annotated_aliases.discard(target_name)
        elif isinstance(node.value, ast.Subscript) and isinstance(node.value.value, ast.Name):
            # Check if being assigned to Annotated
            value_name = node.value.value.id
            if self.current_module:
                value_name = f"{self.current_module}.{value_name}"
            if value_name in self.annotated_aliases:
                self.annotated_aliases.add(target_name)
            else:
                # was assigned to something else
                self.annotated_aliases.discard(target_name)
        elif isinstance(node.value, ast.Attribute):
            value_name = f"{node.value.value.id}{node.value.attr}"
            if self.current_module:
                value_name = f"{self.current_module}.{value_name}"
            if value_name in self.annotated_aliases:
                self.annotated_aliases.add(target_name)
            else:
                # was assigned to something else
                self.annotated_aliases.discard(target_name)
