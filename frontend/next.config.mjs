/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use standalone output inside Docker / Linux containers
  output: process.env.DOCKER_BUILD === "1" ? "standalone" : undefined,
  images: {
    domains: ["localhost"],
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
