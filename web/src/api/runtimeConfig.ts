type RuntimeEnvKey = "VITE_API_URL" | "VITE_WS_URL";

// Fallback only used when no env var AND no browser origin (e.g. SSR/tests)
// Port is configured via web/.env — VITE_API_URL / VITE_WS_URL
const LOCAL_API_FALLBACK = "http://localhost:5172";
const LOCAL_WS_FALLBACK = "ws://localhost:5172";

function readRuntimeEnv(key: RuntimeEnvKey): string | undefined {
  const env = (import.meta as ImportMeta & { env?: Record<string, string | undefined> }).env;
  return env?.[key];
}

function stripTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function normalizeBaseUrl(value?: string | null): string | null {
  const trimmed = value?.trim();
  return trimmed ? stripTrailingSlash(trimmed) : null;
}

function readBrowserOrigin(): string | null {
  return typeof window !== "undefined" ? window.location.origin : null;
}

function isHttpOrigin(origin: string | null): origin is string {
  return Boolean(origin && /^https?:\/\//.test(origin));
}

export function resolveApiBaseUrl(
  configuredBaseUrl = readRuntimeEnv("VITE_API_URL"),
  browserOrigin = readBrowserOrigin()
): string {
  return normalizeBaseUrl(configuredBaseUrl) ?? (isHttpOrigin(browserOrigin) ? stripTrailingSlash(browserOrigin) : LOCAL_API_FALLBACK);
}

export function resolveWsBaseUrl(
  configuredBaseUrl = readRuntimeEnv("VITE_WS_URL"),
  browserOrigin = readBrowserOrigin()
): string {
  const configured = normalizeBaseUrl(configuredBaseUrl);
  if (configured) {
    return configured;
  }

  if (isHttpOrigin(browserOrigin)) {
    const url = new URL(browserOrigin);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    return stripTrailingSlash(url.toString());
  }

  return LOCAL_WS_FALLBACK;
}

export function buildApiUrl(path: string, baseUrl = resolveApiBaseUrl()): string {
  return `${stripTrailingSlash(baseUrl)}${path.startsWith("/") ? path : `/${path}`}`;
}

export function buildWsUrl(path: string, baseUrl = resolveWsBaseUrl()): string {
  return `${stripTrailingSlash(baseUrl)}${path.startsWith("/") ? path : `/${path}`}`;
}
