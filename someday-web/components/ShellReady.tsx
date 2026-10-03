"use client";

import { useEffect } from "react";
import { notifyShellReady, shellBridge } from "@/lib/nativeShell";

// Tells the native shell to drop its splash once the first real screen is up.
// Loading placeholders (Spinner, Skeleton) carry data-loading, so "real" means
// none of them is in the DOM. Sent once per page load; in a browser there is
// no bridge and this does nothing. The shell hides the splash after 8 s anyway.
let sent = false;

export function ShellReady() {
  useEffect(() => {
    if (sent || !shellBridge()) return;
    const check = () => {
      if (sent || document.querySelector("[data-loading]")) return;
      sent = true;
      observer.disconnect();
      notifyShellReady();
    };
    const observer = new MutationObserver(check);
    observer.observe(document.body, { childList: true, subtree: true });
    check();
    return () => observer.disconnect();
  }, []);
  return null;
}
