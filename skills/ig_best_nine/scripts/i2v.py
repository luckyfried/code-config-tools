#!/usr/bin/env python3
"""The generated clips, made on a ComfyUI server: each clip `clips.py list` wrote to clips/requests.json, generated from
its photograph by Wan 2.2's image-to-video models and saved where the request says.

USAGE (S = this skill's folder, R = the run's folder):
    python3 S/scripts/i2v.py --requests R/clips/requests.json --server http://127.0.0.1:8188 [--timeout 900]

The server is a running ComfyUI whose model folders hold the six files in MODELS (Wan 2.2 14B image to video, its
four-step LoRAs, its text encoder and its VAE). A request is made when it names a photograph (`image`), a `prompt` and
a `save_as`; a request for the person's own footage names none of them and is left alone. Each photograph is uploaded,
the clip is generated at about 480p in the photograph's own shape (both sides a multiple of 16), 16 frames a second,
as many frames as its `seconds` (or `duration`) at most 81 (about 5 s; `normalize` loops a shorter clip over its beat),
and saved at `save_as` as H.264. A clip whose file is already there is not made again, so a stopped run is run again
as it was. Prints one line a clip; exits 1 naming each clip that was not made and why, and `normalize --why` stands
those in. Nothing is sent anywhere but the server named.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

FPS = 16
MOST = 81
AREA = 832 * 480
MODELS = {
    "UNETLoader": ["wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"],
    "LoraLoaderModelOnly": ["wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
                            "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"],
    "CLIPLoader": ["umt5_xxl_fp8_e4m3fn_scaled.safetensors"],
    "VAELoader": ["wan_2.1_vae.safetensors"],
}
FIELD = {"UNETLoader": "unet_name", "LoraLoaderModelOnly": "lora_name", "CLIPLoader": "clip_name", "VAELoader": "vae_name"}
NEGATIVE = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，JPEG压缩残留，丑陋的，残缺的，"
            "多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走")


def size_for(size):
    """The generated size for a photograph of `size` ("WxH"): its shape at about 832x480's area, each side a multiple of 16."""
    w, h = (int(x) for x in size.lower().split("x"))
    gw = math.sqrt(AREA * w / h)
    return max(16, round(gw / 16) * 16), max(16, round(gw * h / w / 16) * 16)


def length_for(seconds):
    """Frames for `seconds` at 16 a second, 4n+1 as the model takes them, at most 81."""
    return min(MOST, 4 * math.ceil(max(seconds * FPS - 1, 4) / 4) + 1)


def graph(image, prompt, width, height, length, prefix, seed=1):
    """ComfyUI's own Wan 2.2 14B image-to-video template in API form, core nodes only: the high-noise expert for the
    first two of four steps, the low-noise expert for the rest, each with its four-step LoRA, shift 5, euler/simple."""
    def sampler(model, latent, first, last, noise):
        return {"class_type": "KSamplerAdvanced", "inputs": {
            "model": model, "add_noise": "enable" if noise else "disable", "noise_seed": seed if noise else 0, "steps": 4,
            "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple", "positive": ["12", 0], "negative": ["12", 1],
            "latent_image": latent, "start_at_step": first, "end_at_step": last,
            "return_with_leftover_noise": "enable" if noise else "disable"}}
    hi, lo = MODELS["UNETLoader"]
    lhi, llo = MODELS["LoraLoaderModelOnly"]
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": hi, "weight_dtype": "default"}},
        "2": {"class_type": "UNETLoader", "inputs": {"unet_name": lo, "weight_dtype": "default"}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": lhi, "strength_model": 1.0}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["2", 0], "lora_name": llo, "strength_model": 1.0}},
        "5": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["3", 0], "shift": 5.0}},
        "6": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["4", 0], "shift": 5.0}},
        "7": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODELS["CLIPLoader"][0], "type": "wan", "device": "default"}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["7", 0]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["7", 0]}},
        "10": {"class_type": "VAELoader", "inputs": {"vae_name": MODELS["VAELoader"][0]}},
        "11": {"class_type": "LoadImage", "inputs": {"image": image}},
        "12": {"class_type": "WanImageToVideo", "inputs": {"positive": ["8", 0], "negative": ["9", 0], "vae": ["10", 0],
                                                          "start_image": ["11", 0], "width": width, "height": height,
                                                          "length": length, "batch_size": 1}},
        "13": sampler(["5", 0], ["12", 2], 0, 2, True),
        "14": sampler(["6", 0], ["13", 0], 2, 10000, False),
        "15": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["10", 0]}},
        "16": {"class_type": "SaveImage", "inputs": {"images": ["15", 0], "filename_prefix": prefix}},
    }


def call(base, path, data=None, headers=None, timeout=60):
    req = urllib.request.Request(base + path, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def missing(base):
    """The model files in MODELS the server does not list."""
    out = []
    for node, names in MODELS.items():
        info = json.loads(call(base, f"/object_info/{node}")).get(node) or {}
        listed = (info.get("input", {}).get("required", {}).get(FIELD[node]) or [[]])[0]
        out += [n for n in names if n not in listed]
    return out


def upload(base, path, name):
    boundary = uuid.uuid4().hex
    body = b"".join([
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode(),
        Path(path).read_bytes(),
        f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{boundary}--\r\n'.encode(),
    ])
    return json.loads(call(base, "/upload/image", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}))["name"]


def make(base, req, image, ffmpeg, timeout):
    """One clip generated on the server and saved at its `save_as`: (True, what was made) or (False, why not)."""
    width, height = size_for(req["size"])
    length = length_for(float(req.get("seconds") or req.get("duration") or 0))
    name = upload(base, image, f"clip-{req['id']}{Path(image).suffix.lower()}")
    wf = graph(name, req["prompt"], width, height, length, f"clips/{req['id']}-{uuid.uuid4().hex[:8]}")
    r = json.loads(call(base, "/prompt", json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode(),
                        {"Content-Type": "application/json"}))
    if r.get("node_errors"):
        return False, f"the server refused the graph: {json.dumps(r['node_errors'])[:300]}"
    pid, t0 = r["prompt_id"], time.time()
    while True:
        h = json.loads(call(base, f"/history/{pid}")).get(pid)
        st = (h or {}).get("status") or {}
        if st.get("completed") or st.get("status_str") == "error":
            break
        if time.time() - t0 > timeout:
            call(base, "/interrupt", b"")
            return False, f"not done after {timeout:g} s"
        time.sleep(2)
    if st.get("status_str") == "error":
        msgs = [m[1].get("exception_message", "") for m in st.get("messages", []) if m[0] == "execution_error"]
        return False, f"the server failed: {'; '.join(msgs)[:300] or 'execution error'}"
    items = sorted((it for out in h.get("outputs", {}).values() for v in out.values() if isinstance(v, list)
                    for it in v if isinstance(it, dict) and "filename" in it), key=lambda it: it["filename"])
    if not items:
        return False, "the server returned no frames"
    dest = Path(req["save_as"])
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as d:
        for k, it in enumerate(items, 1):
            q = urllib.parse.urlencode({x: it.get(x, "") for x in ("filename", "subfolder", "type")})
            Path(d, f"{k:05d}.png").write_bytes(call(base, f"/view?{q}", timeout=600))
        part = Path(d, "clip.mp4")
        e = subprocess.run([ffmpeg, "-y", "-v", "error", "-framerate", str(FPS), "-i", str(Path(d, "%05d.png")),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", str(part)], capture_output=True, text=True)
        if e.returncode:
            return False, f"ffmpeg could not write the clip: {e.stderr[-300:]}"
        os.replace(part, dest)
    return True, f"{len(items)} frames at {width}x{height} in {time.time() - t0:.0f} s"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--requests", required=True, help="the run's clips/requests.json")
    ap.add_argument("--server", required=True, help="the ComfyUI server's address, for example http://127.0.0.1:8188")
    ap.add_argument("--timeout", type=float, default=900, help="seconds one clip may take on the server")
    ap.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    a = ap.parse_args()
    base = a.server.rstrip("/")
    reqs = json.loads(Path(a.requests).read_text())["clips"]
    run = Path(a.requests).resolve().parent.parent
    todo = [r for r in reqs if r.get("image") and r.get("prompt") and r.get("save_as")]
    if not todo:
        print("no clip to generate")
        return 0
    if not a.ffmpeg:
        sys.exit("No ffmpeg found: it writes each clip. Run setup.py, or pass --ffmpeg.")
    try:
        call(base, "/system_stats", timeout=10)
        gone = missing(base)
    except (urllib.error.URLError, OSError, ValueError) as e:
        sys.exit(f"no ComfyUI server answers at {base}: {e}")
    if gone:
        sys.exit(f"the server at {base} lacks these model files: {', '.join(gone)}")
    failed = []
    for r in todo:
        if Path(r["save_as"]).exists() and Path(r["save_as"]).stat().st_size > 1000:
            print(f"clip {r['id']}: already at {r['save_as']}")
            continue
        image = Path(r["image"]) if Path(r["image"]).is_absolute() else run / r["image"]
        try:
            ok, said = make(base, r, image, a.ffmpeg, a.timeout) if image.exists() else (False, f"no photograph at {image}")
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            ok, said = False, f"the server stopped answering: {e}"
        print(f"clip {r['id']}: " + (f"made, {said} -> {r['save_as']}" if ok else f"not made: {said}"))
        if not ok:
            failed.append(r["id"])
    if failed:
        print(f"{len(failed)} of {len(todo)} clips not made ({', '.join(failed)}); normalize stands them in")
        return 1
    print(f"{len(todo)} clips made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
