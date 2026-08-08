/** @type {import('next').NextConfig} */
const rawBackend =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8001";

const backendUrl = String(rawBackend).replace(/\/$/, "");
const publicApi = (process.env.NEXT_PUBLIC_API_URL || "/api").trim();
const isVercel = process.env.VERCEL === "1";
const backendIsLocal = /127\.0\.0\.1|localhost/i.test(backendUrl);
// Browser → Railway directly (no Vercel proxy). Preferred when BACKEND_INTERNAL_URL missing.
const useDirectApi = publicApi.startsWith("http://") || publicApi.startsWith("https://");

if (isVercel && backendIsLocal && !useDirectApi) {
  console.warn(
    "[next.config] On Vercel, set BACKEND_INTERNAL_URL=https://YOUR-RAILWAY.up.railway.app " +
      "OR set NEXT_PUBLIC_API_URL=https://YOUR-RAILWAY.up.railway.app/api — " +
      "localhost proxy will crash serverless functions."
  );
}

const nextConfig = {
  reactStrictMode: false,
  async rewrites() {
    // Direct browser→Railway: no proxy rewrites needed (avoids FUNCTION_INVOCATION_FAILED)
    if (useDirectApi) {
      return [];
    }
    // Never proxy to localhost from Vercel — that always crashes
    if (isVercel && backendIsLocal) {
      return [];
    }
    return [
      { source: "/health", destination: `${backendUrl}/health` },
      { source: "/docs", destination: `${backendUrl}/docs` },
      { source: "/docs/:path*", destination: `${backendUrl}/docs/:path*` },
      { source: "/openapi.json", destination: `${backendUrl}/openapi.json` },
      { source: "/redoc", destination: `${backendUrl}/redoc` },
      { source: "/api/:path*", destination: `${backendUrl}/api/:path*` },
    ];
  },
  webpack: (config, { dev }) => {
    if (dev) {
      config.watchOptions = {
        poll: 1000,
        aggregateTimeout: 300,
        ignored: [
          "**/node_modules/**",
          "**/.git/**",
          "**/.next/**",
          "../**/*.db",
          "../exports/**",
          "../uploads/**",
          "../**/__pycache__/**",
          "../**/*.pyc",
        ],
      };
    }
    return config;
  },
};

module.exports = nextConfig;
