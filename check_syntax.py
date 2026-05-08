
import ast
import sys

with open(sys.argv[1], 'rb') as f:
    source = f.read()
try:
    tree = ast.parse(source, filename=sys.argv[1])
    print("No syntax errors found!")
except SyntaxError as e:
    print(f"Syntax error at line {e.lineno}, column {e.offset}: {e.msg}")
    print(f"Line content: {e.text}")
    # Print surrounding lines
    lines = source.decode('utf-8', errors='replace').splitlines()
    start = max(0, e.lineno - 20)
    end = min(len(lines), e.lineno + 20)
    for i in range(start, end):
        marker = ' >>> ' if i == e.lineno - 1 else '     '
        print(f"{marker}{i+1:4d}: {lines[i]}")
