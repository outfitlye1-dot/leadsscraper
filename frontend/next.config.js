/** @type {import('next').NextConfig} */
const backendUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8001";

const nextConfig = {
  // Strict mode double-mounts in dev and can feel like a refresh.
  reactStrictMode: false,
  async rewrites() {
    return [
      {
        source: "/health",
        destination: `${backendUrl}/health`,
      },
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
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
