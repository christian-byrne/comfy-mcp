"""Parser and AST transformer for ComfyUI Workflow DSL."""

from pathlib import Path
from lark import Lark, Transformer, Token, Tree
from .ast_nodes import Connection, Property, Node, Section, Workflow


class WorkflowTransformer(Transformer):
    """Transform Lark parse tree into AST nodes."""

    def connection(self, items):
        """Transform connection: @ NAME.NAME"""
        # items[0] is NAME, items[1] is NAME (after the dot)
        node_name = str(items[0])
        output_name = str(items[1])
        return Connection(node=node_name, output=output_name)

    def number_value(self, items):
        """Transform number value."""
        num_str = str(items[0])
        return float(num_str) if "." in num_str else int(num_str)

    def boolean_value(self, items):
        """Transform boolean value."""
        return str(items[0]) == "true"

    def name_value(self, items):
        """Transform name value (identifier)."""
        return str(items[0])

    def string_value(self, items):
        """Transform string value (text)."""
        return str(items[0]).strip()

    def property(self, items):
        """Transform property: NAME : value"""
        name = str(items[0])
        value = items[1]
        return Property(name=name, value=value)

    def node_type(self, items):
        """Transform node type: TYPE_NAME or TYPE_NAME.TYPE_NAME"""
        if len(items) == 1:
            return str(items[0])
        else:
            return f"{items[0]}.{items[1]}"

    def node(self, items):
        """Transform node: NAME : node_type property*"""
        name = str(items[0])
        node_type = items[1]
        properties = items[2:] if len(items) > 2 else []
        return Node(name=name, node_type=node_type, properties=properties)

    def header(self, items):
        """Transform header: ## TEXT"""
        return str(items[0]).strip()

    def section(self, items):
        """Transform section: header node+"""
        header = items[0]
        nodes = items[1:]
        return Section(header=header, nodes=nodes)

    def workflow(self, items):
        """Transform workflow: section*"""
        sections = [item for item in items if isinstance(item, Section)]
        return Workflow(sections=sections)


class DSLParser:
    """Main DSL parser."""

    def __init__(self, grammar_path: str | Path | None = None):
        """Initialize parser with grammar."""
        if grammar_path is None:
            grammar_path = Path(__file__).parent / "grammar.lark"

        with open(grammar_path) as f:
            self.parser = Lark(
                f.read(),
                start="workflow",
                parser="earley",
                ambiguity="resolve",
            )
        self.transformer = WorkflowTransformer()

    def parse(self, dsl_text: str) -> Workflow:
        """Parse DSL text into AST."""
        tree = self.parser.parse(dsl_text)
        return self.transformer.transform(tree)

    def parse_file(self, path: str | Path) -> Workflow:
        """Parse DSL file into AST."""
        with open(path) as f:
            return self.parse(f.read())
