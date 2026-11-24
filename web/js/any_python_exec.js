import { app } from "../../../scripts/app.js";

const ANY_TYPE = "*";
const NUM_OUTPUTS = 8;
const ALPHABET = "abcdefghijklmnopqrstuvwxyz";

function getDefaultOutputNames() {
    return Array.from({ length: NUM_OUTPUTS }, (_, i) => `out_${i}`);
}

function getNextAlphabetInputName(existingInputs) {
    const existingSet = new Set((existingInputs || []).map((i) => i.name));
    let cycle = 0;

    while (true) {
        for (let i = 0; i < ALPHABET.length; i++) {
            const candidate = `${ALPHABET[i]}${cycle}`;
            if (!existingSet.has(candidate)) {
                return candidate;
            }
        }
        cycle++;
    }
}

const HELP_HTML = `
<div style="font-family: sans-serif; line-height: 1.6; color: #e2e8f0; font-size: 14px;">
  <h2 style="margin-top: 0; color: #ffffff; border-bottom: 1px solid #334155; padding-bottom: 8px;">
    Python Exec (Any I/O) — User Guide
  </h2>

  <p>
    This node executes custom Python code written by the user (you). The main idea behind this node is to allow you to build dynamic prompts with random or sequential combinations of elements and traits.
  </p>

  <p>
    For example, suppose you want to generate multiple images of the same character in the same environment across different poses—where each pose requires adding or removing specific prompt tags, or switching to a different image aspect ratio.
  </p>

  <p>
    To achieve this, you can write <code>if / else</code> conditions for each pose, create dictionaries storing modular prompt segments to inject into your prompt template using <strong>f-strings</strong>, or store custom <code>width</code> and <code>height</code> dimensions to pass directly into an Empty Latent node.
  </p>

  <h3 style="color: #93c5fd; margin-bottom: 6px;">Reading Inputs</h3>
  <p>
    You can pass data into the node through the input sockets on the left (accepts <strong>any</strong> data type) and access or manipulate those values in your code using the input socket's name as a regular Python variable.
  </p>
  <p>
    New inputs follow the sequence <code>a0</code>, <code>b0</code>, <code>c0</code> ... <code>z0</code>, then <code>a1</code>, <code>b1</code>, <code>c1</code> ... <code>z1</code>, and so on.
  </p>
  <p>
    For instance, if you connect a string to an input socket named <code>a0</code> and want to check if its value is <code>"charizard"</code>, you can write:
  </p>
  <pre style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px; overflow-x: auto; color: #a5f3fc;"><code>if a0 == "charizard":
    print("that's charizard")</code></pre>

  <h3 style="color: #93c5fd; margin-bottom: 6px;">Setting Outputs</h3>
  <p>
    This node provides 8 fixed output sockets (<code>out_0</code> through <code>out_7</code>). To set the value sent out through an output socket, simply assign a value to a variable matching that output socket's name. If you want <code>out_0</code> to output <code>"blue eyes"</code>, write:
  </p>
  <pre style="background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 10px; overflow-x: auto; color: #a5f3fc;"><code>out_0 = "blue eyes"</code></pre>

  <p>
    Just like the inputs, output sockets also accept <strong>any</strong> data type. Depending on your conditions, you can output a <code>CONDITIONING</code>, <code>MODEL</code>, <code>CLIP</code>, <code>INT</code>, <code>FLOAT</code>, <code>STRING</code>, or any other object. If you ever need more than 8 outputs, you can chain another instance of this node.
  </p>

  <h3 style="color: #93c5fd; margin-bottom: 6px;">Managing & Renaming Sockets</h3>
  <ul style="padding-left: 20px; margin-top: 4px;">
    <li>Use <strong>+ Input (ANY)</strong> and <strong>- Remove Input</strong> to expand or shrink input ports.</li>
    <li>You can rename both inputs and outputs by <strong>right-clicking any socket</strong> and selecting <em>"Rename variable / socket"</em>, then use your custom names directly in your Python code so they fit your workflow's needs (e.g., <code>pose</code>, <code>seed_val</code>, <code>prompt_out</code>, <code>width</code>).</li>
  </ul>
</div>
`;

function openHelpModal() {
    const existing = document.getElementById("python-any-exec-help-modal");
    if (existing) {
        existing.remove();
    }

    const overlay = document.createElement("div");
    overlay.id = "python-any-exec-help-modal";
    overlay.style.cssText = `
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.65);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        padding: 20px;
    `;

    const dialog = document.createElement("div");
    dialog.style.cssText = `
        background: #1e293b;
        border: 1px solid #475569;
        border-radius: 10px;
        max-width: 680px;
        width: 100%;
        max-height: 82vh;
        display: flex;
        flex-direction: column;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
    `;

    const body = document.createElement("div");
    body.style.cssText = `
        padding: 20px 24px;
        overflow-y: auto;
    `;
    body.innerHTML = HELP_HTML;

    const footer = document.createElement("div");
    footer.style.cssText = `
        padding: 12px 24px;
        border-top: 1px solid #334155;
        display: flex;
        justify-content: flex-end;
        background: #172033;
        border-radius: 0 0 10px 10px;
    `;

    const closeBtn = document.createElement("button");
    closeBtn.textContent = "Close";
    closeBtn.style.cssText = `
        background: #3b82f6;
        color: #ffffff;
        border: none;
        border-radius: 6px;
        padding: 8px 18px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
    `;
    closeBtn.onmouseover = () => (closeBtn.style.background = "#2563eb");
    closeBtn.onmouseout = () => (closeBtn.style.background = "#3b82f6");
    closeBtn.onclick = () => overlay.remove();

    overlay.onclick = (e) => {
        if (e.target === overlay) overlay.remove();
    };

    const onKeyDown = (e) => {
        if (e.key === "Escape") {
            overlay.remove();
            document.removeEventListener("keydown", onKeyDown);
        }
    };
    document.addEventListener("keydown", onKeyDown);

    footer.appendChild(closeBtn);
    dialog.appendChild(body);
    dialog.appendChild(footer);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);
}

function syncDynamicOutputsWidget(node) {
    const widget = node.widgets?.find((w) => w.name === "dynamic_outputs");
    const defaults = getDefaultOutputNames();
    const outNames = Array.from({ length: NUM_OUTPUTS }, (_, i) => {
        const slot = node.outputs?.[i];
        return slot && slot.name ? slot.name : defaults[i];
    });
    if (widget) {
        widget.value = JSON.stringify(outNames);
    }
}

function ensureFixedOutputs(node) {
    const defaults = getDefaultOutputNames();
    node.outputs = node.outputs || [];

    while (node.outputs.length > NUM_OUTPUTS) {
        node.removeOutput(node.outputs.length - 1);
    }

    for (let i = 0; i < node.outputs.length; i++) {
        node.outputs[i].type = ANY_TYPE;
        if (!node.outputs[i].name) {
            node.outputs[i].name = defaults[i];
            node.outputs[i].label = defaults[i];
        }
    }

    for (let i = node.outputs.length; i < NUM_OUTPUTS; i++) {
        node.addOutput(defaults[i], ANY_TYPE);
    }
}

app.registerExtension({
    name: "ComfyUI.PythonAnyExecNode",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "PythonAnyExecNode") return;

        const origOnNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const r = origOnNodeCreated ? origOnNodeCreated.apply(this, arguments) : undefined;

            const defaultOutJson = JSON.stringify(getDefaultOutputNames());
            let dynWidget = this.widgets?.find((w) => w.name === "dynamic_outputs");
            if (!dynWidget) {
                dynWidget = this.addWidget("text", "dynamic_outputs", defaultOutJson, () => {});
            }
            dynWidget.type = "hidden";
            dynWidget.computeSize = () => [0, -4];

            if (!this.inputs || this.inputs.filter((i) => i.name !== "code").length === 0) {
                this.addInput("a0", ANY_TYPE);
            }

            ensureFixedOutputs(this);
            syncDynamicOutputsWidget(this);

            this.addWidget("button", "+ Input (ANY)", null, () => {
                const dynInputs = (this.inputs || []).filter((i) => i.name !== "code");
                const name = getNextAlphabetInputName(dynInputs);
                this.addInput(name, ANY_TYPE);
                this.setDirtyCanvas(true, true);
            });

            this.addWidget("button", "- Remove Input", null, () => {
                const dynInputs = (this.inputs || []).filter((i) => i.name !== "code");
                if (dynInputs.length > 0) {
                    const last = dynInputs[dynInputs.length - 1];
                    const idx = this.inputs.indexOf(last);
                    if (idx !== -1) this.removeInput(idx);
                    this.setDirtyCanvas(true, true);
                }
            });

            this.addWidget("button", "? Help / Info", null, () => {
                openHelpModal();
            });

            return r;
        };

        const origOnConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const r = origOnConfigure ? origOnConfigure.apply(this, arguments) : undefined;
            ensureFixedOutputs(this);
            syncDynamicOutputsWidget(this);
            return r;
        };

        const origGetSlotMenuOptions = nodeType.prototype.getSlotMenuOptions;
        nodeType.prototype.getSlotMenuOptions = function (slot) {
            const options = origGetSlotMenuOptions ? origGetSlotMenuOptions.apply(this, arguments) || [] : [];
            if (!slot || slot.name === "code") return options;

            options.unshift({
                content: "Rename variable / socket",
                callback: () => {
                    app.canvas.prompt(
                        "New variable name (e.g., a0, out_0):",
                        slot.name,
                        (newName) => {
                            if (!newName) return;
                            const cleaned = newName.trim().replace(/[^a-zA-Z0-9_]/g, "_");
                            if (!cleaned) return;
                            slot.name = cleaned;
                            slot.label = cleaned;
                            syncDynamicOutputsWidget(this);
                            this.setDirtyCanvas(true, true);
                        }
                    );
                },
            });

            return options;
        };
    },
});
