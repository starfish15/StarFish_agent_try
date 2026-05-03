import ast
import operator
from tools.base import BaseTool


class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculate"

    @property
    def description(self) -> str:
        return "安全计算四则运算表达式，参数: expression (如 '1 + 2 * (3 - 4)')"

    def run(self, expression: str) -> dict:
        try:
            value = _safe_eval(expression)
            return {"expression": expression, "result": value}
        except Exception as e:
            return {"error": f"无法计算表达式: {e}"}


_ALLOWED_BINOPS: dict[type[ast.operator], object] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS: dict[type[ast.unaryop], object] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(expression: str) -> float | int:
    """Evaluate a math expression using a restricted AST.

    Supports: numbers, parentheses, + - * / // % **, unary +/-.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("expression 不能为空")

    tree = ast.parse(expression, mode="eval")
    return _eval_node(tree.body)


def _eval_node(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("只允许数字常量")

    if isinstance(node, ast.Num):  # pragma: no cover (py<3.8)
        return node.n

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BINOPS:
            raise ValueError(f"不支持的运算符: {op_type.__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_BINOPS[op_type](left, right)

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARYOPS:
            raise ValueError(f"不支持的一元运算符: {op_type.__name__}")
        operand = _eval_node(node.operand)
        return _ALLOWED_UNARYOPS[op_type](operand)

    if isinstance(node, ast.Expression):
        return _eval_node(node.body)

    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")
