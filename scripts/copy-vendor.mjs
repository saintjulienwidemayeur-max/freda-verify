// Copies the large third-party binaries from node_modules into public/vendor so they are NOT committed to git.
// Runs automatically before `npm run build` / `npm run dev` (see package.json). Fails loudly if a source file is missing.
import { copyFileSync, mkdirSync, existsSync } from "node:fs";
import { dirname } from "node:path";

const files = [
  ["node_modules/@techstark/opencv-js/dist/opencv.js", "public/vendor/opencv.js"],
  ["node_modules/@mediapipe/tasks-vision/wasm/vision_wasm_internal.js", "public/vendor/mediapipe/wasm/vision_wasm_internal.js"],
  ["node_modules/@mediapipe/tasks-vision/wasm/vision_wasm_internal.wasm", "public/vendor/mediapipe/wasm/vision_wasm_internal.wasm"],
];
let failed = false;
for (const [from, to] of files) {
  if (!existsSync(from)) { console.error(`copy-vendor: missing ${from} (run npm install)`); failed = true; continue; }
  mkdirSync(dirname(to), { recursive: true });
  copyFileSync(from, to);
}
if (failed) process.exit(1);
console.log(`copy-vendor: ${files.length} files copied to public/vendor`);
