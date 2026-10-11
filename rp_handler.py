import os
import json
import time
import base64
import urllib.request
import subprocess
import runpod
import sys

COMFY_HOST = "127.0.0.1:8188"


def start_comfy():
    print("Launching ComfyUI background process...")
    cmd = [
        sys.executable,
        "-u",
        "/ComfyUI/main.py",
        "--listen",
        "127.0.0.1",
        "--port",
        "8188",
        "--extra-model-paths-config",
        "/app/extra_model_paths.yaml",
    ]

    # Open ComfyUI and direct logs straight to container stdout/stderr
    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)

    # Healthcheck polling
    start_time = time.time()
    while time.time() - start_time < 90:
        # Check if ComfyUI crashed immediately
        poll = proc.poll()
        if poll is not None:
            raise RuntimeError(
                f"ComfyUI crashed on startup with exit code {poll}. Check logs above."
            )

        # Test if the HTTP server is listening
        try:
            req = urllib.request.urlopen(f"http://{COMFY_HOST}/system_stats", timeout=2)
            if req.status == 200:
                print("ComfyUI successfully initialized and ready!")
                return proc
        except Exception:
            time.sleep(1)

    # Kill process if it got stuck hanging
    proc.terminate()
    raise RuntimeError("Timed out waiting for ComfyUI to start after 90 seconds.")


# Start ComfyUI
comfy_process = start_comfy()


# 2. Queue prompt workflow
def queue_prompt(workflow):
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{COMFY_HOST}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


# 3. Poll for execution history
def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


# 4. RunPod Job Handler
def handler(job):
    job_input = job.get("input", {})
    workflow = job_input.get("workflow")

    if not workflow:
        return {"error": "Missing 'workflow' parameter in payload."}

    # Queue generation
    prompt_res = queue_prompt(workflow)
    prompt_id = prompt_res.get("prompt_id")

    # Poll history until complete
    max_wait = 300
    start_time = time.time()
    images_base64 = []

    while time.time() - start_time < max_wait:
        history = get_history(prompt_id)
        if prompt_id in history:
            outputs = history[prompt_id].get("outputs", {})
            for _, node_output in outputs.items():
                if "images" in node_output:
                    for img_meta in node_output["images"]:
                        filename = img_meta["filename"]
                        subfolder = img_meta.get("subfolder", "")

                        img_path = os.path.join("/ComfyUI/output", subfolder, filename)
                        if os.path.exists(img_path):
                            with open(img_path, "rb") as f:
                                images_base64.append(
                                    base64.b64encode(f.read()).decode("utf-8")
                                )
            return {"images": images_base64}
        time.sleep(1)

    return {"error": "Job timed out during execution."}


runpod.serverless.start({"handler": handler})
