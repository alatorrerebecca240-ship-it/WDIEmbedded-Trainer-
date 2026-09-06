// Build only: package the data-independent engine, never question banks or learner data.
const fs = require('fs');
const path = require('path');
const extension = path.resolve(__dirname, '..');
const root = path.resolve(extension, '..', '..');
const destination = path.join(extension, 'runtime');
fs.mkdirSync(path.join(destination, 'trainerlib'), { recursive: true });
fs.mkdirSync(path.join(extension, 'routes'), { recursive: true });
fs.copyFileSync(path.join(root, 'schemas', 'training-route.schema.json'), path.join(extension, 'routes', 'training-route.schema.json'));
fs.copyFileSync(path.join(root, 'trainer.py'), path.join(destination, 'trainer.py'));
for (const entry of fs.readdirSync(path.join(root, 'trainerlib'), { withFileTypes: true })) {
  if (entry.isFile() && entry.name.endsWith('.py')) {
    fs.copyFileSync(path.join(root, 'trainerlib', entry.name), path.join(destination, 'trainerlib', entry.name));
  }
}
console.log('Prepared bundled Python engine; no knowledge packs included.');
