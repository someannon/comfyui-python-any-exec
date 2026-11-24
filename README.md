# Python Exec (Any I/O)

A custom node for **ComfyUI** that executes user-written Python code with expandable `ANY` inputs (`a0`..`z0`, `a1`..`z1`, ...) and 8 fixed `ANY` outputs (`out_0` through `out_7`).

## Features

- **Custom Python execution:** Run arbitrary Python snippets inside your workflow—ideal for dynamic or sequential prompt assembly, pose/trait dictionaries, f-strings, and conditional logic (such as switching aspect ratios or dimensions per pose).
- **Expandable `ANY` inputs:** Add or remove inputs using **+ Input (ANY)** and **- Remove Input**, automatically named `a0`, `b0`, `c0` ... `z0`, then `a1`, `b1`, `c1` ... `z1`, and so on.
- **8 fixed `ANY` outputs:** Provides `out_0` through `out_7`, accepting any data type (`STRING`, `INT`, `FLOAT`, `CONDITIONING`, `MODEL`, `CLIP`, etc.). Chain another node instance if you need more than 8 outputs.
- **Socket variable mapping & renaming:** Access connected inputs by their socket names as Python variables, set outputs by assigning to their socket names, and **right-click any socket** to rename it to fit your workflow.
- **Built-in help modal:** Click **? Help / Info** directly on the node to view usage examples and instructions.

## Installation

### Via ComfyUI / ComfyUI Manager
Search for **Python Exec (Any I/O)** or `comfyui-python-any-exec` and install.

### Manual Installation
Clone or copy this repository into your `ComfyUI/custom_nodes/` directory and restart ComfyUI:

```bash
cd ComfyUI/custom_nodes
git clone [https://github.com/YOUR_USERNAME/comfyui-python-any-exec.git](https://github.com/YOUR_USERNAME/comfyui-python-any-exec.git)