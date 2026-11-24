import json
import traceback


class AnyType(str):
    """Wildcard type accepted by any socket in ComfyUI."""
    def __ne__(self, __value: object) -> bool:
        return False


ANY = AnyType("*")
NUM_OUTPUTS = 8


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
                            "# Example: if input 'a0' receives 'charizard':\n"
                            "# if a0 == \"charizard\":\n"
                            "#     print(\"that's charizard\")\n\n"
                            "# Outputs are set by assigning values to variables matching output socket names\n"
                            "# (out_0 through out_7).\n"
                            "# Example:\n"
                            "# out_0 = \"blue eyes\"\n"
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

        exec_env = {
            "__builtins__": __builtins__,
        }

        for input_name, input_value in kwargs.items():
            if input_name in ("unique_id", "extra_pnginfo", "dynamic_outputs"):
                continue
            exec_env[input_name] = input_value

        for out_name in output_names:
            exec_env.setdefault(out_name, None)

        try:
            compiled = compile(code, "<comfyui_python_any_exec>", "exec")
            exec(compiled, exec_env, exec_env)
        except Exception as exc:
            tb = traceback.format_exc()
            raise RuntimeError(f"Error executing Python code in node:\n{exc}\n\n{tb}") from exc

        results = tuple(exec_env.get(out_name, None) for out_name in output_names)
        return results


NODE_CLASS_MAPPINGS = {
    "PythonAnyExecNode": PythonAnyExecNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "PythonAnyExecNode": "Python Exec (Any I/O)",
}