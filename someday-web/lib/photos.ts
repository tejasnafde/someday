const STORAGE = `${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public`;

export function circlePhotoUrl(circleId: string): string {
  return `${STORAGE}/circle-photos/${circleId}`;
}
