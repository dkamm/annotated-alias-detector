
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

def get_abs_module(current_module: str, module: str, level: int) -> str:
    """Returns the absolute module relative to the current module given a relative import."""
    assert level >= 1, "level must be >= 1"

    parts = current_module.split(".")
    if level > 1:
        parts = parts[:-(level-1)]
    parts.append(module)
    return ".".join(parts)

class AnnotatedAliasDetector(ast.NodeVisitor):
    """AnnotatedAliasDetector detects Annotated aliases through static analysis and recursively analyzing files by import.

    Example:

    Suppose we had files like

    module_a/types.py:
        from typing import Annotated
        FooType = Annotated

    module_a/__init__.py:
        from .types import FooType

    main.py:
        from module_a import FooType

    The visitor visits the files recursively by import and the resulting detected symbols would be
    {
        "FooType",
        "module_a.FooType",
        "module_a.types.FooType",
        "module_a.types.Annotated"
    }
    """

    def __init__(self):
        self.current_module = None
        self.visited_modules = set()
        self.annotated_aliases = set()
    
    def visit_module(self, module: str, level: int) -> str:
        """Recursively visits the module to detect Annotated aliases.

        Returns the module's full name which may not be known beforehand because of relative imports
        """
        if level >= 1:
            # convert relative import into absolute import
            module = get_abs_module(self.current_module, module, level)

        base_module = module.split(".")[0]

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
            # could be a shared object or something?
            return module
        code = module_path.read_text()

        module_node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)
        old_current_module = self.current_module
        self.current_module = module
        self.visited_modules.add(module)
        self.visit(module_node)
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
        self.generic_visit(node)

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

            self.generic_visit(name)
        self.generic_visit(node)

    
    def get_name(self, node) -> str:
        """Converts node to symbol name"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f'{self.get_name(node.value)}.{node.attr}'
        elif isinstance(node, ast.Subscript):
            name = self.get_name(node.value)
            if node.slice:
                name = f"{name}[{self.get_name(node.slice)}]"
            return name
        elif isinstance(node, ast.Slice):
            # TODO: handle this properly?
            return '<slice>'
        else:
            return '<unknown>'


    def unpack_assignment(self, target, value):
        if isinstance(target, ast.Tuple) and isinstance(value, (ast.Tuple, ast.List)):
            for sub_target, sub_value in zip(target.elts, value.elts):
                self.unpack_assignment(sub_target, sub_value)
        else:
            self.process_assignment(target, value)

    def process_assignment(self, target, value):
        target_name = self.get_name(target)
        value_name = self.get_name(value)

        if self.current_module:
            target_name = f"{self.current_module}.{target_name}"
            value_name = f"{self.current_module}.{value_name}"

        if value_name in self.annotated_aliases:
            self.annotated_aliases.add(target_name)
        else:
            self.annotated_aliases.discard(target_name)

    def visit_Assign(self, node):
        if len(node.targets) > 1:
            if not isinstance(node.value, (ast.Tuple, ast.List)) or len(node.value.elts) != len(node.targets):
                # assign each target to node value
                for target in node.targets:
                    self.unpack_assignment(target, node.value)
            else:
                # destructured assignment case
                for target, value in zip(node.targets, node.value.elts):
                    self.unpack_assignment(target, value)
        else:
            self.unpack_assignment(node.targets[0], node.value)
        self.generic_visit(node)
