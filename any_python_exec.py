import ast
import itertools
import json
import random
import traceback
from types import SimpleNamespace


class AnyType(str):
    """Wildcard type accepted by any socket in ComfyUI."""
    def __ne__(self, __value: object) -> bool:
        return False


ANY = AnyType("*")
NUM_OUTPUTS = 8
MAX_LOOP_ITERATIONS = 10000


class _LoopLimitExceeded(Exception):
    pass


def _safe_append(target, item):
    if isinstance(target, list):
        target.append(item)
        return target
    raise TypeError("append() is only allowed on lists.")


def _safe_extend(target, items):
    if isinstance(target, list):
        target.extend(items)
        return target
    raise TypeError("extend() is only allowed on lists.")


def _safe_get(target, key, default=None):
    if isinstance(target, dict):
        return target.get(key, default)
    raise TypeError("get() is only allowed on dicts.")


_ITERTOOLS_NAMESPACE = SimpleNamespace(
    product=itertools.product,
    permutations=itertools.permutations,
    combinations=itertools.combinations,
    combinations_with_replacement=itertools.combinations_with_replacement,
    chain=itertools.chain,
    islice=itertools.islice,
    cycle=itertools.cycle,
    repeat=itertools.repeat,
    zip_longest=itertools.zip_longest,
    accumulate=itertools.accumulate,
)


class SafeAstInterpreter:
    """Safely evaluates a restricted subset of Python AST without eval() or exec()."""

    ALLOWED_BINOPS = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: a / b,
        ast.FloorDiv: lambda a, b: a // b,
        ast.Mod: lambda a, b: a % b,
        ast.Pow: lambda a, b: a ** b,
    }

    ALLOWED_UNARYOPS = {
        ast.UAdd: lambda a: +a,
        ast.USub: lambda a: -a,
        ast.Not: lambda a: not a,
    }

    ALLOWED_BOOLOPS = {
        ast.And: lambda vals: all(vals),
        ast.Or: lambda vals: any(vals),
    }

    ALLOWED_CMPOPS = {
        ast.Eq: lambda a, b: a == b,
        ast.NotEq: lambda a, b: a != b,
        ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a >= b,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.Is: lambda a, b: a is b,
        ast.IsNot: lambda a, b: a is not b,
    }

    def __init__(self, initial_env: dict):
        self.env = dict(initial_env)
        self.loop_steps = 0
        self.safe_funcs = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "tuple": tuple,
            "set": set,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "randint": random.randint,
            "randrange": random.randrange,
            "uniform": random.uniform,
            "random": random.random,
            "choice": random.choice,
            "choices": random.choices,
            "sample": random.sample,
            "itertools": _ITERTOOLS_NAMESPACE,
            "product": itertools.product,
            "permutations": itertools.permutations,
            "combinations": itertools.combinations,
            "combinations_with_replacement": itertools.combinations_with_replacement,
            "chain": itertools.chain,
            "islice": itertools.islice,
            "cycle": itertools.cycle,
            "repeat": itertools.repeat,
            "zip_longest": itertools.zip_longest,
            "accumulate": itertools.accumulate,
        }

    def _check_name(self, name: str):
        if not name or name.startswith("_"):
            raise NameError(f"Access to variable '{name}' is not allowed.")

    def _check_attr(self, attr: str):
        if not attr or attr.startswith("_"):
            raise AttributeError(f"Access to attribute '{attr}' is not allowed.")

    def run(self, code: str):
        tree = ast.parse(code, mode="exec")
        for stmt in tree.body:
            self._exec_stmt(stmt)
        return self.env

    def _tick_loop(self):
        self.loop_steps += 1
        if self.loop_steps > MAX_LOOP_ITERATIONS:
            raise _LoopLimitExceeded(f"Loop iteration limit ({MAX_LOOP_ITERATIONS}) exceeded.")

    def _exec_stmt(self, node):
        if isinstance(node, ast.Assign):
            val = self._eval_expr(node.value)
            for target in node.targets:
                self._assign_target(target, val)
            return

        if isinstance(node, ast.AugAssign):
            self._check_attr(getattr(node.target, "attr", "ok"))
            op_func = self.ALLOWED_BINOPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Operator '{type(node.op).__name__}' is not allowed.")
            current = self._eval_expr(node.target)
            rhs = self._eval_expr(node.value)
            new_val = op_func(current, rhs)
            self._assign_target(node.target, new_val)
            return

        if isinstance(node, ast.Expr):
            self._eval_expr(node.value)
            return

        if isinstance(node, ast.If):
            if self._eval_expr(node.test):
                for s in node.body:
                    self._exec_stmt(s)
            else:
                for s in node.orelse:
                    self._exec_stmt(s)
            return

        if isinstance(node, ast.For):
            iterable = self._eval_expr(node.iter)
            for item in iterable:
                self._tick_loop()
                self._assign_target(node.target, item)
                for s in node.body:
                    self._exec_stmt(s)
            for s in node.orelse:
                self._exec_stmt(s)
            return

        if isinstance(node, ast.Pass):
            return

        raise SyntaxError(f"Statement '{type(node).__name__}' is not supported in this node.")

    def _assign_target(self, target, val):
        if isinstance(target, ast.Name):
            self._check_name(target.id)
            self.env[target.id] = val
            return

        if isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            items = list(val)
            if len(items) != len(target.elts):
                raise ValueError(f"Cannot unpack {len(items)} values into {len(target.elts)} variables.")
            for elt, item in zip(target.elts, items):
                self._assign_target(elt, item)
            return

        if isinstance(target, ast.Subscript):
            container = self._eval_expr(target.value)
            key = self._eval_slice(target.slice)
            container[key] = val
            return

        raise SyntaxError(f"Assignment target '{type(target).__name__}' is not supported.")

    def _eval_slice(self, slc):
        if isinstance(slc, ast.Slice):
            start = self._eval_expr(slc.lower) if slc.lower is not None else None
            stop = self._eval_expr(slc.upper) if slc.upper is not None else None
            step = self._eval_expr(slc.step) if slc.step is not None else None
            return slice(start, stop, step)
        return self._eval_expr(slc)

    def _eval_expr(self, node):
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            self._check_name(node.id)
            if node.id in self.env:
                return self.env[node.id]
            if node.id in self.safe_funcs:
                return self.safe_funcs[node.id]
            raise NameError(f"Name '{node.id}' is not defined.")

        if isinstance(node, ast.Attribute):
            self._check_attr(node.attr)
            obj = self._eval_expr(node.value)
            if obj is _ITERTOOLS_NAMESPACE and hasattr(_ITERTOOLS_NAMESPACE, node.attr):
                return getattr(_ITERTOOLS_NAMESPACE, node.attr)
            raise AttributeError(f"Attribute access '{node.attr}' is not allowed.")

        if isinstance(node, ast.List):
            return [self._eval_expr(elt) for elt in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_expr(elt) for elt in node.elts)

        if isinstance(node, ast.Set):
            return {self._eval_expr(elt) for elt in node.elts}

        if isinstance(node, ast.Dict):
            result = {}
            for k_node, v_node in zip(node.keys, node.values):
                if k_node is None:
                    other = self._eval_expr(v_node)
                    if not isinstance(other, dict):
                        raise TypeError("Dictionary unpacking requires a dict.")
                    result.update(other)
                else:
                    k = self._eval_expr(k_node)
                    v = self._eval_expr(v_node)
                    result[k] = v
            return result

        if isinstance(node, ast.Subscript):
            container = self._eval_expr(node.value)
            key = self._eval_slice(node.slice)
            return container[key]

        if isinstance(node, ast.BinOp):
            op_func = self.ALLOWED_BINOPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Binary operator '{type(node.op).__name__}' is not allowed.")
            left = self._eval_expr(node.left)
            right = self._eval_expr(node.right)
            return op_func(left, right)

        if isinstance(node, ast.UnaryOp):
            op_func = self.ALLOWED_UNARYOPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Unary operator '{type(node.op).__name__}' is not allowed.")
            operand = self._eval_expr(node.operand)
            return op_func(operand)

        if isinstance(node, ast.BoolOp):
            op_func = self.ALLOWED_BOOLOPS.get(type(node.op))
            if not op_func:
                raise ValueError(f"Boolean operator '{type(node.op).__name__}' is not allowed.")
            vals = [self._eval_expr(v) for v in node.values]
            return op_func(vals)

        if isinstance(node, ast.Compare):
            left = self._eval_expr(node.left)
            for op_node, comp_node in zip(node.ops, node.comparators):
                op_func = self.ALLOWED_CMPOPS.get(type(op_node))
                if not op_func:
                    raise ValueError(f"Comparison operator '{type(op_node).__name__}' is not allowed.")
                right = self._eval_expr(comp_node)
                if not op_func(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.IfExp):
            cond = self._eval_expr(node.test)
            return self._eval_expr(node.body if cond else node.orelse)

        if isinstance(node, ast.JoinedStr):
            parts = []
            for item in node.values:
                if isinstance(item, ast.Constant):
                    parts.append(str(item.value))
                elif isinstance(item, ast.FormattedValue):
                    val = self._eval_expr(item.value)
                    if item.conversion == 115:  # !s
                        val = str(val)
                    elif item.conversion == 114:  # !r
                        val = repr(val)
                    elif item.conversion == 97:  # !a
                        val = ascii(val)
                    if item.format_spec:
                        spec = self._eval_expr(item.format_spec)
                        parts.append(format(val, spec))
                    else:
                        parts.append(str(val))
            return "".join(parts)

        if isinstance(node, ast.Call):
            args = [self._eval_expr(a) for a in node.args]
            kwargs = {}
            for kw in node.keywords:
                if kw.arg is None:
                    raise ValueError("**kwargs in function calls is not allowed.")
                kwargs[kw.arg] = self._eval_expr(kw.value)

            # Method calls on lists/dicts (e.g., my_list.append(x), my_dict.get("k"))
            if isinstance(node.func, ast.Attribute):
                self._check_attr(node.func.attr)
                target = self._eval_expr(node.func.value)
                if target is _ITERTOOLS_NAMESPACE:
                    fn = getattr(_ITERTOOLS_NAMESPACE, node.func.attr, None)
                    if callable(fn):
                        return fn(*args, **kwargs)
                method_name = node.func.attr
                if method_name == "append":
                    return _safe_append(target, *args)
                if method_name == "extend":
                    return _safe_extend(target, *args)
                if method_name == "get":
                    return _safe_get(target, *args, **kwargs)
                if method_name == "keys" and isinstance(target, dict):
                    return list(target.keys())
                if method_name == "values" and isinstance(target, dict):
                    return list(target.values())
                if method_name == "items" and isinstance(target, dict):
                    return list(target.items())
                raise ValueError(f"Method '{method_name}' on '{type(target).__name__}' is not allowed.")

            # Direct calls to allowed helper functions (randint, choice, product, len, range, etc.)
            fn = self._eval_expr(node.func)
            if callable(fn):
                return fn(*args, **kwargs)
            raise TypeError("Target is not callable.")

        raise SyntaxError(f"Expression '{type(node).__name__}' is not supported in this node.")


class PythonAnyExecNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "code": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": (
                            "# Inputs are available as variables matching their socket names (a0, b0, ...).\n"
                            "# Supports variables, lists, dicts, f-strings, if/else, for-loops,\n"
                            "# random helpers (randint, choice, random), and itertools (product, chain, etc.).\n\n"
                            "# Example:\n"
                            "# poses = [\"standing\", \"leaping\"]\n"
                            "# moods = [\"calm\", \"fierce\"]\n"
                            "# combos = list(product(poses, moods))\n"
                            "# pose, mood = choice(combos)\n"
                            "# out_0 = f\"{a0}, {pose}, {mood}\"\n"
                        ),
                    },
                ),
            },
            "optional": {},
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO",
                "dynamic_outputs": ("STRING", {"default": "[]"}),
            },
        }

    RETURN_TYPES = (ANY,) * NUM_OUTPUTS
    RETURN_NAMES = tuple(f"out_{i}" for i in range(NUM_OUTPUTS))
    FUNCTION = "execute"
    CATEGORY = "utils/python"
    OUTPUT_NODE = False

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    def _get_output_names(self, dynamic_outputs_raw):
        default_names = [f"out_{i}" for i in range(NUM_OUTPUTS)]
        names = []

        if isinstance(dynamic_outputs_raw, str) and dynamic_outputs_raw.strip():
            try:
                parsed = json.loads(dynamic_outputs_raw)
                if isinstance(parsed, list):
                    for item in parsed:
                        if isinstance(item, dict) and item.get("name"):
                            names.append(str(item["name"]).strip())
                        elif isinstance(item, str) and item.strip():
                            names.append(item.strip())
            except Exception:
                pass

        for idx in range(NUM_OUTPUTS):
            if idx >= len(names) or not names[idx]:
                if idx >= len(names):
                    names.append(default_names[idx])
                else:
                    names[idx] = default_names[idx]

        return names[:NUM_OUTPUTS]

    def execute(
        self,
        code: str,
        unique_id=None,
        extra_pnginfo=None,
        dynamic_outputs="[]",
        **kwargs,
    ):
        output_names = self._get_output_names(dynamic_outputs)

        initial_env = {}
        for input_name, input_value in kwargs.items():
            if input_name in ("unique_id", "extra_pnginfo", "dynamic_outputs"):
                continue
            initial_env[input_name] = input_value

        for out_name in output_names:
            initial_env.setdefault(out_name, None)

        try:
            interpreter = SafeAstInterpreter(initial_env)
            final_env = interpreter.run(code)
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(f"Error evaluating script in node:\n{exc}\n\n{tb}") from exc

        results = tuple(final_env.get(out_name, None) for out_name in output_names)
        return results


NODE_CLASS_MAPPINGS = {
    "PythonAnyExecNode": PythonAnyExecNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PythonAnyExecNode": "Python Exec (Any I/O)",
}
