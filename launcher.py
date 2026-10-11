import base64
import json
import random
import time
import requests

RUNPOD_API_KEY = "YOUR_RUNPOD_API_KEY"
ENDPOINT_ID = "YOUR_ENDPOINT_ID"  # Found in Serverless dashboard

HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
}


def generate(
    checkpoint_name: str,
    prompt: str,
    negative_prompt: str,
    width: int = 832,
    height: int = 1216,
    steps: int = 28,
    cfg: float = 6.0,
    seed: int = None,
):
    # 1. Load API Workflow template
    with open("workflow_api.json", "r") as f:
        wf = json.load(f)

    if seed is None:
        seed = random.randint(1, 999999999999)

    # 2. Programmatically map parameters to nodes
    for _, node in wf.items():
        node_type = node.get("class_type")

        if node_type == "CheckpointLoaderSimple":
            node["inputs"]["ckpt_name"] = checkpoint_name
        elif node_type == "EmptyLatentImage":
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
        elif node_type == "KSampler":
            node["inputs"]["seed"] = seed
            node["inputs"]["steps"] = steps
            node["inputs"]["cfg"] = cfg

    # Update prompts (match your workflow's positive and negative CLIPTextEncode IDs)
    # Check workflow_api.json to verify the exact string IDs for these nodes:
    wf["6"]["inputs"]["text"] = prompt
    wf["7"]["inputs"]["text"] = negative_prompt

    # 3. Send to RunPod
    payload = {"input": {"workflow": wf}}
    print(f"Triggering endpoint (Seed: {seed})...")

    res = requests.post(
        f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
        headers=HEADERS,
        json=payload,
        timeout=180,
    ).json()

    # 4. Handle sync / async responses
    if res.get("status") == "COMPLETED":
        save_images(res["output"], seed)
    elif res.get("status") in ["IN_QUEUE", "IN_PROGRESS"]:
        poll_job(res["id"], seed)
    else:
        print("Build/Execution Error:", res)


def poll_job(job_id, seed):
    print(f"Waiting for job {job_id}...")
    while True:
        res = requests.get(
            f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}", headers=HEADERS
        ).json()
        if res.get("status") == "COMPLETED":
            save_images(res["output"], seed)
            break
        elif res.get("status") == "FAILED":
            print("Execution failed:", res)
            break
        time.sleep(3)


def save_images(output, seed):
    images = output.get("images", [])
    for idx, b64_str in enumerate(images):
        file_path = f"output_{seed}_{idx}.png"
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(b64_str))
        print(f"Saved: {file_path}")


if __name__ == "__main__":
    generate(
        checkpoint_name="cyberrealistic_v42.safetensors",
        prompt="1girl, solo, photorealistic, looking at viewer, cinematic lighting, 8k",
        negative_prompt="(worst quality, low quality:1.4), bad anatomy, deformed limbs",
        steps=25,
        cfg=5.5,
    )
