/**
 * Public deployment switches, read at build time (NEXT_PUBLIC_* values are baked into the bundle).
 *   NEXT_PUBLIC_DISABLE_RECORDING=1   hide the Record sign tab (the backend refuses recording separately with SIGNBRIDGE_RECORDING_ENABLED=false)
 */
export const isOn = (v: string | undefined): boolean => ["1", "true", "yes", "on"].includes((v ?? "").trim().toLowerCase());

export const RECORDING_DISABLED = isOn(process.env.NEXT_PUBLIC_DISABLE_RECORDING);
