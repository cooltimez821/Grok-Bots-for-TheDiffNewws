import type { BiasBand } from "./types";

/** Simple L/C/R meter widths derived from the frozen bias_band enum. */
export function biasMeterWidths(band: BiasBand): {
  left: number;
  center: number;
  right: number;
} {
  switch (band) {
    case "left":
      return { left: 70, center: 20, right: 10 };
    case "lean_left":
      return { left: 50, center: 35, right: 15 };
    case "center":
      return { left: 15, center: 70, right: 15 };
    case "lean_right":
      return { left: 15, center: 35, right: 50 };
    case "right":
      return { left: 10, center: 20, right: 70 };
    case "mixed":
      return { left: 34, center: 32, right: 34 };
  }
}

export function biasBandLabel(band: BiasBand): string {
  switch (band) {
    case "left":
      return "Left";
    case "lean_left":
      return "Lean left";
    case "center":
      return "Center";
    case "lean_right":
      return "Lean right";
    case "right":
      return "Right";
    case "mixed":
      return "Mixed";
  }
}
