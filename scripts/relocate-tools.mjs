import { mkdir, readdir, rename, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const sourceDir = path.join(root, "tools");
const targetDir = path.join(root, "data", "tools");

async function main() {
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
