import { existsSync, readFileSync, readdirSync } from "node:fs";
import { dirname, extname, join, resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];
const required = [
  "README.md",
  "assets/header.svg",
  "assets/globe.svg",
  "assets/crystal.svg",
  "assets/terminal.svg",
  "assets/divider.svg",
  "generated/stats.svg",
  "generated/languages.svg",
  "generated/activity.svg",
  "generated/repositories.svg",
  "data/repository-config.json",
  "data/repositories.json",
  "docs/index.html",
  "docs/favicon.svg",
  "docs/styles.css",
  "docs/app.js",
  ".github/workflows/pages.yml",
  ".github/workflows/validate.yml",
  ".github/workflows/update-metrics.yml"
];

for (const path of required) {
  if (!existsSync(join(root, path))) failures.push(`Missing required file: ${path}`);
}

const textFiles = walk(root).filter(path => [".md", ".html", ".css", ".js", ".mjs", ".py", ".json", ".svg", ".yml"].includes(extname(path)));
for (const file of textFiles) {
  const contents = readFileSync(file, "utf8");
  if (/C:\\Users\\|\/Users\/[^/]+\/(?:Desktop|Documents|Downloads|AppData)\/|AppData\/Local\/Temp/i.test(contents)) failures.push(`Local machine path leaked in ${file.slice(root.length + 1)}`);
  if (/ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}/.test(contents)) failures.push(`Possible GitHub token in ${file.slice(root.length + 1)}`);
}

const readme = readFileSync(join(root, "README.md"), "utf8");
const localReferences = [...readme.matchAll(/(?:src|href)=["']([^"'#]+)["']|!\[[^\]]*\]\(([^)#]+)(?:#[^)]+)?\)/g)]
  .map(match => match[1] || match[2])
  .filter(reference => reference && !/^(?:https?:|mailto:)/.test(reference));
for (const reference of localReferences) {
  if (!existsSync(join(root, reference))) failures.push(`Broken README reference: ${reference}`);
}

try {
  const config = JSON.parse(readFileSync(join(root, "data/repository-config.json"), "utf8"));
  const data = JSON.parse(readFileSync(join(root, "data/repositories.json"), "utf8"));
  if (!Array.isArray(config.ignoreRepositories) || !Array.isArray(config.featuredRepositories)) failures.push("Repository config lists must be arrays");
  if (!Array.isArray(data.repositories)) failures.push("Generated repository data must contain a repositories array");
  for (const repo of data.repositories || []) {
    for (const field of ["name", "url", "description", "updatedAt", "stars", "forks"]) {
      if (!(field in repo)) failures.push(`Generated repository entry ${repo.name || "<unknown>"} is missing ${field}`);
    }
  }
} catch (error) {
  failures.push(`Repository JSON validation failed: ${error.message}`);
}

try {
  execFileSync(process.execPath, ["--check", join(root, "docs/app.js")], { stdio: "pipe" });
} catch (error) {
  failures.push(`JavaScript syntax check failed: ${error.stderr?.toString() || error.message}`);
}

if (failures.length) {
  console.error(failures.map(item => `- ${item}`).join("\n"));
  process.exit(1);
}
console.log(`Validated ${textFiles.length} text assets and ${localReferences.length} local README references.`);

function walk(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    if (entry.name === ".git" || entry.name === "node_modules") return [];
    const path = join(directory, entry.name);
    return entry.isDirectory() ? walk(path) : [path];
  });
}
