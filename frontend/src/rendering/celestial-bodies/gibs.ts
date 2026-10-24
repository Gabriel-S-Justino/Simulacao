/**
 * Camadas globais da NASA GIBS via WMS (EPSG:4326, equiretangular), que mapeiam
 * diretamente nas coordenadas UV de uma esfera. Requisição única por camada,
 * resolução limitada (não baixa a pirâmide de tiles).
 * Docs: https://nasa-gibs.github.io/gibs-api-docs/
 */
const GIBS_BASE =
  (import.meta.env.VITE_GIBS_BASE_URL as string | undefined) ?? "https://gibs.earthdata.nasa.gov";

export interface GibsLayer {
  id: string;
  title: string;
  format: "image/jpeg" | "image/png";
  temporal: false;
  note: string;
}

export const BLUE_MARBLE: GibsLayer = {
  id: "BlueMarble_ShadedRelief_Bathymetry",
  title: "Blue Marble (relevo e batimetria)",
  format: "image/jpeg",
  temporal: false,
  note: "Mosaico composto estático, não é imagem em tempo real.",
};

export const BLACK_MARBLE: GibsLayer = {
  id: "VIIRS_Black_Marble",
  title: "VIIRS Black Marble (luzes noturnas, 2016)",
  format: "image/png",
  temporal: false,
  note: "Composição anual de 2016.",
};

export function gibsWmsUrl(layer: GibsLayer, width = 4096): string {
  const params = new URLSearchParams({
    SERVICE: "WMS",
    REQUEST: "GetMap",
    VERSION: "1.3.0",
    LAYERS: layer.id,
    CRS: "EPSG:4326",
    BBOX: "-90,-180,90,180",
    WIDTH: String(width),
    HEIGHT: String(width / 2),
    FORMAT: layer.format,
  });
  return `${GIBS_BASE}/wms/epsg4326/best/wms.cgi?${params.toString()}`;
}
