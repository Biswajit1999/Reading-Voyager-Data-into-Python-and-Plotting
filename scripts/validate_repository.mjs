import fs from 'node:fs';
const required = ['README.md', 'data/research-reference.json'];

let failures = [];
for (const file of required) if (!fs.existsSync(file)) failures.push(file + ' missing');
const ref = JSON.parse(fs.readFileSync('data/research-reference.json', 'utf8'));
if (!Array.isArray(ref.anchors) || ref.anchors.length < 3) failures.push('reference anchors missing');
if (!Array.isArray(ref.equations) || ref.equations.length === 0) failures.push('equations missing');
if (!Array.isArray(ref.references) || ref.references.length === 0) failures.push('references missing');
for (const anchor of ref.anchors || []) {
  if (!Number.isFinite(anchor.x) || !Number.isFinite(anchor.y) || !anchor.label) failures.push('invalid anchor');
}
const sourceFiles = fs.readdirSync('.').filter(name => /\.(html|css|js|py|ipynb|md)$/i.test(name));
const combined = sourceFiles.map(name => fs.readFileSync(name, 'utf8')).join('\n');
const banned = ['TO' + 'DO', 'PLACE' + 'HOLDER', 'insert ' + 'logic', 'coming ' + 'soon'];
for (const token of banned) if (combined.toLowerCase().includes(token.toLowerCase())) failures.push('unfinished token ' + token);
if (failures.length) {
  console.error(failures.join('\n'));
  process.exit(1);
}
console.log('Reading-Voyager-Data-into-Python-and-Plotting: research validation passed with ' + ref.anchors.length + ' anchors.');
