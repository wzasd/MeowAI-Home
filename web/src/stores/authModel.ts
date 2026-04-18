function extractStatus(error: unknown): number | null {
  if (!error || typeof error !== "object" || !("status" in error)) {
    return null;
  }

  const status = (error as { status?: unknown }).status;
  return typeof status === "number" ? status : null;
}

export function shouldResetStoredSession(error: unknown): boolean {
  const status = extractStatus(error);
  return status === 401 || status === 403;
}

export function getAuthInitErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return "登录状态校验失败，请检查服务连接";
}
