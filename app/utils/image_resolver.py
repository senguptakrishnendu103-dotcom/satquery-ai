import base64
import io
import logging
import os
import uuid
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
    def process_object_grounding(img: Image.Image, query: str) -> Dict[str, Any]:
        """Heuristic grounding fallback that returns evidence, not model confidence."""
        if not isinstance(img, Image.Image):
            raise ValueError("Grounding requires a PIL image.")
        if not query or not query.strip():
            raise ValueError("Grounding requires a non-empty query.")

        arr = np.asarray(img, dtype=np.float32)
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        gray = np.mean(arr, axis=2)
        q = query.lower()

        if any(k in q for k in ("water", "river", "lake", "ocean", "sea", "reservoir")):
            label = "Water body"
            mask = (b > r + 15) & (b > 60)
        elif any(k in q for k in ("ship", "vessel", "boat", "plane", "aircraft")):
            label = "Bright target"
            mask = gray > np.mean(gray) + 1.8 * np.std(gray)
        elif any(k in q for k in ("building", "urban", "structure", "industrial", "panel", "solar")):
            label = "Built infrastructure"
            edge = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32)
            mask = edge > 90
        elif any(k in q for k in ("forest", "tree", "vegetation", "crop", "farm", "green")):
            label = "Vegetation canopy"
            mask = (g > r + 10) & (g > b + 5)
        else:
            label = "Salient high-contrast region"
            mask = np.abs(gray - np.mean(gray)) > 1.2 * np.std(gray)

        boxes = ImageResolver._grid_boxes(mask, 5, 5, 0.12)[:8]
        for box in boxes:
            box["label"] = label

        return {
            "target_feature": label,
            "boxes": boxes,
            "overlay_url": ImageResolver.save_mask_overlay(mask, "grounding_mask"),
            "count": len(boxes),
            "method": "heuristic_image_grounding",
            "confidence": None,
            "confidence_note": "Heuristic segmentation is not a calibrated grounding model.",
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
            "confidence": None,
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
            "confidence": None,
            "confidence_note": "RGB texture proxy; not equivalent to multispectral NDBI.",
        }

    @staticmethod
    def process_vqa_and_caption(img: Image.Image, query: str) -> Dict[str, Any]:
        """Deterministic RGB scene statistics for non-VLM fallback paths."""
        if not isinstance(img, Image.Image):
            raise ValueError("VQA/captioning requires a PIL image.")

        arr = np.asarray(img, dtype=np.float32)
        h, w = arr.shape[:2]
        r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
        brightness, contrast = round(float(arr.mean()), 2), round(float(arr.std()), 2)

        water = (b > r + 15) & (b > 50)
        vegetation = (g > r + 10) & (g > b + 5) & ~water
        urban = (~water) & (~vegetation) & (np.abs(r - g) < 25) & (np.abs(g - b) < 25)
        total = float(w * h)

        water_pct = round(float(water.sum() / total * 100), 2)
        vegetation_pct = round(float(vegetation.sum() / total * 100), 2)
        urban_pct = round(float(urban.sum() / total * 100), 2)
        other_pct = round(max(0.0, 100.0 - water_pct - vegetation_pct - urban_pct), 2)

        covers = [
            ("Water body", water_pct),
            ("Dense vegetation", vegetation_pct),
            ("Urban / built-up area", urban_pct),
            ("Bare soil / other", other_pct),
        ]
        covers.sort(key=lambda item: item[1], reverse=True)
        dominant, pct = covers[0]
        q = (query or "").lower()

        if any(k in q for k in ("water", "river", "ocean", "lake")):
            answer = f"RGB analysis estimates {water_pct}% surface-water-like pixels."
        elif any(k in q for k in ("building", "urban", "structure")):
            answer = f"RGB analysis estimates {urban_pct}% pixels matching the configured built-up heuristic."
        else:
            answer = f"The display raster is dominated by {dominant.lower()} ({pct}%)."

        answer += f" Image size is {w}x{h}; mean brightness is {brightness} and contrast is {contrast}."

        return {
            "answer": answer,
            "confidence": None,
            "confidence_note": "Deterministic RGB heuristic; not a trained VLM/VQA model.",
            "dimensions": f"{w}x{h}",
            "dominant_land_cover": dominant,
            "land_cover_distribution": {
                "water_pct": water_pct,
                "vegetation_pct": vegetation_pct,
                "urban_pct": urban_pct,
                "other_pct": other_pct,
            },
            "brightness": brightness,
            "contrast": contrast,
            "method": "deterministic_rgb_scene_statistics",
        }
