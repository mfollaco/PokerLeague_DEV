// Stable, reusable player accent colors (muted, professional)
// If a player isn't listed, we fall back to a neutral slate.
export const PLAYER_COLORS = {
  "Steve C": "#b08d57",   // muted gold
  "Bill B":  "#6f8fa3",   // steel blue
  "Mike F":  "#7a8f6a",   // muted olive
  "Joe Ferrigno": "#8a6f8f",
  "Todd L":  "#7f8794",
  "Gerry I": "#6f7f8f",
  "Phil Z":  "#8f7a6f",
  "Joe Fitz":"#6f8f84",
  "Russ T":  "#7a7a8f",
  "Josh T":  "#8f6f6f",
  "Dan T":   "#6f8f6f",
  "Dave B":  "#8a8f6f",
  "Josh H":  "#6f6f8f",
  "Dan P":   "#8f6f84",
  "Chris":   "#6f8f8f",
  "Greg":    "#8a7f6f"
};

export const DEFAULT_PLAYER_COLOR = "#6f8fa3";

export function getPlayerColor(name) {
  return PLAYER_COLORS[name] || DEFAULT_PLAYER_COLOR;
}