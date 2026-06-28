import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    // canon/verify tests are pure JS — no DOM needed.
    environment: "node",
  },
});
