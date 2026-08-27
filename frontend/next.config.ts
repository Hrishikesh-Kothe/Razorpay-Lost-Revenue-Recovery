import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone is only for Docker images. Vercel needs the default Next output.
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
