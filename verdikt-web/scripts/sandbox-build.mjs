// Sandbox-only build: bundles the app with esbuild when Vite cannot be installed.
// Usage: node scripts/sandbox-build.mjs <node_modules dir with react/react-dom/esbuild> <outdir>
// The real build is `npm run build` (Vite). This script is not part of the shipped workflow.
import { createRequire } from 'node:module';
import { mkdirSync, readFileSync, writeFileSync, cpSync } from 'node:fs';
import { join, resolve } from 'node:path';

const [, , modulesDir, outDir = '.tmp-build'] = process.argv;
if (!modulesDir) throw new Error('Pass the node_modules directory that contains react, react-dom and esbuild');
const require = createRequire(join(resolve(modulesDir), 'noop.js'));
const esbuild = require('esbuild');
const root = resolve(new URL('..', import.meta.url).pathname);

mkdirSync(join(root, outDir, 'assets'), { recursive: true });
const result = await esbuild.build({
  entryPoints: [join(root, 'src/main.tsx')],
  bundle: true,
  outdir: join(root, outDir, 'assets'),
  entryNames: 'app',
  format: 'esm',
  jsx: 'automatic',
  target: 'es2022',
  sourcemap: true,
  nodePaths: [resolve(modulesDir)],
  define: { 'process.env.NODE_ENV': '"development"' },
  logLevel: 'warning',
  metafile: true,
});
const html = readFileSync(join(root, 'index.html'), 'utf8')
  .replace('<script type="module" src="/src/main.tsx"></script>', '<link rel="stylesheet" href="/assets/app.css" />\n    <script type="module" src="/assets/app.js"></script>');
writeFileSync(join(root, outDir, 'index.html'), html);
cpSync(join(root, 'public'), join(root, outDir), { recursive: true });
console.log('built', Object.keys(result.metafile.outputs).map((p) => p.replace(root + '/', '')).join(', '));
