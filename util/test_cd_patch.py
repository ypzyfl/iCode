"""Sanity check for the cd.yml PyApp distribution patch (guard + replacement).

Extracts the second perl s/// replacement and the two guard regexes straight
from cd.yml and applies them to a mock distribution.rs fragment, mimicking
perl's s///re/replacement/ and -0ne /.../ semantics.
"""
import re
import sys

CD = r"d:\project\iCode\.github\workflows\cd.yml"
text = open(CD, encoding="utf-8").read()

# Replacement side of the unlock patch (between the second "/" and the final "/;")
m = re.search(
    r's/\\n    FileExt::unlock\\\(\\&lock_file\\\)\/(.+?)/;\n', text, re.S
)
assert m, "unlock patch not found in cd.yml"
replacement = (
    m.group(1)
    .replace("\\n", "\n")
    .replace("\\&", "&")
    .replace('\\"', '"')
)
replacement = re.sub(r"\\(?![n&])", "", replacement)  # residual backslashes

pattern = re.compile(r"\n    FileExt::unlock\(&lock_file\)")

mock = (
    "pub fn run_project() -> Result<()> {\n"
    "    let mut command = python_command(&app::python_path());\n"
    "    install_project()?;\n"
    "    FileExt::unlock(&lock_file)\n"
    "}\n"
)
patched, n = pattern.subn(lambda _: replacement, mock)
assert n == 1, "unlock pattern did not match mock"
print("patched ok:\n" + patched)

g1 = re.search(r"install_project\(\)\?;\n    \}.*?if let Err\(alias_error\) = ensure_runtime_aliases\(\)", patched, re.S)
g2 = re.search(r"ensure_runtime_aliases\(\) \{.*?FileExt::unlock\(&lock_file\)", patched, re.S)
assert g1, "guard1 failed"
assert g2, "guard2 failed"
print("guard1 ok")
print("guard2 ok")
print("ALL OK")
