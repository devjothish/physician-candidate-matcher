import type { NextConfig } from "next";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const rootDir = path.dirname(__filename);

const nextConfig: NextConfig = {
  turbopack: {
    root: rootDir,
    resolveAlias: {
      "@/*": [path.join(rootDir, "src/*")],
    },
  },
};

export default nextConfig;
