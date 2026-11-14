import base64
import json
import random
import time
import os
import requests

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY")
ENDPOINT_ID = os.environ.get("ENDPOINT_ID")
assert RUNPOD_API_KEY is not None and ENDPOINT_ID is not None

HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
}


def save_output_images(output, seed):
    images = output.get("images", [])
    if not images:
        print(
            "Warning: Job marked completed but no images were returned in output:",
            output,
        )
        return

    for idx, b64_str in enumerate(images):
        filename = f"output_{seed}_{idx}.png"
        with open(filename, "wb") as f:
            f.write(base64.b64decode(b64_str))
        print(f"🎉 Successfully saved: {filename}")


def poll_for_completion(job_id, seed):
    print(f"Job is processing in the cloud (ID: {job_id}). Polling for results...")
    status_url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"

    start_time = time.time()
    while time.time() - start_time < 300:  # 5 minute timeout
        time.sleep(3)
        res = requests.get(status_url, headers=HEADERS).json()
        status = res.get("status")

        if status == "COMPLETED":
            print(f"Job finished in {res.get('executionTime', 0) / 1000:.1f}s!")
            save_output_images(res.get("output", {}), seed)
            return
        elif status == "FAILED":
            print(f"❌ Job failed: {res.get('error')}")
            return
        elif status in ["IN_PROGRESS", "IN_QUEUE"]:
            print(".", end="", flush=True)
        else:
            print(f"\nUnexpected status: {status}")
            return

    print("\nTimed out waiting for serverless job.")


def generate(
    prompt: str,
    negative_prompt: str,
    checkpoint_name: str = "novaAnimeAM_v6029B.safetensors",
    vae_name: str = "qwen_image_vae.safetensors",
    clip_name: str = "qwen_3_06b_base.safetensors",
    workflow_file_path: str = "workflow_api.json",
    width: int = 960,
    height: int = 1680,
    steps: int = 25,
    cfg: float = 7.0,
    seed: int | None = None,
):
    with open(workflow_file_path, "r") as f:
        wf = json.load(f)

    if seed is None:
        seed = random.randint(1, 999999999999999)

    # Update Prompts
    wf["3"]["inputs"]["text"] = prompt
    wf["4"]["inputs"]["text"] = negative_prompt

    # Update Models
    if "14" in wf:
        if "ckpt_name" in wf["14"]["inputs"]:
            wf["14"]["inputs"]["ckpt_name"] = checkpoint_name
        elif "unet_name" in wf["14"]["inputs"]:
            wf["14"]["inputs"]["unet_name"] = checkpoint_name

    if "15" in wf and "vae_name" in wf["15"]["inputs"]:
        wf["15"]["inputs"]["vae_name"] = vae_name

    if "16" in wf and "clip_name" in wf["16"]["inputs"]:
        wf["16"]["inputs"]["clip_name"] = clip_name

    # Update Dimensions & Sampler
    wf["8"]["inputs"]["width"] = width
    wf["8"]["inputs"]["height"] = height
    wf["5"]["inputs"]["seed"] = seed
    wf["5"]["inputs"]["steps"] = steps
    wf["5"]["inputs"]["cfg"] = cfg

    payload = {"input": {"workflow": wf}}
    print(f"Triggering generation (Seed: {seed})...")

    # We append ?wait=120 to allow RunPod up to 120 seconds before timing out
    res = requests.post(
        f"https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync",
        headers=HEADERS,
        json=payload,
        timeout=180,
    ).json()

    status = res.get("status")
    job_id = res.get("id")

    if status == "COMPLETED":
        print("Job completed immediately!")
        save_output_images(res.get("output", {}), seed)
    elif status in ["IN_PROGRESS", "IN_QUEUE"]:
        poll_for_completion(job_id, seed)
    else:
        print("API Error Response:", res)


if __name__ == "__main__":
    generate(
        prompt="masterpiece, best quality, score_9, score_8, newest, highres, absurdres, very aesthetic, explicit, 1girl, solo, succubus in explicit lingerie, sitting  on a sofa in bedroom, inviting pose, portrait from below, extreme dutch angle, red hair, small black bat wings on back, wide open eyes, glowing purple tattoo on crotch, dim light",
        negative_prompt="small face, text across face, unreadable text, extra rings, extra chains, worst quality, low quality, early, old, score_1, score_2, score_3, cartoon, graphic, painting, crayon, graphite, abstract, glitch, deformed, mutated, disfigured, ugly, long body, bad anatomy, bad hands, missing fingers, extra fingers, extra digits, fewer digits, cropped, very displeasing, artist name, blurry, jpeg artifacts, lowres, censor",
        checkpoint_name="novaAnimeAM_v6029B.safetensors",
        # checkpoint_name="ilustmix_v111.safetensors",
        vae_name="qwen_image_vae.safetensors",
        clip_name="qwen_3_06b_base.safetensors",
    )
