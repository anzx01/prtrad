import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async redirects() {
    return [
      { source: "/markets", destination: "/", permanent: false },
      { source: "/launch-review", destination: "/", permanent: false },
      { source: "/review", destination: "/", permanent: false },
      { source: "/review/:path*", destination: "/", permanent: false },
      { source: "/dq", destination: "/", permanent: false },
      { source: "/tagging", destination: "/", permanent: false },
      { source: "/monitoring", destination: "/", permanent: false },
      { source: "/tag-quality", destination: "/", permanent: false },
      { source: "/lists", destination: "/", permanent: false },
      { source: "/calibration", destination: "/", permanent: false },
      { source: "/netev", destination: "/", permanent: false },
      { source: "/risk", destination: "/", permanent: false },
      { source: "/backtests", destination: "/", permanent: false },
      { source: "/reports", destination: "/", permanent: false },
      { source: "/state-alerts", destination: "/", permanent: false },
    ]
  },
}

export default nextConfig
