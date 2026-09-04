"""
Image & Video Generation Specialist for MOSKY Agent System.

Provides generate_image and generate_video capabilities.
Designed to integrate with the existing 3-specialist supervisor and MCP tools.

Preferred backend (from 2026 research):
- ComfyUI + Flux.2 (for images) + Wan 2.2 (for video) or similar open models.
- This gives Grok Imagine-like quality in open-source/local setup.
- Supports text-to-image, image-to-image, text-to-video, image-to-video.

Usage from MCP or supervisor:
    from openhands_skills.image_video_generator import image_video_generator
    result = image_video_generator.generate_image("a cyberpunk city at night, cinematic", aspect_ratio="16:9")

The actual heavy lifting is done by ComfyUI (recommended).
Configure COMFYUI_URL env var or pass in constructor.
Workflows are loaded from external JSON files in workflows/visual/ (export full from your ComfyUI for Flux.2 images or Wan 2.2 video; pass workflow_file to override).
Errors clearly if no workflow configured.
Supports workflow_file override for custom setups.

All generation goes through guards (risky tool, user_confirmed recommended for cost).
"""

import os
import time
import json
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from project_paths import VISUAL_WORKFLOWS_DIR, MARKET_AGENT_ROOT
except Exception:
    VISUAL_WORKFLOWS_DIR = Path("workflows/visual")
    MARKET_AGENT_ROOT = Path(".")

try:
    from logger import log
except Exception:
    class _Log:
        def info(self, *a, **k): pass
        def warning(self, *a, **k): pass
        def error(self, *a, **k): pass
    log = _Log()

try:
    from openhands_skills.persistent_memory import persistent_memory
except Exception:
    persistent_memory = None


class ComfyUIClient:
    """Thin client for ComfyUI HTTP API. Separates transport from workflow/prompt logic."""
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.timeout = 300

    def is_available(self) -> bool:
        try:
            resp = requests.get(f"{self.url}/system_stats", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def queue_prompt(self, workflow: Dict[str, Any]) -> str:
        try:
            resp = requests.post(f"{self.url}/prompt", json={"prompt": workflow}, timeout=30)
            resp.raise_for_status()
            return resp.json().get("prompt_id")
        except Exception as e:
            raise RuntimeError(f"Failed to queue to ComfyUI at {self.url}: {e}")

    def wait_for_result(self, prompt_id: str, output_node: str = "SaveImage") -> List[str]:
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                resp = requests.get(f"{self.url}/history/{prompt_id}", timeout=10)
                resp.raise_for_status()
                history = resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    if output_node in outputs:
                        images = outputs[output_node].get("images", [])
                        if images:
                            return [img.get("filename") or (img.get("subfolder", "") + "/" + img.get("filename", "")) for img in images]
            except Exception:
                pass
            time.sleep(2)
        raise TimeoutError("ComfyUI generation timed out")


class ImageVideoGenerator:
    """
    Professional image and video generation specialist.
    Follows the same patterns as designer.py, illustration_3d_asset_specialist.py etc.
    Workflows loaded externally (no hardcoded stubs) for maintainability.
    """

    def __init__(self, comfy_url: Optional[str] = None):
        self.comfy_url = comfy_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        self.workflows_dir = VISUAL_WORKFLOWS_DIR
        try:
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass  # best effort, user can create
        self.client = ComfyUIClient(self.comfy_url)

    def _inject_prompt(self, workflow: Dict[str, Any], positive: str, negative: str = "", ref_image: Optional[str] = None) -> Dict[str, Any]:
        """Inject text prompts and reference images into the workflow.
        STRICT CONTRACT: Exported ComfyUI workflows MUST use node _meta.title containing
        'positive' or 'negative' (for text) and 'image' or 'load' for reference.
        This is more robust than pure heuristics. If no matching nodes found, the workflow
        is likely incompatible - user must adjust in ComfyUI.
        """
        wf = dict(workflow)  # shallow copy
        positive_set = False
        negative_set = False
        for node_id, node in wf.items():
            if node.get("class_type") == "CLIPTextEncode":
                inputs = node.setdefault("inputs", {})
                title = (node.get("_meta", {}) or {}).get("title", "").lower()
                if "text" in inputs:
                    if "positive" in title and not positive_set:
                        inputs["text"] = positive
                        positive_set = True
                    elif "negative" in title and not negative_set:
                        inputs["text"] = negative or "low quality, blurry"
                        negative_set = True
                    elif not positive_set and not inputs.get("text"):
                        # fallback only for first empty
                        inputs["text"] = positive
                        positive_set = True
                    elif not negative_set and "low" in str(inputs.get("text", "")).lower():
                        inputs["text"] = negative or "low quality, blurry"
                        negative_set = True
        if ref_image:
            for node_id, node in wf.items():
                if node.get("class_type") == "LoadImage":
                    title = (node.get("_meta", {}) or {}).get("title", "").lower()
                    if "image" in title or "load" in title or "reference" in title:
                        node.setdefault("inputs", {})["image"] = ref_image
                        break
        if not positive_set:
            # last resort: set first CLIPTextEncode
            for node in wf.values():
                if node.get("class_type") == "CLIPTextEncode" and "text" in node.get("inputs", {}):
                    node["inputs"]["text"] = positive
                    break
        return wf

    # Delegated to client for separation of concerns
    def _queue_prompt(self, workflow: Dict[str, Any]) -> str:
        return self.client.queue_prompt(workflow)

    def _wait_for_result(self, prompt_id: str, output_node: str = "SaveImage") -> List[str]:
        return self.client.wait_for_result(prompt_id, output_node)

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        aspect_ratio: str = "16:9",
        style: str = "",
        seed: Optional[int] = None,
        steps: int = 20,
        cfg: float = 3.5,
        model: str = "flux",
        workflow_file: Optional[str] = None,
        **kwargs  # ignore user_confirmed etc from MCP wrapper
    ) -> Dict[str, Any]:
        """
        Generate an image using ComfyUI + Flux (or configured model).

        Returns dict with:
            - status: success / error
            - images: list of filenames (relative to ComfyUI output dir)
            - prompt: the used prompt
            - note: instructions for user
        """
        log.info(f"[ImageVideo] generate_image: {prompt[:80]}...")

        if not self.client.is_available():
            return {"status": "error", "error": "ComfyUI not reachable", "note": "Start ComfyUI with Flux. Place exported workflow JSON as workflows/visual/flux_image.json (or pass workflow_file)."}

        full_prompt = prompt + (", " + style if style else "")
        workflow = self._load_workflow("flux_image", workflow_file)
        workflow = self._inject_prompt(workflow, full_prompt, negative_prompt)

        try:
            prompt_id = self._queue_prompt(workflow)
            images = self._wait_for_result(prompt_id)
            result = {
                "status": "success",
                "images": images,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "note": "Generated via ComfyUI (Flux recommended). Files in ComfyUI/output. Chain to Designer/3D specialist for refinement."
            }
            if persistent_memory:
                try:
                    persistent_memory.store("image_generation", f"{prompt[:100]} -> {images}")
                except Exception:
                    pass
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "note": "Workflow load failed or ComfyUI error. Ensure workflows/visual/flux_image.json exists (export from ComfyUI) or pass workflow_file."
            }

    def generate_video(
        self,
        prompt: str,
        reference_image: Optional[str] = None,
        duration: int = 5,
        fps: int = 24,
        negative_prompt: str = "",
        seed: Optional[int] = None,
        workflow_file: Optional[str] = None,
        **kwargs  # ignore extra like user_confirmed
    ) -> Dict[str, Any]:
        """
        Generate video (text-to-video or image-to-video).

        reference_image: path or URL to starting frame (for image-to-video, like Grok Imagine).
        Uses Wan 2.2 or similar via ComfyUI (recommended from research).

        Returns similar structure as generate_image.
        """
        log.info(f"[ImageVideo] generate_video: {prompt[:80]} ref={reference_image}")

        if not self.client.is_available():
            return {"status": "error", "error": "ComfyUI not reachable", "note": "Start ComfyUI with Wan. Place exported workflow JSON as workflows/visual/wan_video.json (or pass workflow_file)."}

        workflow = self._load_workflow("wan_video", workflow_file)
        workflow = self._inject_prompt(workflow, prompt, negative_prompt, reference_image)

        try:
            prompt_id = self._queue_prompt(workflow)
            videos = self._wait_for_result(prompt_id, output_node="SaveAnimatedWEBP")
            result = {
                "status": "success",
                "videos": videos,
                "prompt": prompt,
                "reference_image": reference_image,
                "duration": duration,
                "note": "Video via ComfyUI (Wan 2.2 rec.). Use generated image as ref for best results. Chain to 3D assets if needed."
            }
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "note": "Workflow load failed or ComfyUI error. Ensure workflows/visual/wan_video.json exists (export from ComfyUI) or pass workflow_file."
            }


# Singleton for easy import (matches other skills)
image_video_generator = ImageVideoGenerator()


def generate_image(prompt: str, workflow_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Convenience wrapper. workflow_file: optional path to custom ComfyUI JSON (exported from your setup)."""
    valid = {k: v for k, v in kwargs.items() if k in ["aspect_ratio", "style", "negative_prompt", "seed", "steps", "cfg", "model"]}
    return image_video_generator.generate_image(prompt, workflow_file=workflow_file, **valid)


def generate_video(prompt: str, reference_image: Optional[str] = None, workflow_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """Convenience wrapper. Pass reference_image for image-to-video. workflow_file for custom ComfyUI JSON."""
    valid = {k: v for k, v in kwargs.items() if k in ["duration", "fps", "negative_prompt", "seed"]}
    return image_video_generator.generate_video(prompt, reference_image=reference_image, workflow_file=workflow_file, **valid)
