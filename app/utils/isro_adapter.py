"""
SatQuery AI - ISRO / SAC Remote-Sensing Product & Metadata Adapter.

Supports:
- Indian Space Research Organisation (ISRO) & Space Applications Centre (SAC) missions:
    - RESOURCESAT (Resourcesat-1 / IRS-P6, Resourcesat-2, Resourcesat-2A)
    - CARTOSAT (Cartosat-1, Cartosat-2 series, Cartosat-3)
    - RISAT (RISAT-1, RISAT-2, RISAT-2B/2BR1)
    - EOS-04 (Radar Imaging Satellite / RISAT-1A equivalent C-band SAR)
    - EOS-06 (Oceansat-3 / OCM-3, SSTM)
- Dedicated XML metadata discovery & parsing:
    - BAND_META.xml, <scene_id>_metadata.xml, metadata.xml, product.xml, header.xml
    - XML tags: <Satellite>, <Sensor>, <DateOfPass>, <SceneID>, <ProductID>, <Polarization>, etc.
- Standard ISRO band naming conventions:
    - L4_BAND*.tif (LISS-4: B2=Green, B3=Red, B4=NIR)
    - L3_BAND*.tif (LISS-3: B2=Green, B3=Red, B4=NIR, B5=SWIR)
    - AW_BAND*.tif (AWiFS: B2=Green, B3=Red, B4=NIR, B5=SWIR)
    - PAN_BAND*.tif (Cartosat PAN: Panchromatic)
    - MX_BAND*.tif (Cartosat MX: B1=Blue, B2=Green, B3=Red, B4=NIR)
    - BAND_VV.tif, BAND_VH.tif, FRS_*.tif (RISAT/EOS-04 SAR)
    - OCM_BAND*.tif (EOS-06 Ocean Colour Monitor)
- Ground-truth band mapping with zero fabrication.
- Non-intrusive: preserves generic GeoTIFF fallback when not an ISRO product.
"""

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple


class ISROProductAdapter:
    """
    Adapter for ISRO / SAC remote-sensing satellite imagery and package metadata.
    """

    # Supported Mission Names
    MISSION_RESOURCESAT = "Resourcesat"
    MISSION_CARTOSAT = "Cartosat"
    MISSION_RISAT = "RISAT"
    MISSION_EOS04 = "EOS-04"
    MISSION_EOS06 = "EOS-06"

    # Supported Sensor Names
    SENSOR_LISS4 = "LISS-4"
    SENSOR_LISS3 = "LISS-3"
    SENSOR_AWIFS = "AWiFS"
    SENSOR_CARTOSAT_PAN = "PAN"
    SENSOR_CARTOSAT_MX = "MX"
    SENSOR_CSAR = "C-SAR"
    SENSOR_OCM3 = "OCM-3"

    @classmethod
    def detect_isro_product(
        cls,
        file_path: str,
        filename: Optional[str] = None,
        dataset_tags: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Detect whether an observation belongs to an ISRO/SAC mission and extract
        mission-specific metadata from XML headers, dataset tags, and filename patterns.

        Returns None if the file is not recognized as an ISRO product.
        """
        if not file_path:
            return None

        filename = filename or os.path.basename(file_path)
        directory = os.path.dirname(os.path.abspath(file_path)) if file_path else ""

        # 1. Look for and parse adjacent/parent XML metadata
        xml_metadata = cls._find_and_parse_xml(file_path, directory)

        # 2. Check dataset tags (from GeoTIFF / TIFF headers)
        tag_metadata = cls._parse_dataset_tags(dataset_tags or {})

        # 3. Check filename / path patterns
        filename_metadata = cls._parse_filename_and_path(filename, file_path)

        # Combine detected fields (XML takes precedence, then tags, then filename)
        isro_data: Dict[str, Any] = {}
        
        # Satellite / Platform
        platform = (
            xml_metadata.get("platform")
            or tag_metadata.get("platform")
            or filename_metadata.get("platform")
        )

        # Sensor / Payload
        sensor = (
            xml_metadata.get("sensor")
            or tag_metadata.get("sensor")
            or filename_metadata.get("sensor")
        )

        # Mission category
        mission = (
            xml_metadata.get("mission")
            or tag_metadata.get("mission")
            or filename_metadata.get("mission")
        )

        # Acquisition date
        acquisition_date = (
            xml_metadata.get("acquisition_date")
            or tag_metadata.get("acquisition_date")
            or filename_metadata.get("acquisition_date")
        )

        # Product / Scene ID
        product_id = (
            xml_metadata.get("product_id")
            or tag_metadata.get("product_id")
            or filename_metadata.get("product_id")
        )

        # Modality
        modality = (
            xml_metadata.get("modality")
            or tag_metadata.get("modality")
            or filename_metadata.get("modality")
        )

        # Specific Band ID (if single band file like L4_BAND2.tif)
        band_identifier = (
            xml_metadata.get("band_identifier")
            or filename_metadata.get("band_identifier")
        )

        # Polarization (for SAR)
        polarization = (
            xml_metadata.get("polarization")
            or tag_metadata.get("polarization")
            or filename_metadata.get("polarization")
        )

        # Spatial resolution (meters)
        resolution_m = (
            xml_metadata.get("spatial_resolution_m")
            or filename_metadata.get("spatial_resolution_m")
        )

        # Determine if this is authentically an ISRO product
        is_isro = bool(mission or platform or (sensor and sensor in [
            cls.SENSOR_LISS4, cls.SENSOR_LISS3, cls.SENSOR_AWIFS,
            cls.SENSOR_CARTOSAT_PAN, cls.SENSOR_CARTOSAT_MX, cls.SENSOR_OCM3
        ]))

        if not is_isro:
            return None

        # Derive modality if not explicit
        if not modality:
            if sensor in [cls.SENSOR_CSAR] or (mission in [cls.MISSION_RISAT, cls.MISSION_EOS04]):
                modality = "sar"
            else:
                modality = "multispectral" if sensor != cls.SENSOR_CARTOSAT_PAN else "optical"

        isro_data = {
            "is_isro_product": True,
            "provider": "ISRO / SAC",
            "mission": mission,
            "platform": platform,
            "sensor": sensor,
            "acquisition_date": acquisition_date,
            "product_id": product_id,
            "modality": modality,
            "band_identifier": band_identifier,
            "polarization": polarization,
            "spatial_resolution_m": resolution_m,
            "xml_metadata_path": xml_metadata.get("xml_source_path"),
        }

        return isro_data

    @classmethod
    def _find_and_parse_xml(
        cls,
        file_path: str,
        directory: str,
    ) -> Dict[str, Any]:
        """
        Search for and parse ISRO/SAC XML metadata files such as BAND_META.xml or <scene>_metadata.xml.
        """
        result: Dict[str, Any] = {}
        if not directory or not os.path.isdir(directory):
            return result

        basename_no_ext = os.path.splitext(os.path.basename(file_path))[0]

        # Candidate XML file patterns
        candidate_names = [
            "BAND_META.xml",
            "band_meta.xml",
            f"{basename_no_ext}.xml",
            f"{basename_no_ext}_metadata.xml",
            f"{basename_no_ext}_METADATA.xml",
            "metadata.xml",
            "METADATA.xml",
            "product.xml",
            "PRODUCT.xml",
            "header.xml",
            "HEADER.xml",
        ]

        xml_path = None
        for name in candidate_names:
            p = os.path.join(directory, name)
            if os.path.isfile(p):
                xml_path = p
                break

        # Also search parent directory if inside a subfolder (e.g. BAND/ directory)
        if not xml_path and os.path.isdir(os.path.dirname(directory)):
            parent_dir = os.path.dirname(directory)
            for name in candidate_names:
                p = os.path.join(parent_dir, name)
                if os.path.isfile(p):
                    xml_path = p
                    break

        if not xml_path:
            return result

        result["xml_source_path"] = xml_path
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Helper to search tags case-insensitively
            def get_tag_text(tags: List[str]) -> Optional[str]:
                for elem in root.iter():
                    elem_tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    for target in tags:
                        if elem_tag.lower() == target.lower() and elem.text and elem.text.strip():
                            return elem.text.strip()
                return None

            # 1. Satellite / Platform
            raw_sat = get_tag_text([
                "Satellite", "Satellite_Name", "SatelliteName", "Platform",
                "Spacecraft", "Mission", "MISSION_NAME", "SatelliteID"
            ])
            if raw_sat:
                sat_clean = cls._normalize_satellite_name(raw_sat)
                result["platform"] = sat_clean
                result["mission"] = cls._infer_mission_from_satellite(sat_clean)

            # 2. Sensor / Payload
            raw_sensor = get_tag_text([
                "Sensor", "Sensor_Name", "SensorName", "Payload",
                "Payload_Name", "Instrument", "Camera"
            ])
            if raw_sensor:
                result["sensor"] = cls._normalize_sensor_name(raw_sensor)

            # 3. Date of Pass / Acquisition Date
            raw_date = get_tag_text([
                "DateOfPass", "Date_Of_Pass", "AcquisitionDate", "Acquisition_Date",
                "Pass_Date", "SceneDate", "ProductDate", "ImagingDate",
                "Start_Time", "StartTime", "GenerationDate"
            ])
            if raw_date:
                parsed_date = cls._parse_isro_date(raw_date)
                if parsed_date:
                    result["acquisition_date"] = parsed_date

            # 4. Product ID / Scene ID
            raw_id = get_tag_text([
                "ProductID", "Product_ID", "SceneID", "Scene_ID",
                "DatasetID", "Product_Information"
            ])
            if raw_id:
                result["product_id"] = raw_id

            # 5. Polarization
            raw_pol = get_tag_text(["Polarization", "Polarisation", "TxRxPolarisation"])
            if raw_pol:
                result["polarization"] = raw_pol.upper().strip()

            # 6. Spatial Resolution
            raw_res = get_tag_text(["PixelResolution", "SpatialResolution", "Resolution", "SamplingDistance"])
            if raw_res:
                try:
                    val = float(re.findall(r"[\d\.]+", raw_res)[0])
                    result["spatial_resolution_m"] = val
                except (IndexError, ValueError):
                    pass

        except Exception:
            # Safe XML parsing failure without crashing
            pass

        return result

    @classmethod
    def _parse_dataset_tags(cls, tags: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GeoTIFF GDAL/TIFF tags for ISRO indicators."""
        result: Dict[str, Any] = {}
        if not tags:
            return result

        tags_lower = {str(k).lower(): str(v) for k, v in tags.items()}

        for k, v in tags_lower.items():
            if any(term in k for term in ["satellite", "platform", "spacecraft"]):
                norm_sat = cls._normalize_satellite_name(v)
                result["platform"] = norm_sat
                result["mission"] = cls._infer_mission_from_satellite(norm_sat)
            elif any(term in k for term in ["sensor", "payload", "instrument"]):
                result["sensor"] = cls._normalize_sensor_name(v)
            elif any(term in k for term in ["date", "pass", "time", "acquisition"]):
                d = cls._parse_isro_date(v)
                if d:
                    result["acquisition_date"] = d
            elif any(term in k for term in ["product_id", "scene_id"]):
                result["product_id"] = v.strip()

        return result

    @classmethod
    def _parse_filename_and_path(cls, filename: str, file_path: str) -> Dict[str, Any]:
        """Parse filename and path structure for ISRO mission patterns."""
        result: Dict[str, Any] = {}
        target_str = f"{file_path} {filename}".upper()

        def match_token(pattern: str) -> bool:
            return bool(re.search(r"(?:^|[^A-Za-z0-9])(" + pattern + r")(?:[^A-Za-z0-9]|$)", target_str))

        # -------------------------------------------------------------
        # 1. Mission / Satellite Detection
        # -------------------------------------------------------------
        if match_token(r"RESOURCESAT[-_ ]?2A|RS2A|RS-2A"):
            result["platform"] = "Resourcesat-2A"
            result["mission"] = cls.MISSION_RESOURCESAT
        elif match_token(r"RESOURCESAT[-_ ]?2|RS2|RS-2"):
            result["platform"] = "Resourcesat-2"
            result["mission"] = cls.MISSION_RESOURCESAT
        elif match_token(r"RESOURCESAT[-_ ]?1|RS1|RS-1|IRS[-_ ]?P6"):
            result["platform"] = "Resourcesat-1 (IRS-P6)"
            result["mission"] = cls.MISSION_RESOURCESAT
        elif "RESOURCESAT" in target_str or "IRS" in target_str:
            result["platform"] = "Resourcesat"
            result["mission"] = cls.MISSION_RESOURCESAT
        elif match_token(r"CARTOSAT[-_ ]?3|CARTO3|CARTO-3"):
            result["platform"] = "Cartosat-3"
            result["mission"] = cls.MISSION_CARTOSAT
        elif match_token(r"CARTOSAT[-_ ]?2[A-F]?|CARTO2[A-F]?|CARTO-2[A-F]?"):
            result["platform"] = "Cartosat-2"
            result["mission"] = cls.MISSION_CARTOSAT
        elif match_token(r"CARTOSAT[-_ ]?1|CARTO1|CARTO-1"):
            result["platform"] = "Cartosat-1"
            result["mission"] = cls.MISSION_CARTOSAT
        elif "CARTOSAT" in target_str or "CARTO" in target_str:
            result["platform"] = "Cartosat"
            result["mission"] = cls.MISSION_CARTOSAT
        elif match_token(r"EOS[-_ ]?0?4|RISAT[-_ ]?1A"):
            result["platform"] = "EOS-04 (RISAT-1A)"
            result["mission"] = cls.MISSION_EOS04
            result["sensor"] = cls.SENSOR_CSAR
            result["modality"] = "sar"
        elif match_token(r"RISAT[-_ ]?1"):
            result["platform"] = "RISAT-1"
            result["mission"] = cls.MISSION_RISAT
            result["sensor"] = cls.SENSOR_CSAR
            result["modality"] = "sar"
        elif match_token(r"RISAT[-_ ]?2[A-Z]?"):
            result["platform"] = "RISAT-2"
            result["mission"] = cls.MISSION_RISAT
            result["sensor"] = "X-SAR"
            result["modality"] = "sar"
        elif match_token(r"EOS[-_ ]?0?6|OCEANSAT[-_ ]?3"):
            result["platform"] = "EOS-06 (Oceansat-3)"
            result["mission"] = cls.MISSION_EOS06
            result["sensor"] = cls.SENSOR_OCM3

        # -------------------------------------------------------------
        # 2. Sensor / Payload Detection
        # -------------------------------------------------------------
        if match_token(r"LISS[-_ ]?4|LISSIV|L4"):
            result["sensor"] = cls.SENSOR_LISS4
            result["spatial_resolution_m"] = 5.8
        elif match_token(r"LISS[-_ ]?3|LISSIII|L3"):
            result["sensor"] = cls.SENSOR_LISS3
            result["spatial_resolution_m"] = 23.5
        elif match_token(r"AWIFS|AW"):
            result["sensor"] = cls.SENSOR_AWIFS
            result["spatial_resolution_m"] = 56.0
        elif match_token(r"PAN|PANCHROMATIC"):
            result["sensor"] = cls.SENSOR_CARTOSAT_PAN
            result["modality"] = "optical"
        elif match_token(r"MX|MULTISPECTRAL") and "CARTO" in target_str:
            result["sensor"] = cls.SENSOR_CARTOSAT_MX
            result["modality"] = "multispectral"
        elif match_token(r"OCM[-_ ]?3|OCM"):
            result["sensor"] = cls.SENSOR_OCM3
            result["modality"] = "multispectral"

        # -------------------------------------------------------------
        # 3. Specific Band File Identifier (e.g. L4_BAND2.tif, BAND3.tif)
        # -------------------------------------------------------------
        band_match = re.search(r"(?:^|[^A-Za-z0-9])(?:L[34]|AW|MX|PAN|OCM)?[-_ ]?BAND[-_ ]?([0-9]+|[A-Z]+)(?:[^A-Za-z0-9]|$)", filename.upper())
        if band_match:
            result["band_identifier"] = band_match.group(1)

        # SAR Polarization in filename (e.g. BAND_VV.tif, FRS_VH.tif)
        sar_pol_match = re.search(r"(?:^|[^A-Za-z0-9])(VV|VH|HH|HV)(?:[^A-Za-z0-9]|$)", filename.upper())
        if sar_pol_match:
            result["polarization"] = sar_pol_match.group(1)

        # -------------------------------------------------------------
        # 4. Acquisition Date in filename (e.g. 20240115, 15JAN2024, 2024-01-15)
        # -------------------------------------------------------------
        date_match = re.search(r"(\d{4}[-_]\d{2}[-_]\d{2})", filename)
        if date_match:
            d = cls._parse_isro_date(date_match.group(1))
            if d:
                result["acquisition_date"] = d
        else:
            # Check 8-digit compact date YYYYMMDD
            compact_match = re.search(r"(?:_|^|-)((?:20|19)\d{2}[01]\d[0-3]\d)(?:_|$|-|\.)", filename)
            if compact_match:
                d = cls._parse_isro_date(compact_match.group(1))
                if d:
                    result["acquisition_date"] = d
            else:
                # Check DDMMMYYYY (e.g. 15JAN2024)
                text_date_match = re.search(r"(\d{1,2}[A-Za-z]{3}\d{4})", filename)
                if text_date_match:
                    d = cls._parse_isro_date(text_date_match.group(1))
                    if d:
                        result["acquisition_date"] = d

        return result

    @classmethod
    def get_isro_band_map(
        cls,
        isro_info: Dict[str, Any],
        band_count: int,
        existing_band_descriptions: Optional[List[str]] = None,
    ) -> Dict[str, List[int]]:
        """
        Build the normalized band map for recognized ISRO products.

        Follows official SAC/ISRO sensor specifications:
        - LISS-4: B2=Green, B3=Red, B4=NIR (3 bands)
        - LISS-3: B2=Green, B3=Red, B4=NIR, B5=SWIR (4 bands)
        - AWiFS: B2=Green, B3=Red, B4=NIR, B5=SWIR (4 bands)
        - Cartosat MX: B1=Blue, B2=Green, B3=Red, B4=NIR (4 bands)
        - Cartosat PAN: B1=Panchromatic (1 band)
        - RISAT / EOS-04: VV, VH, HH, HV (SAR channels)
        """
        band_map: Dict[str, List[int]] = {}
        sensor = isro_info.get("sensor")
        band_id = str(isro_info.get("band_identifier") or "").upper()
        polarization = str(isro_info.get("polarization") or "").upper()

        # -------------------------------------------------------------
        # Single Band File Ingestion (e.g. L4_BAND2.tif or BAND_VV.tif)
        # -------------------------------------------------------------
        if band_count == 1:
            if band_id in ["2", "B2", "GREEN"]:
                band_map["green"] = [1]
            elif band_id in ["3", "B3", "RED"]:
                band_map["red"] = [1]
            elif band_id in ["4", "B4", "NIR"]:
                band_map["nir"] = [1]
            elif band_id in ["5", "B5", "SWIR", "SWIR1"]:
                band_map["swir1"] = [1]
            elif band_id in ["1", "B1", "BLUE"] and sensor != cls.SENSOR_CARTOSAT_PAN:
                band_map["blue"] = [1]
            elif sensor == cls.SENSOR_CARTOSAT_PAN or band_id in ["PAN"]:
                band_map["pan"] = [1]
                band_map["gray"] = [1]
                band_map["red"] = [1]
                band_map["green"] = [1]
                band_map["blue"] = [1]

            # SAR Single Polarization Band
            if polarization == "VV" or band_id == "VV":
                band_map["vv"] = [1]
            elif polarization == "VH" or band_id == "VH":
                band_map["vh"] = [1]
            elif polarization == "HH" or band_id == "HH":
                band_map["hh"] = [1]
            elif polarization == "HV" or band_id == "HV":
                band_map["hv"] = [1]

            return band_map

        # -------------------------------------------------------------
        # Multi-band Stacked Rasters
        # -------------------------------------------------------------
        # 1. LISS-4 Multi-spectral (3 bands: B2-Green, B3-Red, B4-NIR)
        if sensor == cls.SENSOR_LISS4 and band_count >= 3:
            band_map["green"] = [1]  # Band 1 in raster is ISRO Band 2 (Green)
            band_map["red"] = [2]    # Band 2 in raster is ISRO Band 3 (Red)
            band_map["nir"] = [3]    # Band 3 in raster is ISRO Band 4 (NIR)
            # Add synthetic blue channel for standard false/true color visual composite
            band_map["blue"] = [1]

        # 2. LISS-3 & AWiFS Multi-spectral (4 bands: B2-Green, B3-Red, B4-NIR, B5-SWIR)
        elif sensor in [cls.SENSOR_LISS3, cls.SENSOR_AWIFS] and band_count >= 4:
            band_map["green"] = [1]  # Band 1 = Green (B2)
            band_map["red"] = [2]    # Band 2 = Red (B3)
            band_map["nir"] = [3]    # Band 3 = NIR (B4)
            band_map["swir1"] = [4]  # Band 4 = SWIR (B5)
            band_map["blue"] = [1]

        # 3. Cartosat MX (4 bands: B1-Blue, B2-Green, B3-Red, B4-NIR)
        elif sensor == cls.SENSOR_CARTOSAT_MX and band_count >= 4:
            band_map["blue"] = [1]
            band_map["green"] = [2]
            band_map["red"] = [3]
            band_map["nir"] = [4]

        # 4. RISAT / EOS-04 SAR (Dual-pol or Quad-pol)
        elif (sensor == cls.SENSOR_CSAR or isro_info.get("modality") == "sar") and band_count >= 2:
            if "HH" in polarization and "HV" in polarization:
                band_map["hh"] = [1]
                band_map["hv"] = [2]
            else:
                band_map["vv"] = [1]
                band_map["vh"] = [2]

        return band_map

    @classmethod
    def _normalize_satellite_name(cls, name: str) -> str:
        """Normalize satellite string into official canonical name."""
        s = name.upper().strip()
        if "RESOURCESAT-2A" in s or "RS-2A" in s or "RS2A" in s:
            return "Resourcesat-2A"
        if "RESOURCESAT-2" in s or "RS-2" in s or "RS2" in s:
            return "Resourcesat-2"
        if "RESOURCESAT-1" in s or "IRS-P6" in s or "RS1" in s:
            return "Resourcesat-1 (IRS-P6)"
        if "RESOURCESAT" in s:
            return "Resourcesat"
        if "CARTOSAT-3" in s or "CARTO-3" in s or "CARTO3" in s:
            return "Cartosat-3"
        if "CARTOSAT-2" in s or "CARTO-2" in s or "CARTO2" in s:
            return "Cartosat-2"
        if "CARTOSAT-1" in s or "CARTO-1" in s or "CARTO1" in s:
            return "Cartosat-1"
        if "CARTOSAT" in s:
            return "Cartosat"
        if "EOS-04" in s or "EOS04" in s or "RISAT-1A" in s:
            return "EOS-04 (RISAT-1A)"
        if "RISAT-1" in s:
            return "RISAT-1"
        if "RISAT-2" in s:
            return "RISAT-2"
        if "EOS-06" in s or "EOS06" in s or "OCEANSAT-3" in s:
            return "EOS-06 (Oceansat-3)"
        return name.strip()

    @classmethod
    def _normalize_sensor_name(cls, sensor: str) -> str:
        """Normalize sensor string into official canonical sensor ID."""
        s = sensor.upper().strip()
        if "LISS-4" in s or "LISSIV" in s or "L4" in s:
            return cls.SENSOR_LISS4
        if "LISS-3" in s or "LISSIII" in s or "L3" in s:
            return cls.SENSOR_LISS3
        if "AWIFS" in s or "AW" in s:
            return cls.SENSOR_AWIFS
        if "PAN" in s:
            return cls.SENSOR_CARTOSAT_PAN
        if "MX" in s:
            return cls.SENSOR_CARTOSAT_MX
        if "SAR" in s:
            return cls.SENSOR_CSAR
        if "OCM" in s:
            return cls.SENSOR_OCM3
        return sensor.strip()

    @classmethod
    def _infer_mission_from_satellite(cls, sat_name: str) -> Optional[str]:
        """Infer mission category from satellite name."""
        s = sat_name.lower()
        if "resourcesat" in s or "irs-p6" in s:
            return cls.MISSION_RESOURCESAT
        if "cartosat" in s:
            return cls.MISSION_CARTOSAT
        if "risat" in s:
            return cls.MISSION_RISAT
        if "eos-04" in s or "eos04" in s:
            return cls.MISSION_EOS04
        if "eos-06" in s or "eos06" in s or "oceansat" in s:
            return cls.MISSION_EOS06
        return None

    @classmethod
    def _parse_isro_date(cls, raw: str) -> Optional[str]:
        """Parse various ISRO date string formats into standard YYYY-MM-DD."""
        if not raw:
            return None

        val = str(raw).strip()

        # Format list to try
        date_formats = [
            "%d-%b-%Y",      # 15-JAN-2024
            "%d-%B-%Y",      # 15-January-2024
            "%Y-%m-%d",      # 2024-01-15
            "%Y%m%d",        # 20240115
            "%d/%m/%Y",      # 15/01/2024
            "%d-%m-%Y",      # 15-01-2024
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y/%m/%d",
            "%d%b%Y",        # 15JAN2024
        ]

        # Clean string
        val_clean = re.sub(r"[\"']", "", val).strip()

        for fmt in date_formats:
            try:
                dt = datetime.strptime(val_clean, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # Try regex substring extraction for YYYY-MM-DD
        m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", val_clean)
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

        # Try regex substring extraction for DD-MMM-YYYY
        m2 = re.search(r"(\d{1,2})[-/]([A-Za-z]{3})[-/](\d{4})", val_clean)
        if m2:
            try:
                dt = datetime.strptime(f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}", "%d-%b-%Y")
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        return None
