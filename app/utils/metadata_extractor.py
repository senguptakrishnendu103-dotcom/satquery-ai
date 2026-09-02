import os
import re
from typing import Dict, Any, Optional, List

from PIL import Image


class MetadataExtractor:
    """
    Remote-sensing image metadata extractor.

    Responsibilities:
        - Validate supported image formats
        - Extract basic image metadata
        - Extract GeoTIFF geospatial metadata when available
        - Extract band information
        - Detect modality using metadata/filename heuristics
        - Never fabricate acquisition dates or geospatial information

    Supported formats:
        - GeoTIFF / TIFF
        - JP2
        - PNG
        - JPEG / JPG

    Notes:
        Rasterio is preferred for geospatial formats.
        PIL is used as a fallback for ordinary image formats.
    """

    ALLOWED_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".jp2",
    }

    GEOSPATIAL_EXTENSIONS = {
        ".tif",
        ".tiff",
        ".jp2",
    }

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    @staticmethod
    def extract_metadata(
        file_path: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:

        if not file_path:
            return {
                "valid": False,
                "error": "No file path supplied.",
            }

        if not os.path.isfile(file_path):
            return {
                "valid": False,
                "error": f"File not found: {file_path}",
            }

        filename = filename or os.path.basename(file_path)

        ext = os.path.splitext(filename)[1].lower()

        if ext not in MetadataExtractor.ALLOWED_EXTENSIONS:
            return {
                "valid": False,
                "error": (
                    f"Unsupported file type '{ext}'. "
                    "Supported types: PNG, JPG, JPEG, "
                    "GeoTIFF, TIFF and JP2."
                ),
            }

        try:
            file_size_bytes = os.path.getsize(file_path)

            metadata = {
                "valid": True,
                "filename": filename,
                "file_path": file_path,
                "format": MetadataExtractor._get_format(ext),
                "extension": ext,
                "file_size_bytes": file_size_bytes,
                "file_size_kb": round(
                    file_size_bytes / 1024,
                    2,
                ),
                "file_size_mb": round(
                    file_size_bytes / (1024 * 1024),
                    2,
                ),
            }

            # -------------------------------------------------
            # Prefer Rasterio for remote-sensing formats
            # -------------------------------------------------

            if ext in MetadataExtractor.GEOSPATIAL_EXTENSIONS:

                raster_metadata = (
                    MetadataExtractor._extract_rasterio_metadata(
                        file_path=file_path,
                        filename=filename,
                    )
                )

                metadata.update(raster_metadata)

            else:

                image_metadata = (
                    MetadataExtractor._extract_pillow_metadata(
                        file_path=file_path,
                        filename=filename,
                    )
                )

                metadata.update(image_metadata)

            # -------------------------------------------------
            # Modality detection
            # -------------------------------------------------

            metadata["modality"] = (
                MetadataExtractor._detect_modality(
                    filename=filename,
                    metadata=metadata,
                )
            )

            # -------------------------------------------------
            # Acquisition date
            # -------------------------------------------------

            metadata["acquisition_date"] = (
                MetadataExtractor._extract_acquisition_date(
                    filename=filename,
                    metadata=metadata,
                )
            )

            # -------------------------------------------------
            # Validation information
            # -------------------------------------------------

            metadata["validation"] = (
                MetadataExtractor._build_validation_summary(
                    metadata
                )
            )

            return metadata

        except Exception as exc:

            return {
                "valid": False,
                "filename": filename,
                "file_path": file_path,
                "error": (
                    f"Failed to parse image metadata: {str(exc)}"
                ),
            }

    # =========================================================
    # Rasterio metadata
    # =========================================================

    @staticmethod
    def _extract_rasterio_metadata(
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:

        try:
            import rasterio

        except ImportError:

            # Do not make the whole application unusable if
            # Rasterio is not installed.
            #
            # The caller gets explicit information that
            # geospatial metadata could not be extracted.

            return {
                "metadata_source": "PIL/fallback",
                "geospatial_metadata_available": False,
                "geospatial_metadata_error": (
                    "Rasterio is not installed. "
                    "Install rasterio for GeoTIFF/JP2 "
                    "geospatial metadata extraction."
                ),
                "acquisition_date_source": None,
            }

        with rasterio.open(file_path) as src:

            width = src.width
            height = src.height
            count = src.count

            crs = src.crs

            transform = src.transform

            bounds = src.bounds

            resolution = src.res

            dtype = src.dtypes

            nodata = src.nodata

            descriptions = src.descriptions

            tags = src.tags()

            band_metadata = []

            for index in range(1, count + 1):

                band_tags = src.tags(index)

                band_metadata.append(
                    {
                        "index": index,
                        "description": (
                            descriptions[index - 1]
                            if descriptions
                            and index - 1 < len(descriptions)
                            else None
                        ),
                        "dtype": src.dtypes[index - 1],
                        "nodata": src.nodatavals[index - 1],
                        "tags": band_tags,
                    }
                )

            metadata = {
                "metadata_source": "rasterio",

                "width": width,
                "height": height,

                "dimensions": {
                    "width": width,
                    "height": height,
                    "pixels": width * height,
                },

                "band_count": count,

                "bands": band_metadata,

                "data_type": dtype[0] if dtype else None,
                "data_types": dtype,

                "nodata": nodata,

                "crs": (
                    crs.to_string()
                    if crs
                    else None
                ),

                "crs_wkt": (
                    crs.to_wkt()
                    if crs
                    else None
                ),

                "bounds": {
                    "left": bounds.left,
                    "bottom": bounds.bottom,
                    "right": bounds.right,
                    "top": bounds.top,
                },

                "resolution": {
                    "x": resolution[0],
                    "y": resolution[1],
                },

                "transform": [
                    transform.a,
                    transform.b,
                    transform.c,
                    transform.d,
                    transform.e,
                    transform.f,
                ],

                "geospatial_metadata_available": (
                    crs is not None
                ),

                "dataset_tags": tags,

                "color_mode": (
                    "multiband"
                    if count > 1
                    else "single_band"
                ),
            }

            # Extract possible acquisition date from
            # actual raster metadata.
            metadata["raster_acquisition_date"] = (
                MetadataExtractor._find_date_in_metadata(
                    tags
                )
            )

            return metadata

    # =========================================================
    # PIL metadata for ordinary images
    # =========================================================

    @staticmethod
    def _extract_pillow_metadata(
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:

        with Image.open(file_path) as img:

            width, height = img.size

            exif = img.getexif()

            exif_data = {}

            if exif:

                for tag_id, value in exif.items():

                    exif_data[str(tag_id)] = value

            return {
                "metadata_source": "PIL",

                "width": width,
                "height": height,

                "dimensions": {
                    "width": width,
                    "height": height,
                    "pixels": width * height,
                },

                "band_count": len(
                    img.getbands()
                ),

                "bands": [
                    {
                        "index": index + 1,
                        "description": band,
                    }
                    for index, band
                    in enumerate(img.getbands())
                ],

                "data_type": None,

                "nodata": None,

                "crs": None,
                "crs_wkt": None,

                "bounds": None,
                "resolution": None,
                "transform": None,

                "geospatial_metadata_available": False,

                "color_mode": img.mode,

                "exif": exif_data,

                "raster_acquisition_date": (
                    MetadataExtractor._extract_exif_date(
                        exif
                    )
                ),
            }

    # =========================================================
    # Modality detection
    # =========================================================

    @staticmethod
    def _detect_modality(
        filename: str,
        metadata: Dict[str, Any],
    ) -> str:

        filename_lower = filename.lower()

        # -----------------------------------------------------
        # SAR indicators
        # -----------------------------------------------------

        sar_patterns = [
            r"\bsar\b",
            r"sentinel[-_ ]?1",
            r"\brs2\b",
            r"risat",
            r"alos[-_ ]?palsar",
            r"radarsat",
            r"terrasar",
            r"cosmo[-_ ]?skymed",
        ]

        for pattern in sar_patterns:

            if re.search(
                pattern,
                filename_lower,
            ):
                return "SAR"

        # -----------------------------------------------------
        # SAR metadata indicators
        # -----------------------------------------------------

        tags = metadata.get(
            "dataset_tags",
            {},
        )

        tag_text = " ".join(
            f"{key} {value}"
            for key, value in tags.items()
        ).lower()

        if any(
            token in tag_text
            for token in (
                "sentinel-1",
                "sentinel1",
                "sar",
                "radar",
                "backscatter",
                "sigma0",
                "sigma_0",
                "vv",
                "vh",
                "hh",
                "hv",
            )
        ):
            return "SAR"

        # -----------------------------------------------------
        # Multispectral indicators
        # -----------------------------------------------------

        multispectral_patterns = [
            r"multispectral",
            r"sentinel[-_ ]?2",
            r"\bs2\b",
            r"landsat",
            r"cartosat",
            r"worldview",
            r"planet",
        ]

        for pattern in multispectral_patterns:

            if re.search(
                pattern,
                filename_lower,
            ):
                return "Optical Multispectral"

        # -----------------------------------------------------
        # Band count can provide a weak indication
        # -----------------------------------------------------

        band_count = metadata.get(
            "band_count"
        )

        if (
            isinstance(band_count, int)
            and band_count > 3
        ):
            return "Optical Multispectral"

        if (
            isinstance(band_count, int)
            and band_count == 3
        ):
            return "Optical RGB"

        # -----------------------------------------------------
        # Don't incorrectly classify grayscale as SAR.
        # -----------------------------------------------------

        return "Optical / Unknown"

    # =========================================================
    # Acquisition date
    # =========================================================

    @staticmethod
    def _extract_acquisition_date(
        filename: str,
        metadata: Dict[str, Any],
    ) -> Optional[str]:

        # First preference: actual raster metadata.
        raster_date = metadata.get(
            "raster_acquisition_date"
        )

        if raster_date:
            return str(raster_date)

        # Second preference: actual EXIF.
        exif_date = metadata.get(
            "exif_acquisition_date"
        )

        if exif_date:
            return str(exif_date)

        # Third preference: safely recognize an actual
        # date encoded in the filename.
        #
        # This does NOT turn "2024" into a fake date.
        date_from_filename = (
            MetadataExtractor._extract_date_from_filename(
                filename
            )
        )

        if date_from_filename:
            return date_from_filename

        # Correct behavior when unavailable.
        return None

    @staticmethod
    def _extract_exif_date(
        exif: Any,
    ) -> Optional[str]:

        if not exif:
            return None

        # EXIF 306 = DateTime
        value = exif.get(306)

        if value:
            return str(value)

        # EXIF 36867 = DateTimeOriginal
        value = exif.get(36867)

        if value:
            return str(value)

        return None

    @staticmethod
    def _find_date_in_metadata(
        tags: Dict[str, Any],
    ) -> Optional[str]:

        if not tags:
            return None

        possible_keys = [
            "acquisition_date",
            "acquisition_datetime",
            "datetime",
            "date_acquired",
            "sensing_time",
            "sensing_date",
            "date",
            "timestamp",
        ]

        lowered = {
            str(key).lower(): value
            for key, value in tags.items()
        }

        for key in possible_keys:

            value = lowered.get(key)

            if value:
                return str(value)

        # Some satellite products use longer metadata
        # structures. Search keys conservatively.
        for key, value in lowered.items():

            if (
                "acquisition" in key
                or "sensing" in key
            ) and value:

                return str(value)

        return None

    @staticmethod
    def _extract_date_from_filename(
        filename: str,
    ) -> Optional[str]:

        # YYYY-MM-DD
        match = re.search(
            r"(20\d{2})[-_](\d{2})[-_](\d{2})",
            filename,
        )

        if match:

            return (
                f"{match.group(1)}-"
                f"{match.group(2)}-"
                f"{match.group(3)}"
            )

        # YYYYMMDD
        match = re.search(
            r"(20\d{2})(\d{2})(\d{2})",
            filename,
        )

        if match:

            return (
                f"{match.group(1)}-"
                f"{match.group(2)}-"
                f"{match.group(3)}"
            )

        return None

    # =========================================================
    # Format
    # =========================================================

    @staticmethod
    def _get_format(
        extension: str,
    ) -> str:

        formats = {
            ".tif": "GeoTIFF",
            ".tiff": "GeoTIFF",
            ".jp2": "JPEG2000",
            ".png": "PNG",
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
        }

        return formats.get(
            extension,
            extension.replace(
                ".",
                "",
            ).upper(),
        )

    # =========================================================
    # Validation summary
    # =========================================================

    @staticmethod
    def _build_validation_summary(
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        warnings: List[str] = []

        if not metadata.get("crs"):
            if metadata.get("format") == "GeoTIFF":
                warnings.append(
                    "GeoTIFF has no CRS information."
                )

        if metadata.get("acquisition_date") is None:
            warnings.append(
                "Acquisition date unavailable."
            )

        if metadata.get("band_count", 0) <= 0:
            warnings.append(
                "No image bands detected."
            )

        return {
            "is_geospatial": bool(
                metadata.get(
                    "geospatial_metadata_available",
                    False,
                )
            ),

            "has_crs": bool(
                metadata.get("crs")
            ),

            "has_acquisition_date": (
                metadata.get(
                    "acquisition_date"
                ) is not None
            ),

            "has_band_information": (
                metadata.get("band_count", 0) > 0
            ),

            "warnings": warnings,
        }