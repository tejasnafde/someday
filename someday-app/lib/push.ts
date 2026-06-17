import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import { Platform } from "react-native";

const extra = Constants.expoConfig?.extra as Record<string, any>;
const PROJECT_ID: string = extra?.eas?.projectId ?? "";

export async function registerForPush(): Promise<string | null> {
  if (Platform.OS !== "android") return null; // ponytail: iOS when needed
  const { status: existing } = await Notifications.getPermissionsAsync();
  const { status } =
    existing === "granted"
      ? { status: existing }
      : await Notifications.requestPermissionsAsync();
  if (status !== "granted") return null;
  try {
    const { data } = await Notifications.getExpoPushTokenAsync({ projectId: PROJECT_ID });
    return data;
  } catch {
    return null;
  }
}
