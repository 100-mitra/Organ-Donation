import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // GitHub Pages serves the project site under /Organ-Donation/ — the deploy
  // workflow sets VITE_BASE so asset paths resolve there; local dev stays "/".
  base: process.env.VITE_BASE || "/",
  plugins: [react()],
  test: {
    // canon/verify tests are pure JS — no DOM needed.
    environment: "node",
  },
});
