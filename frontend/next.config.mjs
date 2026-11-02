/** @type {import('next').NextConfig} */
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "X-Frame-Options", value: "DENY" },
  // The camera is needed by this origin only; microphone and location are never used.
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=()" },
];

const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["three"],
  output: "standalone",
  agentRules: false,
  async headers() {
    // Large static files that never change between runs are cached for a day (default is max-age=0, a revalidation on every load).
    const longCache = [{ key: "Cache-Control", value: "public, max-age=86400, stale-while-revalidate=604800" }];
    return [
      { source: "/:path*", headers: securityHeaders },
      { source: "/mediapipe/:path*", headers: longCache },
      { source: "/avatar/:path*", headers: longCache },
    ];
  },
};

export default nextConfig;
