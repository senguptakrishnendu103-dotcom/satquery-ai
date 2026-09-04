import React, { useState } from 'react';
import {
  X,
  Search,
  Calendar,
  MapPin,
  Cloud,
  Satellite,
  Plus,
  Check,
  Loader2,
  Globe,
  Download,
  AlertCircle,
} from 'lucide-react';

import { satQueryService } from '../../services/satQueryService';

import type {
  ModalityType,
  Observation,
} from '../../types/satquery';


// ============================================================
// PROPS
// ============================================================

interface SatelliteSearchModalProps {
  isOpen: boolean;

  onClose: () => void;

  /**
   * Existing upload callback.
   *
   * Kept for compatibility with the existing workspace.
   */
  onAddObservation?: (
    file: File,
    modality: ModalityType
  ) => void;

  /**
   * Existing product callback.
   *
   * This now receives the normalized/ingested observation.
   */
  onAddProductAsObservation?: (
    product: any
  ) => void;
}


// ============================================================
// LOCATION PRESETS
// ============================================================

interface LocationPreset {
  name: string;

  region: string;

  bbox: [
    number,
    number,
    number,
    number
  ];
}


const LOCATION_PRESETS: LocationPreset[] = [
  {
    name:
      'Kolkata Metropolitan Area',

    region:
      'India',

    bbox: [
      88.2,
      22.4,
      88.5,
      22.7,
    ],
  },

  {
    name:
      'Suez Canal & Gulf of Suez',

    region:
      'Egypt',

    bbox: [
      32.3,
      29.8,
      32.6,
      30.1,
    ],
  },

  {
    name:
      'Amazon River Basin',

    region:
      'Brazil',

    bbox: [
      -60.2,
      -3.2,
      -59.8,
      -2.8,
    ],
  },

  {
    name:
      'Dubai & Palm Jumeirah',

    region:
      'UAE',

    bbox: [
      55.1,
      24.9,
      55.4,
      25.2,
    ],
  },
];


// ============================================================
// COLLECTION DEFINITIONS
// ============================================================

interface CollectionOption {
  value: string;

  label: string;

  modality: ModalityType;

  supportsCloudFilter: boolean;
}


const COLLECTIONS: CollectionOption[] = [
  {
    value:
      'sentinel-2-l2a',

    label:
      'Sentinel-2 (Optical Multispectral · L2A)',

    modality:
      'MULTISPECTRAL',

    supportsCloudFilter:
      true,
  },

  {
    value:
      'sentinel-2-l1c',

    label:
      'Sentinel-2 (Optical Multispectral · L1C)',

    modality:
      'MULTISPECTRAL',

    supportsCloudFilter:
      true,
  },

  {
    value:
      'sentinel-1-grd',

    label:
      'Sentinel-1 (SAR Radar · GRD)',

    modality:
      'SAR',

    supportsCloudFilter:
      false,
  },
];


// ============================================================
// PRODUCT TYPE
// ============================================================

interface SatelliteProduct {
  product_id: string;

  provider?: string;

  collection?: string;

  platform?: string;

  instrument?: string;

  acquisition_datetime?: string | null;

  cloud_cover?: number | null;

  resolution?: number | null;

  modality?: string;

  thumbnail_url?: string | null;

  product_url?: string | null;

  download_url?: string | null;

  bbox?: number[];

  geo_footprint?: unknown;

  available_bands?: string[];

  metadata?: Record<
    string,
    unknown
  >;

  assets?: Record<
    string,
    unknown
  >;

  processing_level?: string | null;
}


// ============================================================
// HELPERS
// ============================================================

function formatProductDate(
  value?: string | null
): string {
  if (!value) {
    return 'Date unavailable';
  }

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return value;
  }

  return date.toLocaleDateString(
    'en-GB',
    {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }
  );
}


function getCollectionModality(
  collection: string
): ModalityType {
  const option =
    COLLECTIONS.find(
      (item) =>
        item.value === collection
    );

  return (
    option?.modality ||
    'OPTICAL'
  );
}


function isProductMatchingCollection(
  product: SatelliteProduct,
  collection: string
): boolean {
  const normalizedCollection =
    collection
      .toLowerCase()
      .replace(
        /_/g,
        '-'
      );

  const productCollection =
    String(
      product.collection || ''
    )
      .toLowerCase()
      .replace(
        /_/g,
        '-'
      );

  const productName =
    String(
      product.metadata?.name ||
      ''
    ).toUpperCase();

  const productType =
    String(
      product.metadata?.product_type ||
      ''
    ).toUpperCase();

  // ----------------------------------------------------------
  // Sentinel-2 L2A
  // ----------------------------------------------------------

  if (
    normalizedCollection ===
    'sentinel-2-l2a'
  ) {
    return (
      productCollection ===
      'sentinel-2-l2a' ||
      (
        (
          productCollection ===
          'sentinel-2'
        ) &&
        (
          productType ===
          'S2MSI2A' ||
          productName.includes(
            'MSIL2A'
          )
        )
      )
    );
  }

  // ----------------------------------------------------------
  // Sentinel-2 L1C
  // ----------------------------------------------------------

  if (
    normalizedCollection ===
    'sentinel-2-l1c'
  ) {
    return (
      productCollection ===
      'sentinel-2-l1c' ||
      (
        (
          productCollection ===
          'sentinel-2'
        ) &&
        (
          productType ===
          'S2MSI1C' ||
          productName.includes(
            'MSIL1C'
          )
        )
      )
    );
  }

  // ----------------------------------------------------------
  // Sentinel-1 GRD
  // ----------------------------------------------------------

  if (
    normalizedCollection ===
    'sentinel-1-grd'
  ) {
    return (
      productCollection ===
      'sentinel-1-grd' ||
      (
        (
          productCollection ===
          'sentinel-1'
        ) &&
        (
          productType ===
          'GRD' ||
          productName.includes(
            'GRD'
          )
        )
      )
    );
  }

  return false;
}


function normalizeReturnedProducts(
  products: any[],
  collection: string
): SatelliteProduct[] {

  if (
    !Array.isArray(
      products
    )
  ) {
    return [];
  }

  return products
    .filter(
      (product) =>
        isProductMatchingCollection(
          product,
          collection
        )
    )
    .map(
      (product) => {

        const productId =
          String(
            product.product_id ||
            product.id ||
            ''
          );

        const quicklookUrl =
          product.thumbnail_url ||
          product.quicklook_url ||
          (
            productId
              ? satQueryService
                .getCopernicusQuicklookUrl(
                  productId
                )
              : ''
          );

        return {
          ...product,

          product_id:
            productId,

          thumbnail_url:
            quicklookUrl,

          quicklook_url:
            quicklookUrl,

          modality:
            product.modality ||
            (
              getCollectionModality(
                collection
              ) === 'SAR'
                ? 'sar'
                : 'optical'
            ),
        };
      }
    );
}


function productToObservationPreview(
  product: SatelliteProduct,
  collection: string
): Observation {

  const modality =
    getCollectionModality(
      collection
    );

  const date =
    product.acquisition_datetime
      ? formatProductDate(
        product.acquisition_datetime
      )
      : 'DATE NOT AVAILABLE';

  const productName =
    String(
      product.metadata?.name ||
      product.product_id ||
      'Copernicus observation'
    );

  return {
    id:
      `cdse-${product.product_id}`,

    name:
      productName,

    filename:
      productName,

    modality,

    date,

    dimensions:
      'Satellite product',

    status:
      'INGESTING',

    metadata: {
      sensor:
        product.instrument ||
        product.platform ||
        'Copernicus',

      lat:
        calculateCenter(
          product.bbox
        )?.lat,

      lon:
        calculateCenter(
          product.bbox
        )?.lon,

      cloudCover:
        product.cloud_cover !== null &&
          product.cloud_cover !== undefined
          ? `${Number(
            product.cloud_cover
          ).toFixed(1)}%`
          : 'Not available',

      bands:
        Array.isArray(
          product.available_bands
        ) &&
          product.available_bands.length
          ? `${product.available_bands.length} Channels (${product.available_bands.join(', ')})`
          : 'Band information unavailable',

      fileSize:
        'Pending download',

      groundSamplingDistance:
        product.resolution !== null &&
          product.resolution !== undefined
          ? `${product.resolution}m/px`
          : 'Not available',

      acquisitionTime:
        product.acquisition_datetime
          ? formatAcquisitionTime(
            product.acquisition_datetime
          )
          : 'Not available',

      provider:
        product.provider ||
        'copernicus',

      productId:
        product.product_id,

      product_id:
        product.product_id,

      collection:
        collection,

      processingLevel:
        product.processing_level,

      crs:
        'EPSG:4326',

      sourceType:
        'copernicus',

      source_type:
        'copernicus',

      ingestionStatus:
        'pending',

      ingestion_status:
        'pending',
    },

    imageUrl:
      product.thumbnail_url ||
      '',

    thumbnailUrl:
      product.thumbnail_url ||
      '',

    isDemo:
      false,

    ...((
      {
        provider:
          product.provider ||
          'copernicus',

        productId:
          product.product_id,

        product_id:
          product.product_id,

        sourceType:
          'copernicus',

        source_type:
          'copernicus',

        ingestionStatus:
          'pending',

        ingestion_status:
          'pending',

        acquisitionDate:
          product.acquisition_datetime ||
          null,

        acquisition_date:
          product.acquisition_datetime ||
          null,
      } as any
    )),
  } as Observation;
}


function calculateCenter(
  bbox?: number[]
): {
  lat: number;
  lon: number;
} | undefined {

  if (
    !Array.isArray(
      bbox
    ) ||
    bbox.length < 4
  ) {
    return undefined;
  }

  const minLon =
    Number(bbox[0]);

  const minLat =
    Number(bbox[1]);

  const maxLon =
    Number(bbox[2]);

  const maxLat =
    Number(bbox[3]);

  if (
    !Number.isFinite(
      minLon
    ) ||
    !Number.isFinite(
      minLat
    ) ||
    !Number.isFinite(
      maxLon
    ) ||
    !Number.isFinite(
      maxLat
    )
  ) {
    return undefined;
  }

  return {
    lon:
      (minLon + maxLon) /
      2,

    lat:
      (minLat + maxLat) /
      2,
  };
}


function formatAcquisitionTime(
  value: string
): string {

  const date =
    new Date(value);

  if (
    Number.isNaN(
      date.getTime()
    )
  ) {
    return 'Not available';
  }

  return (
    `${date.toISOString().substring(11, 19)} UTC`
  );
}


// ============================================================
// COMPONENT
// ============================================================

export const SatelliteSearchModal:
  React.FC<
    SatelliteSearchModalProps
  > = ({
    isOpen,
    onClose,
    onAddProductAsObservation,
  }) => {

    // --------------------------------------------------------
    // STATE
    // --------------------------------------------------------

    const [
      selectedPreset,
      setSelectedPreset,
    ] = useState<LocationPreset>(
      LOCATION_PRESETS[0]
    );

    const [
      collection,
      setCollection,
    ] = useState<string>(
      'sentinel-2-l2a'
    );

    const [
      startDate,
      setStartDate,
    ] = useState<string>(
      '2024-01-01'
    );

    const [
      endDate,
      setEndDate,
    ] = useState<string>(
      '2024-12-31'
    );

    const [
      maxCloud,
      setMaxCloud,
    ] = useState<number>(
      20
    );

    const [
      isSearching,
      setIsSearching,
    ] = useState<boolean>(
      false
    );

    const [
      isIngestingId,
      setIsIngestingId,
    ] = useState<string | null>(
      null
    );

    const [
      results,
      setResults,
    ] = useState<
      SatelliteProduct[]
    >([]);

    const [
      addedIds,
      setAddedIds,
    ] = useState<string[]>(
      []
    );

    const [
      errorMsg,
      setErrorMsg,
    ] = useState<string | null>(
      null
    );

    const [
      hasSearched,
      setHasSearched,
    ] = useState<boolean>(
      false
    );

    // --------------------------------------------------------
    // CLOSE GUARD
    // --------------------------------------------------------

    if (!isOpen) {
      return null;
    }

    // --------------------------------------------------------
    // COLLECTION INFO
    // --------------------------------------------------------

    const selectedCollection =
      COLLECTIONS.find(
        (item) =>
          item.value === collection
      );

    const supportsCloudFilter =
      selectedCollection
        ?.supportsCloudFilter ??
      false;

    // --------------------------------------------------------
    // COLLECTION CHANGE
    // --------------------------------------------------------

    const handleCollectionChange = (
      value: string
    ) => {

      setCollection(
        value
      );

      setResults(
        []
      );

      setErrorMsg(
        null
      );

      setHasSearched(
        false
      );
    };

    // --------------------------------------------------------
    // SEARCH
    // --------------------------------------------------------

    const handleSearch =
      async () => {

        setIsSearching(
          true
        );

        setErrorMsg(
          null
        );

        setResults(
          []
        );

        setHasSearched(
          true
        );

        try {

          const response =
            await satQueryService
              .searchSatelliteCatalogue({
                bbox:
                  selectedPreset.bbox,

                start_date:
                  startDate,

                end_date:
                  endDate,

                collection:
                  collection,

                max_cloud_cover:
                  supportsCloudFilter
                    ? maxCloud
                    : undefined,

                limit:
                  10,
              });

          const rawProducts =
            response?.products ||
            [];

          const filteredProducts =
            normalizeReturnedProducts(
              rawProducts,
              collection
            );

          setResults(
            filteredProducts
          );

          if (
            rawProducts.length > 0 &&
            filteredProducts.length === 0
          ) {
            setErrorMsg(
              'The catalogue returned products, but none matched the selected collection. No unrelated scenes were shown.'
            );
          } else if (
            filteredProducts.length === 0
          ) {
            setErrorMsg(
              'No matching satellite scenes were found for this region and date range.'
            );
          }

        } catch (
        error
        ) {

          console.error(
            'CDSE satellite search failed:',
            error
          );

          setResults(
            []
          );

          setErrorMsg(
            error instanceof Error
              ? error.message
              : 'CDSE satellite search failed.'
          );

        } finally {

          setIsSearching(
            false
          );
        }
      };

    // --------------------------------------------------------
    // INGEST PRODUCT
    // --------------------------------------------------------

    const handleAddProduct =
      async (
        product: SatelliteProduct
      ) => {

        const productId =
          product.product_id;

        if (
          !productId
        ) {
          setErrorMsg(
            'This satellite product has no valid product ID.'
          );

          return;
        }

        if (
          addedIds.includes(
            productId
          )
        ) {
          return;
        }

        setErrorMsg(
          null
        );

        setIsIngestingId(
          productId
        );

        try {

          // --------------------------------------------------
          // Real CDSE ingestion.
          //
          // This requests backend ingestion instead of merely
          // placing catalogue metadata into the workspace.
          // --------------------------------------------------

          const observation =
            await satQueryService
              .ingestCopernicusProduct(
                productId,
                selectedCollection ===
                  'sentinel-1-grd'
                  ? 'SAR'
                  : 'MULTISPECTRAL',
                true
              );

          if (
            !observation
          ) {
            throw new Error(
              'CDSE ingestion returned no observation.'
            );
          }

          // --------------------------------------------------
          // Ensure the observation actually contains a local
          // backend/model asset.
          // --------------------------------------------------

          const observationAny =
            observation as any;

          const localPath =
            observationAny.filePath ||
            observationAny.file_path ||
            observationAny.localPath ||
            observationAny.local_path;

          if (
            !localPath
          ) {
            throw new Error(
              'CDSE product metadata was received, but no downloadable/local analysis asset was returned.'
            );
          }

          // --------------------------------------------------
          // Add to workspace.
          // --------------------------------------------------

          if (
            onAddProductAsObservation
          ) {
            onAddProductAsObservation(
              observation
            );
          }

          setAddedIds(
            (
              previous
            ) => (
              previous.includes(
                productId
              )
                ? previous
                : [
                  ...previous,
                  productId,
                ]
            )
          );

        } catch (
        error
        ) {

          console.error(
            'CDSE product ingestion failed:',
            error
          );

          setErrorMsg(
            error instanceof Error
              ? error.message
              : `Unable to ingest ${productId}.`
          );

        } finally {

          setIsIngestingId(
            null
          );
        }
      };

    // ==========================================================
    // RENDER
    // ==========================================================

    return (
      <div
        className="
          fixed inset-0 z-50
          flex items-center justify-center
          p-4
          bg-slate-950/80
          backdrop-blur-md
          animate-fadeIn
        "
      >

        <div
          className="
            relative
            flex
            max-h-[90vh]
            w-full
            max-w-4xl
            flex-col
            overflow-hidden
            rounded-2xl
            border
            border-sat-border
            bg-sat-surface
            shadow-2xl
          "
        >

          {/* ==================================================
              HEADER
          ================================================== */}

          <div
            className="
              flex
              items-center
              justify-between
              border-b
              border-sat-border
              bg-sat-panel/80
              px-6
              py-4
            "
          >

            <div className="flex items-center gap-3">

              <div
                className="
                  flex
                  h-10
                  w-10
                  items-center
                  justify-center
                  rounded-xl
                  border
                  border-sat-accent/30
                  bg-sat-accent/10
                "
              >
                <Globe
                  className="
                    h-5
                    w-5
                    text-sat-accent
                  "
                />
              </div>

              <div>

                <h2
                  className="
                    font-display
                    text-base
                    font-bold
                    text-sat-text
                  "
                >
                  Find Satellite Data
                </h2>

                <p
                  className="
                    text-[11px]
                    text-sat-muted
                  "
                >
                  Live Copernicus Data Space
                  catalogue search
                </p>

              </div>

            </div>

            <button
              onClick={onClose}
              className="
                flex
                h-8
                w-8
                items-center
                justify-center
                rounded-lg
                border
                border-sat-border
                bg-sat-bg
                text-sat-muted
                transition-colors
                hover:border-sat-accent
                hover:text-sat-text
              "
              aria-label="Close satellite search"
            >
              <X
                className="h-4 w-4"
              />
            </button>

          </div>


          {/* ==================================================
              MAIN
          ================================================== */}

          <div
            className="
              grid
              grid-cols-1
              md:grid-cols-12
              flex-1
              min-h-0
              overflow-hidden
            "
          >

            {/* ================================================
                LEFT SEARCH PANEL
            ================================================ */}

            <div
              className="
                md:col-span-4
                border-r
                border-sat-border
                bg-sat-bg/50
                p-5
                overflow-y-auto
                space-y-5
              "
            >

              {/* Region */}

              <div>

                <label
                  className="
                    text-[10px]
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-dim
                    flex
                    items-center
                    gap-1.5
                    mb-2
                  "
                >
                  <MapPin
                    className="
                      h-3
                      w-3
                      text-sat-accent
                    "
                  />
                  Target Region
                </label>

                <div className="space-y-1.5">

                  {LOCATION_PRESETS.map(
                    (
                      preset
                    ) => {

                      const isSelected =
                        selectedPreset.name ===
                        preset.name;

                      return (
                        <button
                          key={
                            preset.name
                          }
                          onClick={() =>
                            setSelectedPreset(
                              preset
                            )
                          }
                          className={`
                            w-full
                            text-left
                            p-2.5
                            rounded-lg
                            border
                            text-xs
                            transition-all
                            ${isSelected
                              ? 'border-sat-accent bg-sat-accent/10 font-bold text-sat-text'
                              : 'border-sat-border bg-sat-surface text-sat-muted hover:border-sat-borderLight'
                            }
                          `}
                        >

                          <div
                            className="
                              text-[11px]
                              font-medium
                              text-sat-text
                            "
                          >
                            {preset.name}
                          </div>

                          <div
                            className="
                              text-[9px]
                              text-sat-dim
                            "
                          >
                            {preset.region}
                          </div>

                        </button>
                      );
                    }
                  )}

                </div>

              </div>


              {/* Collection */}

              <div>

                <label
                  className="
                    text-[10px]
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-dim
                    flex
                    items-center
                    gap-1.5
                    mb-2
                  "
                >
                  <Satellite
                    className="
                      h-3
                      w-3
                      text-sat-accent
                    "
                  />
                  Satellite Collection
                </label>

                <select
                  value={
                    collection
                  }
                  onChange={(
                    event
                  ) =>
                    handleCollectionChange(
                      event.target.value
                    )
                  }
                  className="
                    w-full
                    rounded-lg
                    border
                    border-sat-border
                    bg-sat-surface
                    p-2.5
                    text-xs
                    text-sat-text
                    focus:border-sat-accent
                    focus:outline-none
                  "
                >

                  {COLLECTIONS.map(
                    (
                      item
                    ) => (
                      <option
                        key={
                          item.value
                        }
                        value={
                          item.value
                        }
                      >
                        {item.label}
                      </option>
                    )
                  )}

                </select>

                <div
                  className="
                    mt-2
                    rounded-lg
                    border
                    border-sat-border
                    bg-sat-surface/60
                    p-2.5
                    text-[9px]
                    text-sat-muted
                  "
                >
                  Searching only the selected
                  collection. Unrelated products
                  are not substituted.
                </div>

              </div>


              {/* Date Range */}

              <div>

                <label
                  className="
                    text-[10px]
                    font-bold
                    uppercase
                    tracking-wider
                    text-sat-dim
                    flex
                    items-center
                    gap-1.5
                    mb-2
                  "
                >
                  <Calendar
                    className="
                      h-3
                      w-3
                      text-sat-accent
                    "
                  />
                  Acquisition Period
                </label>

                <div
                  className="
                    grid
                    grid-cols-2
                    gap-2
                  "
                >

                  <div>

                    <span
                      className="
                        text-[8px]
                        text-sat-dim
                        block
                        mb-1
                      "
                    >
                      From
                    </span>

                    <input
                      type="date"
                      value={
                        startDate
                      }
                      onChange={(
                        event
                      ) =>
                        setStartDate(
                          event.target.value
                        )
                      }
                      max={
                        endDate
                      }
                      className="
                        w-full
                        rounded-md
                        border
                        border-sat-border
                        bg-sat-surface
                        p-1.5
                        text-[10px]
                        text-sat-text
                        focus:border-sat-accent
                        focus:outline-none
                      "
                    />

                  </div>

                  <div>

                    <span
                      className="
                        text-[8px]
                        text-sat-dim
                        block
                        mb-1
                      "
                    >
                      To
                    </span>

                    <input
                      type="date"
                      value={
                        endDate
                      }
                      onChange={(
                        event
                      ) =>
                        setEndDate(
                          event.target.value
                        )
                      }
                      min={
                        startDate
                      }
                      className="
                        w-full
                        rounded-md
                        border
                        border-sat-border
                        bg-sat-surface
                        p-1.5
                        text-[10px]
                        text-sat-text
                        focus:border-sat-accent
                        focus:outline-none
                      "
                    />

                  </div>

                </div>

              </div>


              {/* Cloud */}

              <div>

                <div
                  className="
                    flex
                    items-center
                    justify-between
                    mb-1.5
                  "
                >

                  <label
                    className="
                      text-[10px]
                      font-bold
                      uppercase
                      tracking-wider
                      text-sat-dim
                      flex
                      items-center
                      gap-1.5
                    "
                  >
                    <Cloud
                      className="
                        h-3
                        w-3
                        text-sat-accent
                      "
                    />

                    Max Cloud Cover
                  </label>

                  <span
                    className="
                      text-[10px]
                      font-bold
                      text-sat-accent
                    "
                  >
                    {supportsCloudFilter
                      ? `${maxCloud}%`
                      : 'N/A for SAR'}
                  </span>

                </div>

                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={
                    maxCloud
                  }
                  disabled={
                    !supportsCloudFilter
                  }
                  onChange={(
                    event
                  ) =>
                    setMaxCloud(
                      Number(
                        event.target.value
                      )
                    )
                  }
                  className="
                    w-full
                    accent-sat-accent
                    disabled:opacity-40
                  "
                />

              </div>


              {/* Search */}

              <button
                type="button"
                onClick={
                  handleSearch
                }
                disabled={
                  isSearching
                }
                className="
                  w-full
                  flex
                  items-center
                  justify-center
                  gap-2
                  rounded-xl
                  bg-sat-accent
                  py-3
                  text-xs
                  font-bold
                  text-slate-950
                  hover:bg-sat-accent/90
                  disabled:opacity-50
                  transition-all
                  shadow-lg
                  shadow-sat-accent/20
                "
              >

                {isSearching ? (
                  <>
                    <Loader2
                      className="
                        h-4
                        w-4
                        animate-spin
                      "
                    />

                    <span>
                      Searching CDSE...
                    </span>
                  </>
                ) : (
                  <>
                    <Search
                      className="
                        h-4
                        w-4
                      "
                    />

                    <span>
                      Search Satellite Data
                    </span>
                  </>
                )}

              </button>

            </div>


            {/* ================================================
                RIGHT RESULTS
            ================================================ */}

            <div
              className="
                md:col-span-8
                p-5
                overflow-y-auto
                space-y-4
              "
            >

              {/* Results heading */}

              <div
                className="
                  flex
                  items-center
                  justify-between
                "
              >

                <div
                  className="
                    text-xs
                    font-bold
                    text-sat-text
                    flex
                    items-center
                    gap-2
                  "
                >

                  <span>
                    Available Scenes
                  </span>

                  <span
                    className="
                      rounded-full
                      bg-sat-accent/10
                      px-2
                      py-0.5
                      text-[10px]
                      font-bold
                      text-sat-accent
                      border
                      border-sat-accent/20
                    "
                  >
                    {results.length}
                    {' '}
                    found
                  </span>

                </div>

                <span
                  className="
                    text-[10px]
                    text-sat-dim
                  "
                >
                  Source: Copernicus Data Space
                </span>

              </div>


              {/* Error / information */}

              {errorMsg && (
                <div
                  className="
                    flex
                    items-start
                    gap-2
                    rounded-xl
                    border
                    border-sat-border
                    bg-sat-bg/80
                    p-3
                    text-[10px]
                    text-sat-muted
                  "
                >

                  <AlertCircle
                    className="
                      h-4
                      w-4
                      shrink-0
                      text-sat-accent
                    "
                  />

                  <span>
                    {errorMsg}
                  </span>

                </div>
              )}


              {/* Initial state */}

              {!hasSearched &&
                results.length === 0 && (
                  <div
                    className="
                      flex
                      min-h-[320px]
                      items-center
                      justify-center
                      rounded-2xl
                      border
                      border-dashed
                      border-sat-border
                      bg-sat-bg/50
                      px-6
                      text-center
                    "
                  >

                    <div>

                      <Satellite
                        className="
                          mx-auto
                          mb-3
                          h-8
                          w-8
                          text-sat-dim
                        "
                      />

                      <p
                        className="
                          text-sm
                          font-semibold
                          text-sat-text
                        "
                      >
                        Search the live catalogue
                      </p>

                      <p
                        className="
                          mt-1
                          text-[10px]
                          text-sat-muted
                        "
                      >
                        Choose a region, collection,
                        and acquisition period.
                      </p>

                    </div>

                  </div>
                )}


              {/* Empty results */}

              {hasSearched &&
                !isSearching &&
                results.length === 0 && (
                  <div
                    className="
                      flex
                      min-h-[320px]
                      items-center
                      justify-center
                      rounded-2xl
                      border
                      border-sat-border
                      bg-sat-bg/50
                      px-6
                      text-center
                    "
                  >

                    <div>

                      <Search
                        className="
                          mx-auto
                          mb-3
                          h-8
                          w-8
                          text-sat-dim
                        "
                      />

                      <p
                        className="
                          text-sm
                          font-semibold
                          text-sat-text
                        "
                      >
                        No matching scenes found
                      </p>

                      <p
                        className="
                          mt-1
                          text-[10px]
                          text-sat-muted
                        "
                      >
                        Try widening the date range
                        or cloud-cover threshold.
                      </p>

                    </div>

                  </div>
                )}


              {/* Results */}

              {results.length > 0 && (
                <div
                  className="
                    grid
                    grid-cols-1
                    gap-3
                  "
                >

                  {results.map(
                    (
                      product
                    ) => {

                      const productId =
                        product.product_id;

                      const isAdded =
                        addedIds.includes(
                          productId
                        );

                      const isIngesting =
                        isIngestingId ===
                        productId;

                      const quicklookUrl =
                        product.thumbnail_url ||
                        satQueryService
                          .getCopernicusQuicklookUrl(
                            productId
                          );

                      return (
                        <div
                          key={
                            productId
                          }
                          className="
                            flex
                            flex-col
                            sm:flex-row
                            items-center
                            gap-4
                            rounded-xl
                            border
                            border-sat-border
                            bg-sat-bg/80
                            p-3.5
                            hover:border-sat-borderLight
                            transition-all
                          "
                        >

                          {/* Preview */}

                          <div
                            className="
                              h-24
                              w-full
                              sm:w-28
                              shrink-0
                              overflow-hidden
                              rounded-lg
                              border
                              border-sat-border
                              bg-sat-surface
                            "
                          >

                            {quicklookUrl ? (
                              <img
                                src={
                                  quicklookUrl
                                }
                                alt={
                                  product.platform ||
                                  product.product_id
                                }
                                className="
                                  h-full
                                  w-full
                                  object-cover
                                "
                                loading="lazy"
                                onError={(
                                  event
                                ) => {
                                  (
                                    event.currentTarget
                                      as HTMLImageElement
                                  ).style.display =
                              'none';
                                }}
                              />
                            ) : (
                            <div
                              className="
                                  h-full
                                  w-full
                                  flex
                                  items-center
                                  justify-center
                                  text-[9px]
                                  text-sat-dim
                                "
                            >
                              No quicklook
                            </div>
                            )}

                          </div>


                          {/* Product metadata */}

                          <div
                            className="
                              min-w-0
                              flex-1
                              space-y-1
                            "
                          >

                            <div
                              className="
                                flex
                                flex-wrap
                                items-center
                                gap-2
                              "
                            >

                              <span
                                className="
                                  rounded
                                  bg-sat-accent/10
                                  px-1.5
                                  py-0.5
                                  text-[8px]
                                  font-bold
                                  text-sat-accent
                                  border
                                  border-sat-accent/20
                                "
                              >
                                {
                                  product.platform ||
                                  'Satellite'
                                }
                              </span>

                              <span
                                className="
                                  text-[9px]
                                  text-sat-dim
                                "
                              >
                                {formatProductDate(
                                  product.acquisition_datetime
                                )}
                              </span>

                              {product.processing_level && (
                                <span
                                  className="
                                    text-[8px]
                                    text-sat-muted
                                  "
                                >
                                  {
                                    product.processing_level
                                  }
                                </span>
                              )}

                            </div>


                            <h4
                              className="
                                text-xs
                                font-bold
                                text-sat-text
                                truncate
                              "
                              title={
                                product.metadata?.name as string
                              }
                            >
                              {String(
                                product.metadata?.name ||
                                product.product_id
                              )}
                            </h4>


                            <div
                              className="
                                flex
                                flex-wrap
                                items-center
                                gap-3
                                text-[9px]
                                text-sat-muted
                              "
                            >

                              <span>
                                Resolution:{' '}
                                {product.resolution !== null &&
                                  product.resolution !== undefined
                                  ? `${product.resolution}m`
                                  : 'N/A'}
                              </span>

                              <span>
                                Cloud:{' '}
                                {product.cloud_cover !== null &&
                                  product.cloud_cover !== undefined
                                  ? `${Number(product.cloud_cover).toFixed(1)}%`
                                  : 'N/A'}
                              </span>

                              <span className="uppercase">
                                Mode:{' '}
                                {product.modality ||
                                  'UNKNOWN'}
                              </span>

                            </div>


                            <div
                              className="
                                truncate
                                text-[8px]
                                text-sat-dim
                              "
                              title={
                                product.product_id
                              }
                            >
                              ID: {
                                product.product_id
                              }
                            </div>

                          </div>


                          {/* Action */}

                          <button
                            onClick={() =>
                              handleAddProduct(
                                product
                              )
                            }
                            disabled={
                              isAdded ||
                              isIngesting
                            }
                            className={`
                              shrink-0
                              flex
                              items-center
                              gap-1.5
                              rounded-lg
                              px-3
                              py-2
                              text-xs
                              font-bold
                              transition-all
                              ${isAdded
                                ? 'border border-sat-stable/30 bg-sat-stable/10 text-sat-stable cursor-default'
                                : isIngesting
                                  ? 'border border-sat-border bg-sat-surface text-sat-muted cursor-wait'
                                  : 'bg-sat-accent text-slate-950 hover:bg-sat-accent/90'
                              }
                            `}
                          >

                            {isAdded ? (
                              <>
                                <Check
                                  className="
                                    h-3.5
                                    w-3.5
                                  "
                                />

                                <span>
                                  Added
                                </span>
                              </>
                            ) : isIngesting ? (
                              <>
                                <Loader2
                                  className="
                                    h-3.5
                                    w-3.5
                                    animate-spin
                                  "
                                />

                                <span>
                                  Ingesting...
                                </span>
                              </>
                            ) : (
                              <>
                                <Download
                                  className="
                                    h-3.5
                                    w-3.5
                                  "
                                />

                                <span>
                                  Add & Ingest
                                </span>
                              </>
                            )}

                          </button>

                        </div>
                      );
                    }
                  )}

                </div>
              )}

            </div>

          </div>

        </div>

      </div>
    );
  };