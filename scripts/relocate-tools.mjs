import { mkdir, readdir, rename, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const publicDir = path.join(root, "dist", "public");
const sourceDir = path.join(publicDir, "tools");
const targetDir = path.join(publicDir, "data", "tools");

async function preserveBrowserScriptPaths() {
  const sourceAppDir = path.join(publicDir, "app");
  const targetJsDir = path.join(publicDir, "js");
  await rm(targetJsDir, { recursive: true, force: true });
  try {
    await rename(sourceAppDir, targetJsDir);
  } catch (error) {
    if (error?.code === "ENOENT") return;
    throw error;
  }
}

async function main() {
  await preserveBrowserScriptPaths();

  let entries = [];
  try {
    entries = await readdir(sourceDir, { withFileTypes: true });
  } catch {
    return;
  }

  await mkdir(targetDir, { recursive: true });
  await Promise.all(entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".js"))
    .map((entry) => rename(path.join(sourceDir, entry.name), path.join(targetDir, entry.name))));
  await rm(sourceDir, { recursive: true, force: true });
}

await main();
