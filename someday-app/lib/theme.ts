import { useColorScheme } from "react-native";

const light = {
  bg: "#F3EEF9",
  card: "rgba(255,255,255,0.80)",
  cardSoft: "rgba(255,255,255,0.55)",
  brd: "rgba(150,128,186,0.18)",
  txt: "#1C1525",
  txtM: "#5A4E72",
  txtL: "#9B90B4",
  acc: "#5B4B8A",
  accM: "#8B78C0",
  accL: "rgba(91,75,138,0.10)",
  pink: "#FF4B6E",
  green: "#00B87A",
};

const dark: typeof light = {
  bg: "#101010",
  card: "rgba(30,30,30,0.92)",
  cardSoft: "rgba(22,22,22,0.80)",
  brd: "rgba(255,255,255,0.11)",
  txt: "#EEEEEE",
  txtM: "#888888",
  txtL: "#444444",
  acc: "#9B8DC4",
  accM: "#BDB0E0",
  accL: "rgba(155,141,196,0.11)",
  pink: "#E8607A",
  green: "#2DBF8A",
};

export function useTheme() {
  return useColorScheme() === "dark" ? dark : light;
}
