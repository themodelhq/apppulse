/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.mzstatic.com" },       // Apple app icons
      { protocol: "https", hostname: "play-lh.googleusercontent.com" }, // Play icons
    ],
  },
};

module.exports = nextConfig;
