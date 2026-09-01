const SESSION_KEY =
  "dynamic-commerce-session-id";

let cachedSessionId:
  | string
  | null = null;


export function getSessionIdSnapshot():
string {
  if (
    typeof window ===
    "undefined"
  ) {
    return "";
  }

  if (cachedSessionId) {
    return cachedSessionId;
  }

  const existing =
    window.localStorage.getItem(
      SESSION_KEY
    );

  if (existing) {
    cachedSessionId =
      existing;

    return existing;
  }

  const sessionId =
    crypto.randomUUID();

  window.localStorage.setItem(
    SESSION_KEY,
    sessionId
  );

  cachedSessionId =
    sessionId;

  return sessionId;
}


export function getServerSessionSnapshot():
string {
  return "";
}


export function subscribeToSession():
() => void {
  return () => {};
}