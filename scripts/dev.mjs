import { spawn } from "node:child_process";

const python = process.platform === "win32" ? "python" : "python3";
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const windows = process.platform === "win32";
const children = [
  spawn(python, ["local_api.py"], { stdio: "inherit", shell: windows }),
  spawn(npm, ["run", "dev:web"], { stdio: "inherit", shell: windows }),
];

let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill();
  process.exit(code);
}

for (const child of children) {
  child.on("error", (error) => {
    console.error(error.message);
    stop(1);
  });
  child.on("exit", (code, signal) => {
    if (!stopping && code !== 0) {
      console.error(`Development service stopped (${signal ?? code}).`);
      stop(code ?? 1);
    }
  });
}

process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
