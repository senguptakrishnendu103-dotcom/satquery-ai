"""
SatQuery AI - Remote-Sensing Metadata Extractor.

Responsibilities
----------------
- Validate supported raster/image formats.
- Extract file information.
- Extract Rasterio geospatial metadata.
- Extract band metadata.
- Detect likely remote-sensing modality.
- Extract acquisition date from genuine metadata/filename values.
- Build a validation summary.
- Build a normalized band map that downstream processing tools can use.

Important
---------
This module DOES NOT load the full raster into memory.

Pixel/band processing should be performed by a dedicated raster-processing
layer immediately before model/tool execution.
"""

import os
import re

from datetime import (
    datetime,
)

from typing import (
    Dict,
    Any,
    Optional,
    List,
    Tuple,
)


from PIL import Image

from app.utils.isro_adapter import ISROProductAdapter


class MetadataExtractor:
    """
    Remote-sensing image metadata extractor.

    Supported formats:
        - GeoTIFF / TIFF
        - JP2
        - PNG
        - JPEG / JPG

    Rasterio is preferred for geospatial formats.
    PIL is used for ordinary image files.
    """

    # ============================================================
    # SUPPORTED FILES
    # ============================================================

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

    # ============================================================
    # PUBLIC API
    # ============================================================

    @staticmethod
    def extract_metadata(
        file_path: str,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract normalized metadata from an uploaded observation.

        Returns a dictionary containing:
            - validation information
            - file information
            - dimensions
            - band information
            - geospatial information
            - modality
            - acquisition date
            - band map
        """

        # --------------------------------------------------------
        # File existence
        # --------------------------------------------------------

        if not file_path:

            return {
                "valid": False,
                "error":
                    "No file path supplied.",
            }

        if not os.path.isfile(
            file_path
        ):

            return {
                "valid": False,
                "error":
                    f"File not found: {file_path}",
            }

        # --------------------------------------------------------
        # Filename
        # --------------------------------------------------------

        filename = (
            filename
            or os.path.basename(
                file_path
            )
        )

        ext = (
            os.path.splitext(
                filename
            )[1]
            .lower()
        )

        # --------------------------------------------------------
        # Extension validation
        # --------------------------------------------------------

        if (
            ext
            not in MetadataExtractor.ALLOWED_EXTENSIONS
        ):

            return {
                "valid": False,
                "error": (
                    f"Unsupported file type '{ext}'. "
                    "Supported types: PNG, JPG, JPEG, "
                    "GeoTIFF, TIFF and JP2."
                ),
            }

        # --------------------------------------------------------
        # Extraction
        # --------------------------------------------------------

        try:

            file_size_bytes = (
                os.path.getsize(
                    file_path
                )
            )

            metadata: Dict[str, Any] = {

                "valid":
                    True,

                "filename":
                    filename,

                "file_path":
                    file_path,

                "format":
                    MetadataExtractor._get_format(
                        ext
                    ),

                "extension":
                    ext,

                "file_size_bytes":
                    file_size_bytes,

                "file_size_kb":
                    round(
                        file_size_bytes / 1024,
                        2,
                    ),

                "file_size_mb":
                    round(
                        file_size_bytes /
                        (1024 * 1024),
                        2,
                    ),

                "metadata_source":
                    None,

                "modality":
                    None,

                "acquisition_date":
                    None,

                "band_map":
                    {},
            }

            # ----------------------------------------------------
            # Rasterio for remote-sensing formats
            # ----------------------------------------------------

            if (
                ext
                in MetadataExtractor.GEOSPATIAL_EXTENSIONS
            ):

                raster_metadata = (
                    MetadataExtractor
                    ._extract_rasterio_metadata(
                        file_path=file_path,
                        filename=filename,
                    )
                )

                metadata.update(
                    raster_metadata
                )

            # ----------------------------------------------------
            # PIL for ordinary images
            # ----------------------------------------------------

            else:

                image_metadata = (
                    MetadataExtractor
                    ._extract_pillow_metadata(
                        file_path=file_path,
                        filename=filename,
                    )
                )

                metadata.update(
                    image_metadata
                )

            # ----------------------------------------------------
            # ISRO / SAC Mission & Metadata Detection
            # ----------------------------------------------------

            isro_info = ISROProductAdapter.detect_isro_product(
                file_path=file_path,
                filename=filename,
                dataset_tags=metadata.get("tags") or metadata.get("dataset_tags"),
            )

            if isro_info:
                metadata["isro_metadata"] = isro_info
                metadata["is_isro_product"] = True
                metadata["isro_mission"] = isro_info.get("mission")
                metadata["isro_sensor"] = isro_info.get("sensor")
                metadata["isro_product_id"] = isro_info.get("product_id")
                metadata["isro_provider"] = isro_info.get("provider")
                if isro_info.get("platform"):
                    metadata["platform"] = isro_info["platform"]
                if isro_info.get("sensor"):
                    metadata["sensor"] = isro_info["sensor"]
                if isro_info.get("spatial_resolution_m"):
                    metadata["spatial_resolution_m"] = isro_info["spatial_resolution_m"]
                if isro_info.get("xml_metadata_path"):
                    metadata["xml_metadata_path"] = isro_info["xml_metadata_path"]
                if isro_info.get("acquisition_date"):
                    metadata["isro_acquisition_date"] = isro_info["acquisition_date"]
            else:
                metadata["is_isro_product"] = False

            # ----------------------------------------------------
            # Modality
            # ----------------------------------------------------

            metadata[
                "modality"
            ] = (
                MetadataExtractor
                ._detect_modality(
                    filename=filename,
                    metadata=metadata,
                )
            )

            # ----------------------------------------------------
            # Acquisition date
            # ----------------------------------------------------

            metadata[
                "acquisition_date"
            ] = (
                MetadataExtractor
                ._extract_acquisition_date(
                    filename=filename,
                    metadata=metadata,
                )
            )

            # ----------------------------------------------------
            # Band map
            # ----------------------------------------------------

            metadata[
                "band_map"
            ] = (
                MetadataExtractor
                ._build_band_map(
                    metadata
                )
            )

            # ----------------------------------------------------
            # Derived normalized fields
            # ----------------------------------------------------

            metadata[
                "sensor"
            ] = (
                MetadataExtractor
                ._infer_sensor(
                    filename=filename,
                    metadata=metadata,
                )
            )

            metadata[
                "platform"
            ] = (
                MetadataExtractor
                ._infer_platform(
                    filename=filename,
                    metadata=metadata,
                )
            )

            # ----------------------------------------------------
            # Validation
            # ----------------------------------------------------

            metadata[
                "validation"
            ] = (
                MetadataExtractor
                ._build_validation_summary(
                    metadata
                )
            )

            return metadata

        except Exception as exc:

            return {
                "valid":
                    False,

                "filename":
                    filename,

                "file_path":
                    file_path,

                "error":
                    (
                        "Failed to parse image metadata: "
                        f"{str(exc)}"
                    ),
            }

    # ============================================================
    # RASTERIO METADATA
    # ============================================================

    @staticmethod
    def _extract_rasterio_metadata(
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:
        """
        Extract geospatial/raster metadata without loading the
        complete image into memory.
        """

        try:

            import rasterio

        except ImportError:

            return {
                "metadata_source":
                    "PIL/fallback",

                "geospatial_metadata_available":
                    False,

                "geospatial_metadata_error":
                    (
                        "Rasterio is not installed. "
                        "Install rasterio for GeoTIFF/JP2 "
                        "geospatial metadata extraction."
                    ),

                "acquisition_date_source":
                    None,

                "band_map":
                    {},
            }

        with rasterio.open(
            file_path
        ) as src:

            width = (
                src.width
            )

            height = (
                src.height
            )

            count = (
                src.count
            )

            crs = (
                src.crs
            )

            transform = (
                src.transform
            )

            bounds = (
                src.bounds
            )

            resolution = (
                src.res
            )

            dtypes = (
                list(
                    src.dtypes
                )
            )

            nodata = (
                src.nodata
            )

            descriptions = (
                src.descriptions
            )

            dataset_tags = (
                src.tags()
            )

            # ----------------------------------------------------
            # Band metadata
            # ----------------------------------------------------

            band_metadata: List[
                Dict[str, Any]
            ] = []

            for index in range(
                1,
                count + 1,
            ):

                band_tags = (
                    src.tags(
                        index
                    )
                )

                description = None

                if (
                    descriptions
                    and
                    index - 1
                    <
                    len(
                        descriptions
                    )
                ):
                    description = (
                        descriptions[
                            index - 1
                        ]
                    )

                band_metadata.append(
                    {
                        "index":
                            index,

                        "description":
                            description,

                        "dtype":
                            (
                                dtypes[
                                    index - 1
                                ]
                                if index - 1
                                < len(
                                    dtypes
                                )
                                else None
                            ),

                        "nodata":
                            (
                                src.nodatavals[
                                    index - 1
                                ]
                                if (
                                    hasattr(
                                        src,
                                        "nodatavals",
                                    )
                                    and
                                    index - 1
                                    <
                                    len(
                                        src.nodatavals
                                    )
                                )
                                else None
                            ),

                        "tags":
                            band_tags,
                    }
                )

            metadata: Dict[
                str,
                Any
            ] = {

                "metadata_source":
                    "rasterio",

                "width":
                    width,

                "height":
                    height,

                "dimensions":
                    {
                        "width":
                            width,

                        "height":
                            height,

                        "pixels":
                            width * height,
                    },

                "band_count":
                    count,

                "bands":
                    band_metadata,

                "data_type":
                    (
                        dtypes[0]
                        if dtypes
                        else None
                    ),

                "data_types":
                    dtypes,

                "nodata":
                    nodata,

                "crs":
                    (
                        crs.to_string()
                        if crs
                        else None
                    ),

                "crs_wkt":
                    (
                        crs.to_wkt()
                        if crs
                        else None
                    ),

                "bounds":
                    {
                        "left":
                            bounds.left,

                        "bottom":
                            bounds.bottom,

                        "right":
                            bounds.right,

                        "top":
                            bounds.top,
                    },

                "bbox":
                    [
                        bounds.left,
                        bounds.bottom,
                        bounds.right,
                        bounds.top,
                    ],

                "resolution":
                    {
                        "x":
                            resolution[0],

                        "y":
                            resolution[1],
                    },

                "spatial_resolution":
                    {
                        "x":
                            resolution[0],

                        "y":
                            resolution[1],
                    },

                "transform":
                    [
                        transform.a,
                        transform.b,
                        transform.c,
                        transform.d,
                        transform.e,
                        transform.f,
                    ],

                "geospatial_metadata_available":
                    crs is not None,

                "dataset_tags":
                    dataset_tags,

                "color_mode":
                    (
                        "multiband"
                        if count > 1
                        else "single_band"
                    ),
            }

            # ----------------------------------------------------
            # Acquisition date
            # ----------------------------------------------------

            metadata[
                "raster_acquisition_date"
            ] = (
                MetadataExtractor
                ._find_date_in_metadata(
                    dataset_tags
                )
            )

            # ----------------------------------------------------
            # Provider/platform metadata
            # ----------------------------------------------------

            metadata[
                "platform"
            ] = (
                MetadataExtractor
                ._find_tag_value(
                    dataset_tags,
                    [
                        "platform",
                        "platform_name",
                        "platformShortName",
                        "satellite",
                        "satellite_name",
                    ],
                )
            )

            metadata[
                "sensor"
            ] = (
                MetadataExtractor
                ._find_tag_value(
                    dataset_tags,
                    [
                        "sensor",
                        "instrument",
                        "instrument_name",
                        "instrumentShortName",
                    ],
                )
            )

            metadata[
                "processing_level"
            ] = (
                MetadataExtractor
                ._find_tag_value(
                    dataset_tags,
                    [
                        "processing_level",
                        "processingLevel",
                    ],
                )
            )

            metadata[
                "product_type"
            ] = (
                MetadataExtractor
                ._find_tag_value(
                    dataset_tags,
                    [
                        "product_type",
                        "productType",
                    ],
                )
            )

            return metadata

    # ============================================================
    # PIL METADATA
    # ============================================================

    @staticmethod
    def _extract_pillow_metadata(
        file_path: str,
        filename: str,
    ) -> Dict[str, Any]:

        with Image.open(
            file_path
        ) as img:

            width, height = (
                img.size
            )

            exif = (
                img.getexif()
            )

            exif_data: Dict[
                str,
                Any
            ] = {}

            if exif:

                for (
                    tag_id,
                    value
                ) in exif.items():

                    try:
                        exif_data[
                            str(tag_id)
                        ] = value

                    except Exception:
                        continue

            bands = list(
                img.getbands()
            )

            return {

                "metadata_source":
                    "PIL",

                "width":
                    width,

                "height":
                    height,

                "dimensions":
                    {
                        "width":
                            width,

                        "height":
                            height,

                        "pixels":
                            width * height,
                    },

                "band_count":
                    len(
                        bands
                    ),

                "bands":
                    [
                        {
                            "index":
                                index + 1,

                            "description":
                                band,
                        }

                        for (
                            index,
                            band
                        )
                        in enumerate(
                            bands
                        )
                    ],

                "data_type":
                    None,

                "data_types":
                    [],

                "nodata":
                    None,

                "crs":
                    None,

                "crs_wkt":
                    None,

                "bounds":
                    None,

                "bbox":
                    None,

                "resolution":
                    None,

                "spatial_resolution":
                    None,

                "transform":
                    None,

                "geospatial_metadata_available":
                    False,

                "color_mode":
                    img.mode,

                "exif":
                    exif_data,

                "raster_acquisition_date":
                    MetadataExtractor
                    ._extract_exif_date(
                        exif
                    ),

                "sensor":
                    None,

                "platform":
                    None,

                "processing_level":
                    None,

                "product_type":
                    None,
            }

    # ============================================================
    # MODALITY DETECTION
    # ============================================================

    @staticmethod
    def _detect_modality(
        filename: str,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Detect likely modality.

        Priority:
            1. Explicit SAR filename/product metadata.
            2. Explicit optical/multispectral metadata.
            3. Satellite naming conventions.
            4. Band count as a weak clue.
        """

        filename_lower = (
            filename.lower()
        )

        # --------------------------------------------------------
        # SAR filename indicators
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # SAR metadata indicators
        # --------------------------------------------------------

        all_tag_text = (
            MetadataExtractor
            ._metadata_text(
                metadata
            )
        )

        if MetadataExtractor._contains_any(
            all_tag_text,
            [
                "sentinel-1",
                "sentinel1",
                "sar",
                "radar",
                "backscatter",
                "sigma0",
                "sigma_0",
                "sigma nought",
                "polarization",
                "polarisation",
                "c-sar",
                "c sar",
            ],
        ):
            return "SAR"

        # --------------------------------------------------------
        # Multispectral satellite indicators
        # --------------------------------------------------------

        multispectral_patterns = [
            r"multispectral",
            r"sentinel[-_ ]?2",
            r"\bs2\b",
            r"landsat",
            r"cartosat",
            r"worldview",
            r"planet",
            r"rapideye",
        ]

        for pattern in multispectral_patterns:

            if re.search(
                pattern,
                filename_lower,
            ):
                return "Optical Multispectral"

        # --------------------------------------------------------
        # Band description analysis
        # --------------------------------------------------------

        band_text = (
            MetadataExtractor
            ._band_description_text(
                metadata
            )
        )

        if MetadataExtractor._contains_any(
            band_text,
            [
                "nir",
                "near infrared",
                "near-infrared",
                "swir",
                "red edge",
                "red-edge",
                "blue",
                "green",
                "red",
            ],
        ):

            return "Optical Multispectral"

        # --------------------------------------------------------
        # Weak band-count signal
        # --------------------------------------------------------

        band_count = metadata.get(
            "band_count"
        )

        if (
            isinstance(
                band_count,
                int,
            )
            and band_count > 3
        ):
            return "Optical Multispectral"

        if (
            isinstance(
                band_count,
                int,
            )
            and band_count == 3
        ):
            return "Optical RGB"

        # --------------------------------------------------------
        # Safe fallback
        # --------------------------------------------------------

        return "Optical / Unknown"

    # ============================================================
    # SENSOR INFERENCE
    # ============================================================

    @staticmethod
    def _infer_sensor(
        filename: str,
        metadata: Dict[str, Any],
    ) -> Optional[str]:

        explicit_sensor = (
            metadata.get(
                "sensor"
            )
        )

        if explicit_sensor:
            return str(
                explicit_sensor
            )

        if metadata.get("is_isro_product") and metadata.get("isro_sensor"):
            return str(metadata["isro_sensor"])

        text = (
            MetadataExtractor
            ._metadata_text(
                metadata
            )
            .lower()
        )

        filename_lower = (
            filename.lower()
        )

        # ISRO / SAC sensors
        if "liss-4" in text or "liss-4" in filename_lower or "liss4" in filename_lower or "l4" in filename_lower:
            return "LISS-4"
        if "liss-3" in text or "liss-3" in filename_lower or "liss3" in filename_lower or "l3" in filename_lower:
            return "LISS-3"
        if "awifs" in text or "awifs" in filename_lower or "aw_" in filename_lower:
            return "AWiFS"
        if "cartosat" in filename_lower or "cartosat" in text:
            if "pan" in filename_lower or "pan" in text:
                return "PAN"
            if "mx" in filename_lower or "mx" in text:
                return "MX"
        if "ocm" in text or "ocm" in filename_lower or "oceansat" in filename_lower:
            return "OCM-3"

        if (
            "sentinel-1"
            in text
            or "sentinel-1"
            in filename_lower
            or "risat"
            in filename_lower
            or "eos-04"
            in filename_lower
            or "eos04"
            in filename_lower
        ):
            return "C-SAR"

        if (
            "sentinel-2"
            in text
            or "sentinel-2"
            in filename_lower
            or "msi"
            in text
            or "msi"
            in filename_lower
            or "s2a"
            in filename_lower
            or "s2b"
            in filename_lower
            or "s2c"
            in filename_lower
        ):
            return "MSI"

        if (
            "landsat"
            in filename_lower
        ):
            return "OLI/TIRS"

        return None

    # ============================================================
    # PLATFORM INFERENCE
    # ============================================================

    @staticmethod
    def _infer_platform(
        filename: str,
        metadata: Dict[str, Any],
    ) -> Optional[str]:

        explicit_platform = (
            metadata.get(
                "platform"
            )
        )

        if explicit_platform:
            return str(
                explicit_platform
            )

        if metadata.get("is_isro_product") and metadata.get("isro_metadata", {}).get("platform"):
            return str(metadata["isro_metadata"]["platform"])

        filename_upper = (
            filename.upper()
        )

        patterns = [
            (
                r"S1A",
                "Sentinel-1A",
            ),
            (
                r"S1B",
                "Sentinel-1B",
            ),
            (
                r"S1C",
                "Sentinel-1C",
            ),
            (
                r"S2A",
                "Sentinel-2A",
            ),
            (
                r"S2B",
                "Sentinel-2B",
            ),
            (
                r"S2C",
                "Sentinel-2C",
            ),
            (
                r"LANDSAT[-_ ]?8",
                "Landsat 8",
            ),
            (
                r"LANDSAT[-_ ]?9",
                "Landsat 9",
            ),
            (
                r"RESOURCESAT[-_ ]?2A|RS2A",
                "Resourcesat-2A",
            ),
            (
                r"RESOURCESAT[-_ ]?2|RS2",
                "Resourcesat-2",
            ),
            (
                r"RESOURCESAT[-_ ]?1|RS1|IRS[-_ ]?P6",
                "Resourcesat-1 (IRS-P6)",
            ),
            (
                r"CARTOSAT[-_ ]?3|CARTO3",
                "Cartosat-3",
            ),
            (
                r"CARTOSAT[-_ ]?2|CARTO2",
                "Cartosat-2",
            ),
            (
                r"CARTOSAT[-_ ]?1|CARTO1",
                "Cartosat-1",
            ),
            (
                r"EOS[-_ ]?0?4|RISAT[-_ ]?1A",
                "EOS-04 (RISAT-1A)",
            ),
            (
                r"RISAT[-_ ]?1",
                "RISAT-1",
            ),
            (
                r"RISAT[-_ ]?2",
                "RISAT-2",
            ),
            (
                r"EOS[-_ ]?0?6|OCEANSAT[-_ ]?3",
                "EOS-06 (Oceansat-3)",
            ),
        ]

        for (
            pattern,
            platform,
        ) in patterns:

            if re.search(
                r"(?:^|[^A-Za-z0-9])(" + pattern + r")(?:[^A-Za-z0-9]|$)",
                filename_upper,
            ):
                return platform

        return None

    # ============================================================
    # BAND MAP
    # ============================================================

    @staticmethod
    def _build_band_map(
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a normalized semantic band map.

        This does not load pixels.

        Example:

            {
                "blue": [2],
                "green": [3],
                "red": [4],
                "nir": [8],
                "swir1": [11],
                "swir2": [12],
                "vv": [1],
                "vh": [2]
            }

        Multiple candidates are preserved as lists because different
        datasets may encode the same semantic band differently.
        """

        result: Dict[
            str,
            List[int]
        ] = {}

        bands = (
            metadata.get(
                "bands"
            )
            or []
        )

        if not isinstance(
            bands,
            list,
        ):
            return result

        for band in bands:

            if not isinstance(
                band,
                dict,
            ):
                continue

            index = band.get(
                "index"
            )

            try:
                index_int = int(
                    index
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            description = str(
                band.get(
                    "description",
                    "",
                )
                or ""
            ).strip().lower()

            tag_text = " ".join(
                f"{key}:{value}"
                for key, value
                in (
                    band.get(
                        "tags"
                    )
                    or {}
                ).items()
            ).lower()

            text = (
                f"{description} "
                f"{tag_text}"
            )

            semantic_names = (
                MetadataExtractor
                ._semantic_band_names(
                    text
                )
            )

            for semantic_name in semantic_names:

                result.setdefault(
                    semantic_name,
                    [],
                )

                if (
                    index_int
                    not in result[
                        semantic_name
                    ]
                ):

                    result[
                        semantic_name
                    ].append(
                        index_int
                    )

        # --------------------------------------------------------
        # Use satellite conventions only when metadata gives enough
        # evidence. Avoid pretending arbitrary band positions are
        # Sentinel-2 bands.
        # --------------------------------------------------------

        platform = str(
            metadata.get(
                "platform",
                ""
            )
            or ""
        ).lower()

        sensor = str(
            metadata.get(
                "sensor",
                ""
            )
            or ""
        ).lower()

        filename = str(
            metadata.get(
                "filename",
                ""
            )
            or ""
        ).lower()

        is_sentinel2 = (
            "sentinel-2"
            in platform
            or "sentinel-2"
            in filename
            or "msi"
            in sensor
        )

        is_sentinel1 = (
            "sentinel-1"
            in platform
            or "sentinel-1"
            in filename
            or "c-sar"
            in sensor
        )

        # --------------------------------------------------------
        # Sentinel-2 fallback semantic map.
        is_landsat = (
            "landsat" in platform
            or "landsat" in filename
            or "oli" in sensor
        )

        # --------------------------------------------------------
        # ISRO / SAC Mission band mapping
        # --------------------------------------------------------
        isro_info = metadata.get("isro_metadata")
        if not isro_info and metadata.get("is_isro_product"):
            isro_info = {
                "sensor": sensor,
                "platform": platform,
                "mission": metadata.get("isro_mission"),
                "modality": metadata.get("modality"),
            }

        if isro_info:
            band_count = metadata.get("band_count")
            if not isinstance(band_count, int):
                band_count = len(metadata.get("bands") or []) or 1

            isro_map = ISROProductAdapter.get_isro_band_map(
                isro_info=isro_info,
                band_count=band_count,
            )
            for name, indices in isro_map.items():
                if name not in result:
                    result[name] = indices
                else:
                    for idx in indices:
                        if idx not in result[name]:
                            result[name].append(idx)

        # --------------------------------------------------------
        # Sentinel-2 fallback semantic map.
        # --------------------------------------------------------

        if is_sentinel2:
            conventions = {
                "blue": 2,
                "green": 3,
                "red": 4,
                "nir": 8,
                "swir1": 11,
                "swir2": 12,
            }

            band_count = metadata.get("band_count")

            for name, index in conventions.items():
                if (
                    name not in result
                    and isinstance(band_count, int)
                    and band_count >= index
                ):
                    result[name] = [index]

        # --------------------------------------------------------
        # Landsat 8/9 fallback semantic map.
        # --------------------------------------------------------

        elif is_landsat:
            conventions = {
                "blue": 2,
                "green": 3,
                "red": 4,
                "nir": 5,
                "swir1": 6,
                "swir2": 7,
            }

            band_count = metadata.get("band_count")

            for name, index in conventions.items():
                if (
                    name not in result
                    and isinstance(band_count, int)
                    and band_count >= index
                ):
                    result[name] = [index]

        # --------------------------------------------------------
        # Standard RGB / RGB-NIR fallback when no tags matched
        # --------------------------------------------------------

        elif not result:
            band_count = metadata.get("band_count")
            if isinstance(band_count, int):
                if band_count == 3:
                    result["red"] = [1]
                    result["green"] = [2]
                    result["blue"] = [3]
                elif band_count == 4:
                    result["red"] = [1]
                    result["green"] = [2]
                    result["blue"] = [3]
                    result["nir"] = [4]
                elif band_count == 6:
                    # Standard 6-band stacked product (B02, B03, B04, B08, B11, B12)
                    result["blue"] = [1]
                    result["green"] = [2]
                    result["red"] = [3]
                    result["nir"] = [4]
                    result["swir1"] = [5]
                    result["swir2"] = [6]

        # --------------------------------------------------------
        # Sentinel-1 fallback map.
        # --------------------------------------------------------

        if is_sentinel1:
            band_count = metadata.get("band_count")

            if isinstance(band_count, int) and band_count >= 1:
                if "vv" not in result:
                    result["vv"] = [1]

                if band_count >= 2 and "vh" not in result:
                    result["vh"] = [2]

        return result

    # ============================================================
    # SEMANTIC BAND NAMES
    # ============================================================

    @staticmethod
    def _semantic_band_names(
        text: str,
    ) -> List[str]:

        text = str(text or "").lower()

        names: List[str] = []

        # ISRO LISS / AWiFS / Cartosat explicit band naming
        if re.search(r"\b(l[34]|aw|liss[34]|awifs)[-_ ]?band[-_ ]?2\b", text):
            names.append("green")
        elif re.search(r"\b(l[34]|aw|liss[34]|awifs)[-_ ]?band[-_ ]?3\b", text):
            names.append("red")
        elif re.search(r"\b(l[34]|aw|liss[34]|awifs)[-_ ]?band[-_ ]?4\b", text):
            names.append("nir")
        elif re.search(r"\b(l3|aw|liss3|awifs)[-_ ]?band[-_ ]?5\b", text):
            names.append("swir1")
        elif re.search(r"\bmx[-_ ]?band[-_ ]?1\b", text):
            names.append("blue")
        elif re.search(r"\bmx[-_ ]?band[-_ ]?2\b", text):
            names.append("green")
        elif re.search(r"\bmx[-_ ]?band[-_ ]?3\b", text):
            names.append("red")
        elif re.search(r"\bmx[-_ ]?band[-_ ]?4\b", text):
            names.append("nir")
        elif re.search(r"\bpan[-_ ]?band\b", text) or "panchromatic" in text:
            names.extend(["pan", "gray", "red", "green", "blue"])

        # Blue (Sentinel-2 B02/B2, Landsat B02/B2, or 'blue')
        if (
            re.search(r"\bblue\b", text)
            or re.search(r"\bb0?2\b", text)
        ):
            if "blue" not in names:
                names.append("blue")

        # Green (Sentinel-2 B03/B3, Landsat B03/B3, or 'green')
        if (
            re.search(r"\bgreen\b", text)
            or re.search(r"\bb0?3\b", text)
        ):
            if "green" not in names:
                names.append("green")

        # Red (Sentinel-2 B04/B4, Landsat B04/B4, or 'red')
        if (
            re.search(r"\bred\b", text)
            or re.search(r"\bb0?4\b", text)
        ):
            if "red" not in names:
                names.append("red")

        # NIR (Sentinel-2 B08/B8/B8A, Landsat B05/B5, or 'nir')
        if (
            "nir" in text
            or "near infrared" in text
            or "near-infrared" in text
            or re.search(r"\bb0?8\b", text)
            or "b8a" in text
            or re.search(r"\bb0?5\b", text)
        ):
            if "nir" not in names:
                names.append("nir")

        # Red edge (Sentinel-2 B05, B06, B07)
        if (
            "red edge" in text
            or "red-edge" in text
            or re.search(r"\bb0?6\b", text)
            or re.search(r"\bb0?7\b", text)
        ):
            if "red_edge" not in names:
                names.append("red_edge")

        # SWIR1 (Sentinel-2 B11, Landsat B06/B6)
        if (
            "swir1" in text
            or "swir 1" in text
            or "swir_1" in text
            or re.search(r"\bb11\b", text)
        ):
            if "swir1" not in names:
                names.append("swir1")

        # SWIR2 (Sentinel-2 B12, Landsat B07/B7)
        if (
            "swir2" in text
            or "swir 2" in text
            or "swir_2" in text
            or re.search(r"\bb12\b", text)
        ):
            if "swir2" not in names:
                names.append("swir2")

        # SAR Polarizations
        if (
            re.search(r"\bvv\b", text)
            or "sigma0 vv" in text
            or "sigma0_vv" in text
        ):
            if "vv" not in names:
                names.append("vv")

        if (
            re.search(r"\bvh\b", text)
            or "sigma0 vh" in text
            or "sigma0_vh" in text
        ):
            if "vh" not in names:
                names.append("vh")

        if (
            re.search(r"\bhh\b", text)
            or "sigma0 hh" in text
            or "sigma0_hh" in text
        ):
            if "hh" not in names:
                names.append("hh")

        if (
            re.search(r"\bhv\b", text)
            or "sigma0 hv" in text
            or "sigma0_hv" in text
        ):
            if "hv" not in names:
                names.append("hv")

        return names

    # ============================================================
    # ACQUISITION DATE
    # ============================================================

    @staticmethod
    def _extract_acquisition_date(
        filename: str,
        metadata: Dict[str, Any],
    ) -> Optional[str]:
        """
        Extract only dates supported by actual metadata/filename.

        No year-only fallback is created.
        """
        # --------------------------------------------------------
        # ISRO XML / detected date
        # --------------------------------------------------------
        if metadata.get("isro_acquisition_date"):
            return metadata["isro_acquisition_date"]

        # --------------------------------------------------------
        # Raster metadata
        # --------------------------------------------------------

        raster_date = (
            metadata.get(
                "raster_acquisition_date"
            )
        )

        normalized = (
            MetadataExtractor
            ._normalize_date_value(
                raster_date
            )
        )

        if normalized:
            return normalized

        # --------------------------------------------------------
        # EXIF
        # --------------------------------------------------------

        exif_date = (
            metadata.get(
                "exif_acquisition_date"
            )
        )

        normalized = (
            MetadataExtractor
            ._normalize_date_value(
                exif_date
            )
        )

        if normalized:
            return normalized

        # --------------------------------------------------------
        # Filename
        # --------------------------------------------------------

        date_from_filename = (
            MetadataExtractor
            ._extract_date_from_filename(
                filename
            )
        )

        if date_from_filename:
            return date_from_filename

        return None

    @staticmethod
    def _normalize_date_value(
        value: Any,
    ) -> Optional[str]:
        """
        Normalize a genuine metadata date where possible.

        Returns ISO-like text when safely parseable.
        """

        if value is None:
            return None

        if isinstance(
            value,
            datetime,
        ):
            return value.isoformat()

        text = str(
            value
        ).strip()

        if not text:
            return None

        # Preserve standard ISO timestamps directly.
        if (
            re.match(
                r"^\d{4}-\d{2}-\d{2}",
                text,
            )
        ):
            return text

        # EXIF style:
        # YYYY:MM:DD HH:MM:SS
        match = re.match(
            r"^(\d{4}):(\d{2}):(\d{2})"
            r"(?:[ T](.*))?$",
            text,
        )

        if match:

            date_part = (
                f"{match.group(1)}-"
                f"{match.group(2)}-"
                f"{match.group(3)}"
            )

            if match.group(4):
                return (
                    f"{date_part} "
                    f"{match.group(4)}"
                )

            return date_part

        return text

    @staticmethod
    def _extract_exif_date(
        exif: Any,
    ) -> Optional[str]:

        if not exif:
            return None

        # EXIF DateTime
        value = exif.get(
            306
        )

        if value:
            return str(
                value
            )

        # DateTimeOriginal
        value = exif.get(
            36867
        )

        if value:
            return str(
                value
            )

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
            "sensing_datetime",
            "datetimeoriginal",
            "date",
            "timestamp",
            "start_datetime",
            "start_date",
        ]

        lowered = {
            str(
                key
            ).lower():
                value

            for (
                key,
                value
            )
            in tags.items()
        }

        for key in possible_keys:

            value = (
                lowered.get(
                    key
                )
            )

            if value:

                normalized = (
                    MetadataExtractor
                    ._normalize_date_value(
                        value
                    )
                )

                if normalized:
                    return normalized

        # Conservative fallback.
        for (
            key,
            value
        ) in lowered.items():

            if (
                (
                    "acquisition"
                    in key
                )
                or (
                    "sensing"
                    in key
                )
            ) and value:

                normalized = (
                    MetadataExtractor
                    ._normalize_date_value(
                        value
                    )
                )

                if normalized:
                    return normalized

        return None

    # ============================================================
    # FILENAME DATE
    # ============================================================

    @staticmethod
    def _extract_date_from_filename(
        filename: str,
    ) -> Optional[str]:

        # --------------------------------------------------------
        # YYYY-MM-DD / YYYY_MM_DD
        # --------------------------------------------------------

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

        # --------------------------------------------------------
        # YYYYMMDD
        # --------------------------------------------------------

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

    # ============================================================
    # FORMAT
    # ============================================================

    @staticmethod
    def _get_format(
        extension: str,
    ) -> str:

        formats = {
            ".tif":
                "GeoTIFF",

            ".tiff":
                "GeoTIFF",

            ".jp2":
                "JPEG2000",

            ".png":
                "PNG",

            ".jpg":
                "JPEG",

            ".jpeg":
                "JPEG",
        }

        return formats.get(
            extension,
            extension
            .replace(
                ".",
                "",
            )
            .upper(),
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _build_validation_summary(
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:

        warnings: List[
            str
        ] = []

        errors: List[
            str
        ] = []

        # --------------------------------------------------------
        # File
        # --------------------------------------------------------

        if not metadata.get(
            "file_path"
        ):
            errors.append(
                "No file path is available."
            )

        # --------------------------------------------------------
        # Raster dimensions
        # --------------------------------------------------------

        width = metadata.get(
            "width"
        )

        height = metadata.get(
            "height"
        )

        if (
            not isinstance(
                width,
                int,
            )
            or width <= 0
        ):
            warnings.append(
                "Image width unavailable or invalid."
            )

        if (
            not isinstance(
                height,
                int,
            )
            or height <= 0
        ):
            warnings.append(
                "Image height unavailable or invalid."
            )

        # --------------------------------------------------------
        # Geospatial metadata
        # --------------------------------------------------------

        if (
            metadata.get(
                "format"
            )
            == "GeoTIFF"
            and
            not metadata.get(
                "crs"
            )
        ):

            warnings.append(
                "GeoTIFF has no CRS information."
            )

        if (
            metadata.get(
                "format"
            )
            == "GeoTIFF"
            and
            not metadata.get(
                "bounds"
            )
        ):

            warnings.append(
                "GeoTIFF has no spatial bounds."
            )

        # --------------------------------------------------------
        # Acquisition date
        # --------------------------------------------------------

        if (
            metadata.get(
                "acquisition_date"
            )
            is None
        ):

            warnings.append(
                "Acquisition date unavailable."
            )

        # --------------------------------------------------------
        # Bands
        # --------------------------------------------------------

        band_count = (
            metadata.get(
                "band_count",
                0,
            )
        )

        if (
            not isinstance(
                band_count,
                int,
            )
            or band_count <= 0
        ):

            warnings.append(
                "No image bands detected."
            )

        # --------------------------------------------------------
        # Band map
        # --------------------------------------------------------

        band_map = (
            metadata.get(
                "band_map"
            )
            or {}
        )

        if not band_map:
            warnings.append(
                "No semantic band mapping could be inferred."
            )

        # --------------------------------------------------------
        # Modality
        # --------------------------------------------------------

        modality = (
            metadata.get(
                "modality"
            )
        )

        if (
            not modality
            or modality == "Optical / Unknown"
        ):

            warnings.append(
                "Imaging modality is uncertain."
            )

        return {

            "is_geospatial":
                bool(
                    metadata.get(
                        "geospatial_metadata_available",
                        False,
                    )
                ),

            "has_crs":
                bool(
                    metadata.get(
                        "crs"
                    )
                ),

            "has_bounds":
                bool(
                    metadata.get(
                        "bounds"
                    )
                ),

            "has_acquisition_date":
                (
                    metadata.get(
                        "acquisition_date"
                    )
                    is not None
                ),

            "has_band_information":
                (
                    isinstance(
                        band_count,
                        int,
                    )
                    and
                    band_count > 0
                ),

            "has_semantic_band_map":
                bool(
                    band_map
                ),

            "modality":
                modality,

            "warnings":
                warnings,

            "errors":
                errors,

            "ready_for_analysis":
                len(
                    errors
                ) == 0
                and
                isinstance(
                    width,
                    int,
                )
                and
                isinstance(
                    height,
                    int,
                )
                and
                width > 0
                and
                height > 0,
        }

    # ============================================================
    # METADATA SEARCH HELPERS
    # ============================================================

    @staticmethod
    def _find_tag_value(
        tags: Dict[str, Any],
        keys: List[str],
    ) -> Optional[str]:

        if not isinstance(
            tags,
            dict,
        ):
            return None

        lowered = {
            str(
                key
            ).lower():
                value

            for (
                key,
                value
            )
            in tags.items()
        }

        for key in keys:

            value = (
                lowered.get(
                    key.lower()
                )
            )

            if (
                value is not None
                and
                str(value).strip()
            ):

                return str(
                    value
                )

        return None

    @staticmethod
    def _metadata_text(
        metadata: Dict[str, Any],
    ) -> str:

        chunks: List[
            str
        ] = []

        for key in (
            "dataset_tags",
            "sensor",
            "platform",
            "processing_level",
            "product_type",
        ):

            value = (
                metadata.get(
                    key
                )
            )

            if (
                isinstance(
                    value,
                    dict,
                )
            ):

                chunks.extend(
                    [
                        f"{k} {v}"
                        for (
                            k,
                            v
                        )
                        in value.items()
                    ]
                )

            elif value is not None:

                chunks.append(
                    str(
                        value
                    )
                )

        return " ".join(
            chunks
        ).lower()

    @staticmethod
    def _band_description_text(
        metadata: Dict[str, Any],
    ) -> str:

        bands = (
            metadata.get(
                "bands"
            )
            or []
        )

        chunks: List[
            str
        ] = []

        if not isinstance(
            bands,
            list,
        ):
            return ""

        for band in bands:

            if not isinstance(
                band,
                dict,
            ):
                continue

            chunks.append(
                str(
                    band.get(
                        "description",
                        "",
                    )
                )
            )

            tags = (
                band.get(
                    "tags"
                )
                or {}
            )

            if isinstance(
                tags,
                dict,
            ):

                chunks.extend(
                    [
                        str(
                            value
                        )
                        for value
                        in tags.values()
                    ]
                )

        return " ".join(
            chunks
        ).lower()

    @staticmethod
    def _contains_any(
        text: str,
        tokens: List[str],
    ) -> bool:

        normalized = str(
            text or ""
        ).lower()

        return any(
            token.lower()
            in normalized
            for token
            in tokens
        )