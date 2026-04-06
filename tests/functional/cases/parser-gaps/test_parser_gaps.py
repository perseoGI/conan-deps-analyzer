# """
# Expected failures until the parser supports BinOp requires and compound Version booleans.

# Semantics (Conan runtime): only 3.1.0 satisfies both negated Version comparisons for gap-pkg.
# """

# from pathlib import Path

# from parser.dependency_extractor import extract_conan_dependencies

# from conftest import conanfile_in, functional_profile, meta0

# _CASE = Path(__file__).resolve().parent


# def test_binop_string_concat_requires_are_extracted():
#     """Requires tree-sitter/... and tree-sitter-alt/... built with + must appear in deps."""
#     path = conanfile_in(_CASE)
#     deps = extract_conan_dependencies(path, no_cache=True)
#     for v in deps.versions:
#         assert "tree-sitter" in deps.deps[v], "BinOp literal concat not extracted"
#         assert meta0(deps, v, "tree-sitter").version == "1.0.0"
#         assert "tree-sitter-alt" in deps.deps[v], "BinOp with conandata slice not extracted"
#         assert meta0(deps, v, "tree-sitter-alt").version == {
#             "1.0.0": "0.1.0",
#             "2.0.0": "0.2.0",
#             "3.1.0": "0.3.0",
#         }[v]


# def test_compound_not_version_and_only_3_1_0_gets_gap_pkg():
#     """(not V < 2.3.5) and (not V < 3.0.0) is True only for 3.1.0 here."""
#     path = conanfile_in(_CASE)
#     deps = extract_conan_dependencies(path, no_cache=True)
#     host = functional_profile("Linux")
#     deps.evaluate(None, profile_host=host, profile_build=host)

#     m10 = meta0(deps, "1.0.0", "gap-pkg")
#     m20 = meta0(deps, "2.0.0", "gap-pkg")
#     m31 = meta0(deps, "3.1.0", "gap-pkg")

#     assert m10.default is False
#     assert m20.default is False
#     assert m31.default is True
