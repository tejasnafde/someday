"use client";

import { useEffect, useState } from "react";
import { cn } from "cn";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/shadcn/alert-dialog";

type ConfirmOptions = {
  title: string;
  description?: string;
  confirmLabel?: string;
  destructive?: boolean;  // Delete, Leave, Remove: ghost button with --cp text
  notice?: boolean;       // one OK button, the replacement for alert()
};
type Request = ConfirmOptions & { resolve: (ok: boolean) => void };

let show: ((r: Request) => void) | null = null;

// Drop-in for window.confirm() / alert(): `if (!(await confirmDialog({...}))) return;`.
// Native dialogs look foreign and show the page URL as their title inside the
// Android WebView shell. Needs <ConfirmHost /> mounted once (root layout).
export function confirmDialog(options: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    if (show) show({ ...options, resolve });
    else resolve(window.confirm(options.title));
  });
}

export function ConfirmHost() {
  const [req, setReq] = useState<Request | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    show = (r) => { setReq(r); setOpen(true); };
    return () => { show = null; };
  }, []);

  // Action and Cancel also fire onOpenChange(false); resolving twice is a no-op.
  function close(ok: boolean) {
    req?.resolve(ok);
    setOpen(false);
  }

  return (
    <AlertDialog open={open} onOpenChange={(next) => { if (!next) close(false); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{req?.title}</AlertDialogTitle>
          {req?.description ? (
            <AlertDialogDescription>{req.description}</AlertDialogDescription>
          ) : (
            <AlertDialogDescription className="sr-only">{req?.title}</AlertDialogDescription>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter className={cn(req?.notice && "grid-cols-1")}>
          {!req?.notice && <AlertDialogCancel variant="outline" onClick={() => close(false)}>Cancel</AlertDialogCancel>}
          <AlertDialogAction variant={req?.destructive ? "destructive" : "default"} onClick={() => close(true)}>
            {req?.confirmLabel ?? (req?.notice ? "OK" : "Confirm")}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
