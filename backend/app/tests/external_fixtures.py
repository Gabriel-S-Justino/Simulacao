# ruff: noqa: E501
"""Respostas de exemplo para os testes dos adaptadores.

ORIGEM: montadas a partir da estrutura descrita na documentação oficial de cada
fonte (links nos módulos de app/integrations). NÃO são respostas gravadas ao vivo:
o ambiente onde foram escritas não alcança os hosts da NASA/JPL. Os valores numéricos
são ilustrativos e não devem ser usados como dado científico. A verificação ao vivo
está registrada como pendente em docs/api-integrations.md.
"""

from __future__ import annotations

from typing import Any

APOD: dict[str, Any] = {
    "date": "2024-05-10",
    "title": "Exemplo de título",
    "explanation": "Texto de exemplo.",
    "media_type": "image",
    "url": "https://apod.nasa.gov/apod/image/2405/exemplo.jpg",
    "hdurl": "https://apod.nasa.gov/apod/image/2405/exemplo_hd.jpg",
    "copyright": "Autor de Exemplo",
    "service_version": "v1",
}

# NeoWs envia números de distância/velocidade como strings.
NEOWS_FEED: dict[str, Any] = {
    "links": {},
    "element_count": 1,
    "near_earth_objects": {
        "2024-05-10": [
            {
                "id": "1000001",
                "neo_reference_id": "1000001",
                "name": "(2099 XX1)",
                "nasa_jpl_url": "https://ssd.jpl.nasa.gov/tools/sbdb_lookup.html#/?sstr=1000001",
                "absolute_magnitude_h": 22.1,
                "estimated_diameter": {
                    "kilometers": {"estimated_diameter_min": 0.1, "estimated_diameter_max": 0.2},
                    "meters": {"estimated_diameter_min": 100.0, "estimated_diameter_max": 200.0},
                },
                "is_potentially_hazardous_asteroid": False,
                "close_approach_data": [
                    {
                        "close_approach_date": "2024-05-10",
                        "close_approach_date_full": "2024-May-10 12:00",
                        "epoch_date_close_approach": 1715342400000,
                        "relative_velocity": {
                            "kilometers_per_second": "10.5",
                            "kilometers_per_hour": "37800",
                        },
                        "miss_distance": {
                            "astronomical": "0.02",
                            "lunar": "7.8",
                            "kilometers": "2991957.4",
                        },
                        "orbiting_body": "Earth",
                    }
                ],
                "is_sentry_object": False,
            }
        ]
    },
}

DONKI_FLR: list[dict[str, Any]] = [
    {
        "flrID": "2024-05-10T06:27:00-FLR-001",
        "beginTime": "2024-05-10T06:27Z",
        "peakTime": "2024-05-10T06:54Z",
        "endTime": "2024-05-10T07:06Z",
        "classType": "X3.9",
        "sourceLocation": "S17W29",
        "activeRegionNum": 13664,
        "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/FLR/00000/-1",
    }
]

DONKI_GST: list[dict[str, Any]] = [
    {
        "gstID": "2024-05-10T15:00:00-GST-001",
        "startTime": "2024-05-10T15:00Z",
        "allKpIndex": [
            {"observedTime": "2024-05-10T18:00Z", "kpIndex": 8.0, "source": "NOAA"},
            {"observedTime": "2024-05-10T21:00Z", "kpIndex": 9.0, "source": "NOAA"},
        ],
        "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/GST/00000/-1",
    }
]

DONKI_CME: list[dict[str, Any]] = [
    {
        "activityID": "2024-05-10T07:12:00-CME-001",
        "startTime": "2024-05-10T07:12Z",
        "sourceLocation": "S17W29",
        "note": "Exemplo.",
        "link": "https://kauai.ccmc.gsfc.nasa.gov/DONKI/view/CME/00000/-1",
        "cmeAnalyses": [
            {"speed": 900.0, "halfAngle": 40.0, "type": "O", "isMostAccurate": False},
            {
                "time21_5": "2024-05-10T10:00Z",
                "latitude": -15.0,
                "longitude": 30.0,
                "halfAngle": 45.0,
                "speed": 1200.0,
                "type": "O",
                "isMostAccurate": True,
            },
        ],
    }
]

EPIC: list[dict[str, Any]] = [
    {
        "identifier": "20240510003633",
        "caption": "Imagem de exemplo",
        "image": "epic_1b_20240510003633",
        "version": "03",
        "date": "2024-05-10 00:31:45",
        "centroid_coordinates": {"lat": 10.5, "lon": 160.2},
        "dscovr_j2000_position": {"x": -1.2e6, "y": -6.0e5, "z": -2.0e5},
        "lunar_j2000_position": {"x": 1.0e5, "y": 3.0e5, "z": 1.5e5},
        "sun_j2000_position": {"x": -9.0e7, "y": -1.0e8, "z": -4.5e7},
        "attitude_quaternions": {"q0": 0.0, "q1": 0.0, "q2": 0.0, "q3": 1.0},
    },
    {
        "identifier": "20240510014136",
        "caption": "Imagem de exemplo",
        "image": "epic_1b_20240510014136",
        "version": "03",
        "date": "2024-05-10 01:36:48",
        "centroid_coordinates": {"lat": 10.4, "lon": 144.0},
        "dscovr_j2000_position": {"x": -1.2e6, "y": -6.0e5, "z": -2.0e5},
        "lunar_j2000_position": {"x": 1.0e5, "y": 3.0e5, "z": 1.5e5},
        "sun_j2000_position": {"x": -9.0e7, "y": -1.0e8, "z": -4.5e7},
    },
]

EONET: dict[str, Any] = {
    "title": "EONET Events",
    "events": [
        {
            "id": "EONET_0001",
            "title": "Tempestade de exemplo",
            "description": None,
            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_0001",
            "closed": None,
            "categories": [{"id": "severeStorms", "title": "Severe Storms"}],
            "sources": [{"id": "JTWC", "url": "https://www.metoc.navy.mil/jtwc/"}],
            "geometry": [
                {
                    "magnitudeValue": 45.0,
                    "magnitudeUnit": "kts",
                    "date": "2024-05-09T18:00:00Z",
                    "type": "Point",
                    "coordinates": [130.0, 12.0],
                },
                {
                    "magnitudeValue": 55.0,
                    "magnitudeUnit": "kts",
                    "date": "2024-05-10T00:00:00Z",
                    "type": "Point",
                    "coordinates": [129.0, 13.0],
                },
            ],
        },
        {
            "id": "EONET_0002",
            "title": "Incêndio de exemplo",
            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_0002",
            "closed": None,
            "categories": [{"id": "wildfires", "title": "Wildfires"}],
            "sources": [{"id": "IRWIN", "url": "https://irwin.doi.gov/observer/"}],
            "geometry": [
                {
                    "magnitudeValue": None,
                    "magnitudeUnit": None,
                    "date": "2024-05-08T00:00:00Z",
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-120.0, 40.0],
                            [-119.0, 40.0],
                            [-119.0, 41.0],
                            [-120.0, 41.0],
                            [-120.0, 40.0],
                        ]
                    ],
                }
            ],
        },
    ],
}

ISS: dict[str, Any] = {
    "iss_position": {"latitude": -19.783929798887073, "longitude": -72.29753187401747},
    "message": "success",
    "timestamp": 1454357342,
}

# Linhas longas abaixo reproduzem o layout de colunas do Horizons.
# Corpo de "result" do Horizons com CSV_FORMAT=YES e VEC_TABLE=2 (colunas pelo cabeçalho).
HORIZONS_RESULT = """API VERSION: 1.2
API SOURCE: NASA/JPL Horizons API

*******************************************************************************
 Revised: Exemplo                   Moon / (Earth)                          301
*******************************************************************************
Ephemeris / API_USER
Target body name: Moon (301)                      {source: DE441}
Center body name: Earth (399)                     {source: DE441}
*******************************************************************************
            JDTDB,            Calendar Date (TDB),                      X,                      Y,                      Z,                     VX,                     VY,                     VZ,
**************************************************************************************************************************************************************************************************
$$SOE
2460440.500000000, A.D. 2024-May-10 00:00:00.0000,  3.000000000000000E+05,  2.000000000000000E+05,  1.000000000000000E+05, -5.000000000000000E-01,  6.000000000000000E-01,  3.000000000000000E-01,
2460440.541666667, A.D. 2024-May-10 01:00:00.0000,  2.980000000000000E+05,  2.020000000000000E+05,  1.010000000000000E+05, -5.100000000000000E-01,  5.900000000000000E-01,  3.000000000000000E-01,
$$EOE
*******************************************************************************
"""

SBDB_OK: dict[str, Any] = {
    "signature": {"source": "NASA/JPL Small-Body Database (SBDB) API", "version": "1.3"},
    "object": {
        "des": "433",
        "spkid": "2000433",
        "fullname": "433 Eros (A898 PA)",
        "shortname": "433 Eros",
        "kind": "an",
        "neo": True,
        "pha": False,
        "orbit_class": {"name": "Amor", "code": "AMO"},
        "orbit_id": "exemplo",
    },
    "orbit": {
        "epoch": "2460600.5",
        "equinox": "J2000",
        "source": "JPL",
        "moid": "0.15",
        "condition_code": "0",
        "first_obs": "1893-10-29",
        "last_obs": "2024-01-01",
        "elements": [
            {
                "name": "e",
                "label": "e",
                "title": "eccentricity",
                "value": "0.2229",
                "sigma": "1.0E-9",
                "units": None,
            },
            {
                "name": "a",
                "label": "a",
                "title": "semi-major axis",
                "value": "1.458",
                "sigma": "2.0E-10",
                "units": "au",
            },
            {
                "name": "i",
                "label": "i",
                "title": "inclination",
                "value": "10.83",
                "sigma": "1.0E-7",
                "units": "deg",
            },
        ],
    },
}

SBDB_MULTI: dict[str, Any] = {
    "signature": {"version": "1.0", "source": "NASA/JPL Small-Body Database (SBDB) API"},
    "code": 300,
    "message": "specified query matched more than one object",
    "list": [{"pdes": "1P", "name": "1P/Halley"}, {"pdes": "1P-A", "name": "Exemplo"}],
}

CAD: dict[str, Any] = {
    "signature": {"source": "NASA/JPL SBDB Close Approach Data API", "version": "1.5"},
    "count": "1",
    "fields": [
        "des",
        "orbit_id",
        "jd",
        "cd",
        "dist",
        "dist_min",
        "dist_max",
        "v_rel",
        "v_inf",
        "t_sigma_f",
        "h",
        "diameter",
        "diameter_sigma",
        "fullname",
    ],
    "data": [
        [
            "2099 XX1",
            "5",
            "2460445.123",
            "2024-May-15 14:57",
            "0.01",
            "0.0099",
            "0.0101",
            "8.5",
            "8.4",
            "< 00:01",
            "24.5",
            None,
            None,
            "       (2099 XX1)",
        ]
    ],
}

GIBS_CAPABILITIES = b"""<?xml version="1.0" encoding="UTF-8"?>
<Capabilities xmlns="http://www.opengis.net/wmts/1.0"
  xmlns:ows="http://www.opengis.net/ows/1.1" version="1.0.0">
  <Contents>
    <Layer>
      <ows:Title>Corrected Reflectance (True Color, VIIRS, Suomi NPP)</ows:Title>
      <ows:Identifier>VIIRS_SNPP_CorrectedReflectance_TrueColor</ows:Identifier>
      <Format>image/jpeg</Format>
      <TileMatrixSetLink><TileMatrixSet>250m</TileMatrixSet></TileMatrixSetLink>
      <Dimension>
        <ows:Identifier>Time</ows:Identifier>
        <ows:UOM>ISO8601</ows:UOM>
        <Default>2024-05-10</Default>
        <Current>false</Current>
        <Value>2015-11-24/2024-05-10/P1D</Value>
      </Dimension>
    </Layer>
    <Layer>
      <ows:Title>Blue Marble</ows:Title>
      <ows:Identifier>BlueMarble_ShadedRelief_Bathymetry</ows:Identifier>
      <Format>image/jpeg</Format>
      <TileMatrixSetLink><TileMatrixSet>500m</TileMatrixSet></TileMatrixSetLink>
    </Layer>
    <Layer>
      <ows:Title>Outra camada</ows:Title>
      <ows:Identifier>Unrelated_Layer</ows:Identifier>
      <Format>image/png</Format>
    </Layer>
    <TileMatrixSet><ows:Identifier>250m</ows:Identifier></TileMatrixSet>
  </Contents>
</Capabilities>
"""
