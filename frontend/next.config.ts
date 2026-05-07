import type { NextConfig } from "next";

const BACKEND_ORIGIN = process.env.VOICE_LAB_BACKEND_ORIGIN ?? "http://127.0.0.1:8100";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_ORIGIN}/api/:path*`,
      },
      {
        source: "/media/:path*",
        destination: `${BACKEND_ORIGIN}/media/:path*`,
      },
    ];
  },
};

export default nextConfig;
