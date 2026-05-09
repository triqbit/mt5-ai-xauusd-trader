import ast
import sys

class SIMChecker(ast.NodeVisitor):
    def visit_If(self, node):
        # SIM102: nested if
        if len(node.body) == 1 and isinstance(node.body[0], ast.If) and not node.orelse:
            print(f"SIM102 at line {node.lineno}")

        # SIM114: identical bodies in if/elif
        if node.orelse and len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            # This is an elif. Comparing body of if and body of elif is hard here,
            # but SIM114 usually refers to consecutive if branches with same body.
            pass

        self.generic_visit(node)

with open(sys.argv[1], 'r') as f:
    tree = ast.parse(f.read())
    SIMChecker().visit(tree)
