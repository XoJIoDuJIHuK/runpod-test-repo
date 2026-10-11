import os
import sys
import json
import time
import base64
import urllib.request
import subprocess
import traceback
import runpod

COMFY_HOST = "127.0.0.1:8188"

print("=== RUNPOD VOLUME INSPECTION ===", flush=True)
if not os.path.exists("/runpod-volume"):
    print(
        "ERROR: /runpod-volume does NOT exist at all! Volume is not attached.",
        flush=True,
    )
else:
    contents = []
    for root, dirs, files in os.walk("/runpod-volume"):
        for f in files:
            contents.append(os.path.join(root, f))
    if not contents:
        print(
            "WARNING: /runpod-volume exists, but is COMPLETELY EMPTY. Check Volume attachment & region!",
            flush=True,
        )
    else:
        print(f"Found {len(contents)} files in /runpod-volume:")
        for item in contents[:20]:  # print first 20 files
            print(f"  -> {item}", flush=True)
print("================================", flush=True)

# Symlink fallback so both /models/clip and /models/text_encoders always work
if os.path.exists("/runpod-volume/models/text_encoders") and not os.path.exists(
    "/runpod-volume/models/clip"
):
    try:
        os.symlink("/runpod-volume/models/text_encoders", "/runpod-volume/models/clip")
    except Exception:
        pass
elif os.path.exists("/runpod-volume/models/clip") and not os.path.exists(
    "/runpod-volume/models/text_encoders"
):
    try:
        os.symlink("/runpod-volume/models/clip", "/runpod-volume/models/text_encoders")
    except Exception:
        pass


def start_comfy():
    print("Launching ComfyUI background process...", flush=True)
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

    proc = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr)

    start_time = time.time()
    while time.time() - start_time < 90:
        poll = proc.poll()
        if poll is not None:
            raise RuntimeError(
                f"ComfyUI terminated unexpectedly with exit code {poll}."
            )

        try:
            req = urllib.request.urlopen(f"http://{COMFY_HOST}/system_stats", timeout=2)
            if req.status == 200:
                print("ComfyUI successfully initialized and ready!", flush=True)
                return proc
        except Exception:
            time.sleep(1)

    proc.terminate()
    raise RuntimeError("Timed out waiting for ComfyUI to respond after 90 seconds.")


# Main startup protected with visible traceback
try:
    comfy_process = start_comfy()
except Exception as e:
    print(f"FATAL STARTUP ERROR: {e}", file=sys.stderr, flush=True)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)


def queue_prompt(workflow):
    payload = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(
        f"http://{COMFY_HOST}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{COMFY_HOST}/history/{prompt_id}") as response:
        return json.loads(response.read())


def handler(job):
    job_input = job.get("input", {})
    workflow = job_input.get("workflow")

    if not workflow:
        return {"error": "Missing 'workflow' parameter in payload."}

    prompt_res = queue_prompt(workflow)
    prompt_id = prompt_res.get("prompt_id")

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
