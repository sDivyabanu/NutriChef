import type { NextConfig } from "next";

// Local FastAPI NLP service. Proxied under /backend so calls are same-origin and carry the auth cookie.
const NLP_API_URL = process.env.NLP_API_URL || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${NLP_API_URL}/api/:path*` }];
  },
};

export default nextConfig;
