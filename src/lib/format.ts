export function formatPublishedAt(iso: string): string {
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
      timeZoneName: "short",
    });
  } catch {
    return iso;
  }
}

export function formatRelativeUpdated(iso?: string): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const now = Date.now();
    const diffMs = Math.max(0, now - d.getTime());
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    if (hours < 1) return "Updated just now";
    if (hours < 24) return `Updated ${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `Updated ${days}d ago`;
  } catch {
    return "";
  }
}
