export const GOOGLE_FAILED: string;
export const CODE_FAILED: string;
export const LINK_EXPIRED: string;
export const CALLBACK_FAILED: string;

export function errorCode(e: unknown): string;
export function emailSendMessage(e: unknown): string;
export function callbackError(
  search: string,
  hash: string,
): { code: string; message: string | null; cancelled: boolean } | null;
