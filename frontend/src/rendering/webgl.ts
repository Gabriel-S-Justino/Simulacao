export function hasWebGL2(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return canvas.getContext("webgl2") !== null;
  } catch {
    return false;
  }
}
