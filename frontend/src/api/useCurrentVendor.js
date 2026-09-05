import { useEffect, useState } from "react";
import { get } from "./apiService";

// Small shared hook so any page/layout can know who is logged in and
// their role, without re-fetching it in more than one place.
export function useCurrentVendor() {
  const [vendor, setVendor] = useState(null);

  useEffect(() => {
    get("/vendor/me").then(setVendor).catch(() => setVendor(null));
  }, []);

  return vendor;
}
