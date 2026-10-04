import { useEffect, useState } from "react";

// Minimal hash router: "#/analyses/abc" -> "/analyses/abc"
function current(): string {
  const h = window.location.hash.replace(/^#/, "");
  return h || "/analyze";
}

export function useRoute(): string {
  const [route, setRoute] = useState(current());
  useEffect(() => {
    const on = () => setRoute(current());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function navigate(path: string) {
  window.location.hash = path;
}

export const isFixtureMode = () => new URLSearchParams(window.location.search).get("fixture") === "1";
