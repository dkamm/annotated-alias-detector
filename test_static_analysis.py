import ast
import os
import importlib
from pathlib import Path
from textwrap import dedent
from static_analysis import AnnotatedAliasDetector, get_path_for_relative_import, get_module_from_path

def test_get_path_for_relative_import_module_path():

    path = get_path_for_relative_import(
        cwd=Path(os.getcwd()),
        module_name="module_a.types",
        level=1
    )
    assert path == Path(os.getcwd()) / "module_a" / "types.py"


def test_get_path_for_relative_import_package_path():

    path = get_path_for_relative_import(
        cwd=Path(os.getcwd()) / "module_a",
        module_name="nested",
        level=1
    )
    assert path == Path(os.getcwd()) / "module_a" / "nested" / "__init__.py"

def test_get_path_for_relative_import_multilevel():

    path = get_path_for_relative_import(
        cwd=Path(os.getcwd()) / "module_a" / "nested",
        module_name="types",
        level=2
    )
    assert path == Path(os.getcwd()) / "module_a" / "types.py"

def test_get_path_from_import_spec():
    spec = importlib.util.find_spec("jaxtyping")
    spec_path = Path(spec.origin)
    assert str(spec_path).endswith("jaxtyping/__init__.py")

def test_get_module_from_package_path():
    path = Path("/home") / "dkamm" / "python3.9" / "module_a" / "foo" / "bar" / "__init__.py"
    module_name = get_module_from_path(path, level=3)
    assert module_name == "module_a.foo.bar"

def test_get_module_from_module_path():
    path = Path("/home") / "dkamm" / "python3.9" / "module_a" / "foo" / "bar.py"
    module_name = get_module_from_path(path, level=3)
    assert module_name == "module_a.foo.bar"

def test_basic_import():
    code = dedent("""
    from module_a import FooType
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["module_a.types.FooType", "module_a.types.BarType", "module_a.types.BazType"]
    )
    assert (set([
        ("FooType", "module_a.FooType"),  
        ("module_a.FooType", "module_a.types.FooType"),  
        ("module_a.types.FooType", None),  
        ("module_a.BarType", "module_a.types.BarType"),  
        ("module_a.types.BarType", None),  
        ("module_a.BazType", "module_a.types.BazType"),  
        ("module_a.types.BazType", None),  
    ]) <= set(analyzer.symbol_import_graph.items())
    )

def test_direct_import():
    code = dedent("""
    from module_a.types import FooType
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["module_a.types.FooType", "module_a.types.BarType", "module_a.types.BazType"]
    )
    assert (set([
        ("FooType", "module_a.types.FooType"),  
        ("module_a.types.FooType", None),  
    ]) <= set(analyzer.symbol_import_graph.items())
    )
