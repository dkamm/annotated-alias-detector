import ast
import os
import importlib
from pathlib import Path
from textwrap import dedent
from static_analysis import AnnotatedAliasDetector, get_abs_module

def test_get_abs_module_level_1():
    abs_module = get_abs_module("numpy.core", "_multiarray_umath", 1)
    assert abs_module == "numpy.core._multiarray_umath"

def test_get_abs_module_level_2():
    abs_module = get_abs_module("numpy.core.numeric", "_multiarray_umath", 2)
    assert abs_module == "numpy.core._multiarray_umath"

def test_basic_import():
    code = dedent("""
    from module_a import FooType
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["FooType", 
         "module_a.FooType",
         "module_a.BarType",
         "module_a.BazType",
         "module_a.types.FooType",
         "module_a.types.BarType",
         "module_a.types.BazType",
         "module_a.types.Annotated"]
    )

def test_direct_import():
    code = dedent("""
    from module_a.types import FooType
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["FooType", "module_a.types.FooType", "module_a.types.BarType", "module_a.types.BazType", "module_a.types.Annotated"]
    )


def test_jaxtyping_from_import():
    code = dedent("""
    from jaxtyping import Float
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["Float",
         "jaxtyping.Float",
         "jaxtyping.Int8",
         "jaxtyping.Int32",
         "jaxtyping.UInt8",
         "jaxtyping.Int",
         "jaxtyping.Complex64",
         "jaxtyping.Float32",
         "jaxtyping.UInt64",
         "jaxtyping.Int64",
         "jaxtyping.Integer",
         "jaxtyping.BFloat16",
         "jaxtyping.UInt16",
         "jaxtyping.Complex",
         "jaxtyping.Float16",
         "jaxtyping.Int16",
         "jaxtyping.UInt32",
         "jaxtyping.Complex128",
         "jaxtyping.Float64",
         "jaxtyping.Key",
         "jaxtyping.Shaped",
         "jaxtyping.UInt",
         "jaxtyping.Inexact",
         "jaxtyping.Num",
         "jaxtyping.Float",
         "jaxtyping.Bool",
         "jaxtyping._indirection.Int8",
         "jaxtyping._indirection.Int32",
         "jaxtyping._indirection.UInt8",
         "jaxtyping._indirection.Int",
         "jaxtyping._indirection.Complex64",
         "jaxtyping._indirection.Float32",
         "jaxtyping._indirection.UInt64",
         "jaxtyping._indirection.Int64",
         "jaxtyping._indirection.Integer",
         "jaxtyping._indirection.BFloat16",
         "jaxtyping._indirection.UInt16",
         "jaxtyping._indirection.Complex",
         "jaxtyping._indirection.Float16",
         "jaxtyping._indirection.Int16",
         "jaxtyping._indirection.UInt32",
         "jaxtyping._indirection.Complex128",
         "jaxtyping._indirection.Float64",
         "jaxtyping._indirection.Key",
         "jaxtyping._indirection.Shaped",
         "jaxtyping._indirection.UInt",
         "jaxtyping._indirection.Inexact",
         "jaxtyping._indirection.Num",
         "jaxtyping._indirection.Float",
         "jaxtyping._indirection.Bool",
         "jaxtyping._indirection.Annotated",
         "typeguard._checkers.Annotated"
        ]
    )

def test_jaxtyping_import():
    code = dedent("""
    import jaxtyping
    MyFloat = jaxtyping.Float
    """)

    node = compile(code, filename="<string>", mode="exec", flags=ast.PyCF_ONLY_AST)

    analyzer = AnnotatedAliasDetector()
    analyzer.visit(node)
    assert analyzer.annotated_aliases == set(
        ["MyFloat",
         "jaxtyping.Float",
         "jaxtyping.Int8",
         "jaxtyping.Int32",
         "jaxtyping.UInt8",
         "jaxtyping.Int",
         "jaxtyping.Complex64",
         "jaxtyping.Float32",
         "jaxtyping.UInt64",
         "jaxtyping.Int64",
         "jaxtyping.Integer",
         "jaxtyping.BFloat16",
         "jaxtyping.UInt16",
         "jaxtyping.Complex",
         "jaxtyping.Float16",
         "jaxtyping.Int16",
         "jaxtyping.UInt32",
         "jaxtyping.Complex128",
         "jaxtyping.Float64",
         "jaxtyping.Key",
         "jaxtyping.Shaped",
         "jaxtyping.UInt",
         "jaxtyping.Inexact",
         "jaxtyping.Num",
         "jaxtyping.Float",
         "jaxtyping.Bool",
         "jaxtyping._indirection.Int8",
         "jaxtyping._indirection.Int32",
         "jaxtyping._indirection.UInt8",
         "jaxtyping._indirection.Int",
         "jaxtyping._indirection.Complex64",
         "jaxtyping._indirection.Float32",
         "jaxtyping._indirection.UInt64",
         "jaxtyping._indirection.Int64",
         "jaxtyping._indirection.Integer",
         "jaxtyping._indirection.BFloat16",
         "jaxtyping._indirection.UInt16",
         "jaxtyping._indirection.Complex",
         "jaxtyping._indirection.Float16",
         "jaxtyping._indirection.Int16",
         "jaxtyping._indirection.UInt32",
         "jaxtyping._indirection.Complex128",
         "jaxtyping._indirection.Float64",
         "jaxtyping._indirection.Key",
         "jaxtyping._indirection.Shaped",
         "jaxtyping._indirection.UInt",
         "jaxtyping._indirection.Inexact",
         "jaxtyping._indirection.Num",
         "jaxtyping._indirection.Float",
         "jaxtyping._indirection.Bool",
         "jaxtyping._indirection.Annotated",
         "typeguard._checkers.Annotated"
        ]
    )