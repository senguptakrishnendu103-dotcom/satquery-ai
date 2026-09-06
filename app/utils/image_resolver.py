import base64
import io
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import requests
from PIL import Image, ImageFilter

try:
    import rasterio
except ImportError:  # pragma: no cover
    rasterio = None

logger = logging.getLogger("satquery.utils.image_resolver")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ImageResolver:
    """Resolve and process real remote-sensing assets.

    No synthetic satellite image is generated when input resolution fails.
    Missing or unreadable assets raise explicit errors so the backend cannot
    silently produce plausible-looking fake analysis.
    """

    @staticmethod
    def load_image(obs: Dict[str, Any]) -> Image.Image:
        """Load an observation as a displayable RGB PIL image."""
        if not isinstance(obs, dict):
            raise ValueError("Observation must be a dictionary.")

        image = obs.get("image")
        if isinstance(image, Image.Image):
            return image.convert("RGB")

        array = obs.get("array")
        if isinstance(array, np.ndarray):
            return ImageResolver._numpy_to_rgb(array)

        target = ImageResolver._resolve_target(obs)
        if not target:
            raise ValueError("No model-readable image path or URL was supplied.")

        local_path = ImageResolver._resolve_local_path(target)
        if local_path:
            return ImageResolver._load_local_as_rgb(local_path, obs)

        if target.startswith("/api/"):
            target = f"http://127.0.0.1:8000{target}"

        if target.startswith(("http://", "https://")):
            return ImageResolver._load_remote_image(target)

        if target.startswith("data:image/"):
            try:
                _, encoded = target.split(",", 1)
                return Image.open(io.BytesIO(base64.b64decode(encoded))).convert("RGB")
            except Exception as exc:
                raise ValueError(f"Invalid base64 image data: {exc}") from exc

        raise FileNotFoundError(f"Unable to resolve observation asset: {target}")

    @staticmethod
    def _resolve_target(obs: Dict[str, Any]) -> Optional[str]:
        for key in (
            "file_path", "filePath", "local_path", "localPath", "image_path",
            "path", "url", "imageUrl", "image_url", "thumbnail_url"
        ):
            value = obs.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _resolve_local_path(target: str) -> Optional[str]:
        if target.startswith("file:///"):
            path = target[8:].replace("/", os.sep)
            if os.name == "nt" and len(path) >= 3 and path[0] == os.sep:
                path = path[1:]
            return path if os.path.isfile(path) else None

        if os.path.isabs(target) and os.path.isfile(target):
            return target

        if os.path.isfile(target):
            return os.path.abspath(target)

        base_joined = os.path.join(BASE_DIR, target)
        if os.path.isfile(base_joined):
            return base_joined

        clean = target.lstrip("/")
        if clean.startswith("static/"):
            path = os.path.join(STATIC_DIR, clean[len("static/"):])
            return path if os.path.isfile(path) else None

        basename = os.path.basename(target)
        upload_path = os.path.join(UPLOAD_DIR, basename) if basename else ""
        if upload_path and os.path.isfile(upload_path):
            return upload_path

        return None

    @staticmethod
    def _load_local_as_rgb(path: str, obs: Dict[str, Any]) -> Image.Image:
        raster_ext = (".tif", ".tiff", ".jp2", ".j2k", ".img", ".vrt")
        if path.lower().endswith(raster_ext) or rasterio is not None:
            try:
                if rasterio is not None:
                    return ImageResolver._load_raster_as_rgb(path, obs)
            except Exception as raster_exc:
                if path.lower().endswith(raster_ext):
                    raise ValueError(f"Unable to open remote-sensing raster '{path}': {raster_exc}") from raster_exc

        try:
            with Image.open(path) as img:
                return img.convert("RGB")
        except Exception as exc:
            raise ValueError(f"Unable to open image asset '{path}': {exc}") from exc

    @staticmethod
    def _load_remote_image(url: str) -> Image.Image:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with Image.open(io.BytesIO(response.content)) as img:
                return img.convert("RGB")
        except Exception as exc:
            raise ValueError(f"Unable to download/open image URL: {exc}") from exc

    @staticmethod
    def _numpy_to_rgb(array: np.ndarray) -> Image.Image:
        arr = np.asarray(array)
        if arr.ndim == 2:
            gray = ImageResolver._normalize_band(arr)
            return Image.fromarray(gray, mode="L").convert("RGB")

        if arr.ndim == 3:
            if arr.shape[0] <= 32 and arr.shape[1] > 64 and arr.shape[2] > 64:
                arr = np.moveaxis(arr, 0, -1)
            if arr.shape[-1] == 1:
                gray = ImageResolver._normalize_band(arr[..., 0])
                return Image.fromarray(gray, mode="L").convert("RGB")
            if arr.shape[-1] >= 3:
                rgb = np.stack([ImageResolver._normalize_band(arr[..., i]) for i in range(3)], axis=-1)
                return Image.fromarray(rgb.astype(np.uint8), mode="RGB")

        raise ValueError(f"Unsupported numpy image shape {arr.shape}.")

    @staticmethod
    def _normalize_band(band: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
        arr = np.asarray(band, dtype=np.float32)
        valid = np.isfinite(arr)
        if not np.any(valid):
            return np.zeros(arr.shape, dtype=np.uint8)

        values = arr[valid]
        lo = float(np.percentile(values, low))
        hi = float(np.percentile(values, high))
        if hi <= lo:
            lo, hi = float(values.min()), float(values.max())
        if hi <= lo:
            return np.zeros(arr.shape, dtype=np.uint8)

        out = np.clip((arr - lo) / (hi - lo), 0.0, 1.0)
        out[~valid] = 0.0
        return (out * 255.0).astype(np.uint8)

    @staticmethod
    def _extract_band_map(obs: Dict[str, Any]) -> Dict[str, Any]:
        for source in (
            obs.get("band_map"),
            (obs.get("metadata") or {}).get("band_map") if isinstance(obs.get("metadata"), dict) else None,
            (obs.get("product_metadata") or {}).get("band_map") if isinstance(obs.get("product_metadata"), dict) else None,
        ):
            if isinstance(source, dict):
                return source
        return {}

    @staticmethod
    def _band_index(band_map: Dict[str, Any], aliases: Tuple[str, ...], default: int) -> int:
        normalized = {str(k).lower(): v for k, v in band_map.items()}
        for alias in aliases:
            if alias.lower() not in normalized:
                continue
            value = normalized[alias.lower()]
            if isinstance(value, (list, tuple)) and len(value) > 0:
                value = value[0]
            if isinstance(value, dict):
                value = value.get("index") or value.get("band") or value.get("band_index")
            try:
                return int(value)
            except (TypeError, ValueError):
                pass
        return default

    @staticmethod
    def _load_raster_as_rgb(path: str, obs: Dict[str, Any]) -> Image.Image:
        if rasterio is None:
            raise RuntimeError("Rasterio is required for GeoTIFF/JP2 assets.")

        with rasterio.open(path) as src:
            if src.count < 1:
                raise ValueError("Raster contains no bands.")

            band_map = ImageResolver._extract_band_map(obs)
            red = ImageResolver._band_index(band_map, ("red", "b04", "band_4"), 1)
            green = ImageResolver._band_index(band_map, ("green", "b03", "band_3"), min(2, src.count))
            blue = ImageResolver._band_index(band_map, ("blue", "b02", "band_2"), min(3, src.count))

            red = max(1, min(red, src.count))
            green = max(1, min(green, src.count))
            blue = max(1, min(blue, src.count))

            rgb = np.stack([
                ImageResolver._normalize_band(src.read(red)),
                ImageResolver._normalize_band(src.read(green)),
                ImageResolver._normalize_band(src.read(blue)),
            ], axis=-1)
            return Image.fromarray(rgb, mode="RGB")

    @staticmethod
    def ensure_displayable_preview(raster_path: str, output_dir: Optional[str] = None) -> str:
        """
        Ensure a browser-renderable RGB PNG preview exists for any GeoTIFF / JP2 / TIFF raster
        and return its public URL. If already a PNG/JPEG, return its direct URL.
        """
        p = Path(raster_path).resolve()
        suffix = p.suffix.lower()

        if suffix in [".png", ".jpg", ".jpeg", ".webp"]:
            return f"/static/uploads/{p.name}"

        out_dir = Path(output_dir) if output_dir else Path(UPLOAD_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)

        preview_name = f"{p.stem}_preview.png"
        preview_path = out_dir / preview_name

        if not preview_path.exists() or preview_path.stat().st_size == 0:
            try:
                rgb_img = ImageResolver._load_raster_as_rgb(str(p), {})
                rgb_img.save(str(preview_path), format="PNG")
            except Exception:
                return f"/static/uploads/{p.name}"

        return f"/static/uploads/{preview_name}"

    @staticmethod
    def save_mask_overlay(mask_arr: np.ndarray, prefix: str = "overlay") -> str:
        """Save a 2-D mask as a transparent evidence overlay."""
        mask = np.asarray(mask_arr)
        if mask.ndim != 2:
            raise ValueError(f"Mask must be 2-D, got {mask.shape}.")

        active = mask > 0
        rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
        rgba[active, 1] = 255
        rgba[active, 2] = 180
        rgba[active, 3] = 160

        filename = f"{prefix}_{uuid.uuid4().hex[:10]}.png"
        filepath = os.path.join(UPLOAD_DIR, filename)
        Image.fromarray(rgba, mode="RGBA").save(filepath, format="PNG")
        return f"/static/uploads/{filename}"

    @staticmethod
    def _grid_boxes(mask: np.ndarray, rows: int, cols: int, min_density: float):
        h, w = mask.shape
        boxes = []
        cell_h = max(1, h // rows)
        cell_w = max(1, w // cols)

        for r in range(rows):
            for c in range(cols):
                y0, x0 = r * cell_h, c * cell_w
                y1 = h if r == rows - 1 else min(h, (r + 1) * cell_h)
                x1 = w if c == cols - 1 else min(w, (c + 1) * cell_w)
                cell = mask[y0:y1, x0:x1]
                if cell.size == 0:
                    continue
                density = float(np.mean(cell))
                if density >= min_density:
                    boxes.append({
                        "x": round(x0 / w * 100.0, 2),
                        "y": round(y0 / h * 100.0, 2),
                        "w": round((x1 - x0) / w * 100.0, 2),
                        "h": round((y1 - y0) / h * 100.0, 2),
                        "density": round(density, 4),
                    })

        boxes.sort(key=lambda item: item["density"], reverse=True)
        return boxes

    @staticmethod
    def process_bi_temporal_change(
        img_a: Image.Image,
        img_b: Image.Image,
        threshold: float = 0.25,
        pixel_size_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Deterministic normalized pixel-difference change heuristic."""
        if not isinstance(img_a, Image.Image) or not isinstance(img_b, Image.Image):
            raise ValueError("Bi-temporal comparison requires two PIL images.")
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be between 0 and 1.")

        w, h = img_a.size
        img_b = img_b.resize((w, h), Image.Resampling.BILINEAR)
        arr_a = np.asarray(img_a, dtype=np.float32)
        arr_b = np.asarray(img_b, dtype=np.float32)

        diff = np.mean(np.abs(arr_a - arr_b), axis=2)
        lo, hi = float(np.percentile(diff, 2)), float(np.percentile(diff, 98))
        diff_norm = np.zeros_like(diff) if hi <= lo else np.clip((diff - lo) / (hi - lo), 0.0, 1.0)
        mask = diff_norm > threshold

        changed_pixels = int(mask.sum())
        total_pixels = int(mask.size)
        changed_pct = round(changed_pixels / total_pixels * 100.0, 2)

        boxes = ImageResolver._grid_boxes(mask, 4, 4, 0.15)
        for box in boxes:
            box["label"] = f"Changed region ({round(box['density'] * 100, 1)}%)"

        area_sqkm = None
        if pixel_size_m is not None:
            if pixel_size_m <= 0:
                raise ValueError("pixel_size_m must be positive.")
            area_sqkm = round(changed_pixels * pixel_size_m ** 2 / 1_000_000.0, 4)

        return {
            "changed_percentage": changed_pct,
            "changed_area_sqkm": area_sqkm,
            "changed_pixels": changed_pixels,
            "total_pixels": total_pixels,
            "boxes": boxes,
            "overlay_url": ImageResolver.save_mask_overlay(mask, "change_mask"),
            "method": "normalized_absolute_display_difference",
            "threshold": threshold,
            "confidence": None,
            "confidence_note": "Deterministic thresholding; no calibrated model confidence.",
        }

    @staticmethod
    def process_water_detection(img: Image.Image, threshold: float = 0.15) -> Dict[str, Any]:
        """RGB water proxy. Use real Green/NIR NDWI for multispectral analysis."""
        if not isinstance(img, Image.Image):
            raise ValueError("Water detection requires a PIL image.")
        arr = np.asarray(img, dtype=np.float32)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        ndwi_rgb = (g - r) / (g + r + 1e-6)
        mask = (ndwi_rgb >= threshold) | ((b > g + 10) & (b > r + 20))

        return {
            "water_percentage": round(float(mask.mean() * 100.0), 2),
            "water_pixels": int(mask.sum()),
            "total_pixels": int(mask.size),
            "ndwi_min": round(float(ndwi_rgb.min()), 4),
            "ndwi_max": round(float(ndwi_rgb.max()), 4),
            "ndwi_mean": round(float(ndwi_rgb.mean()), 4),
            "threshold": threshold,
            "overlay_url": ImageResolver.save_mask_overlay(mask, "ndwi_water"),
            "method": "rgb_ndwi_proxy",
            "confidence": 0.0,
            "confidence_note": "RGB proxy; not equivalent to multispectral Green/NIR NDWI.",
        }

    @staticmethod
    def process_builtup_detection(img: Image.Image, threshold: float = 0.10) -> Dict[str, Any]:
        """RGB built-up texture proxy. Use real NIR/SWIR NDBI for multispectral analysis."""
        if not isinstance(img, Image.Image):
            raise ValueError("Built-up detection requires a PIL image.")
        arr = np.asarray(img, dtype=np.float32)
        r, g = arr[..., 0], arr[..., 1]
        edges = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
        idx = ((r - g) / (r + g + 1e-6)) + edges * 0.5
        mask = idx >= threshold

        return {
            "builtup_percentage": round(float(mask.mean() * 100.0), 2),
            "builtup_pixels": int(mask.sum()),
            "total_pixels": int(mask.size),
            "index_min": round(float(idx.min()), 4),
            "index_max": round(float(idx.max()), 4),
            "index_mean": round(float(idx.mean()), 4),
            "threshold": threshold,
            "overlay_url": ImageResolver.save_mask_overlay(mask, "builtup_proxy"),
            "method": "rgb_builtup_texture_proxy",
            "confidence": 0.0,
            "confidence_note": "RGB texture proxy; not equivalent to multispectral NDBI.",
        }

