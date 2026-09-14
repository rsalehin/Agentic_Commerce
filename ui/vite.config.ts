import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// strictPort: never fall back to another port (Windows rule).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
  },
});
