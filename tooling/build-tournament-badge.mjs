// Local authored-asset compiler. Produces a textured, beveled relief GLB;
// does not modify the supplied art or publish anything to the CDN.
import { readFile, writeFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';
const [source, output, threeRoot, pngModule] = process.argv.slice(2);
if (!source || !output || !threeRoot || !pngModule) throw Error('Usage: node build-tournament-badge.mjs ART.png OUTPUT.glb THREE_DIRECTORY PNGJS_MODULE');
const THREE = await import(pathToFileURL(`${threeRoot}/build/three.module.js`).href);
const { GLTFExporter } = await import(pathToFileURL(`${threeRoot}/examples/jsm/exporters/GLTFExporter.js`).href);
const { PNG } = (await import(pathToFileURL(pngModule).href)).default;
const artwork = await readFile(source);
const png = PNG.sync.read(artwork);
const size = 6.4, height = size * png.height / png.width;
const left = [], right = [];
for (let y = 0; y < png.height; y += 5) {
  let min = png.width, max = -1;
  for (let x = 0; x < png.width; x++) if (png.data[(y * png.width + x) * 4 + 3] > 40) { min = Math.min(min, x); max = x; }
  if (max >= min) { const yy = (0.5 - y / png.height) * height; left.push([(min / png.width - 0.5) * size, yy]); right.push([(max / png.width - 0.5) * size, yy]); }
}
const points = [...left, ...right.reverse()];
const shape = new THREE.Shape(points.map(([x, y]) => new THREE.Vector2(x, y)));
const bodyGeometry = new THREE.ExtrudeGeometry(shape, { depth: 0.32, bevelEnabled: true, bevelThickness: 0.045, bevelSize: 0.028, bevelSegments: 3, steps: 1 });
bodyGeometry.translate(0, 0, -0.16);
const metal = new THREE.MeshStandardMaterial({ color: 0xc58c30, metalness: 0.9, roughness: 0.3 });
const faceMaterial = new THREE.MeshStandardMaterial({ color: 0xffffff, roughness: 0.36, metalness: 0.04, transparent: true, alphaTest: 0.04, side: THREE.DoubleSide });
faceMaterial.name = 'Tournament debut enamel';
const group = new THREE.Group(); group.name = 'Tournament debut achievement badge';
const body = new THREE.Mesh(bodyGeometry, metal); body.name = 'Solid bronze and gold shield'; group.add(body);
// A small actual relief displacement catches light on the enamel instead of
// representing the whole award as a flat image plane.
const faceGeometry = new THREE.PlaneGeometry(size, height, 128, 128);
const uv = faceGeometry.attributes.uv;
for (let i = 0; i < uv.count; i++) uv.setY(i, 1 - uv.getY(i));
const pos = faceGeometry.attributes.position;
for (let i = 0; i < pos.count; i++) {
  const x = Math.min(png.width - 1, Math.max(0, Math.round((pos.getX(i) / size + 0.5) * png.width)));
  const y = Math.min(png.height - 1, Math.max(0, Math.round((0.5 - pos.getY(i) / height) * png.height)));
  const offset = (y * png.width + x) * 4;
  const luminance = (png.data[offset] * 0.2126 + png.data[offset + 1] * 0.7152 + png.data[offset + 2] * 0.0722) / 255;
  pos.setZ(i, 0.205 + luminance * 0.055);
}
faceGeometry.computeVertexNormals();
const face = new THREE.Mesh(faceGeometry, faceMaterial); face.name = 'Textured raised enamel tournament emblem'; group.add(face);
class NodeFileReader { readAsArrayBuffer(blob) { blob.arrayBuffer().then(r => { this.result = r; this.onloadend?.(); }); } }
globalThis.FileReader = NodeFileReader;
const base = Buffer.from(await new GLTFExporter().parseAsync(group, { binary: true }));
const jsonLength = base.readUInt32LE(12), json = JSON.parse(base.subarray(20, 20 + jsonLength).toString().trimEnd());
const binHeader = 20 + jsonLength, binary = base.subarray(binHeader + 8, binHeader + 8 + base.readUInt32LE(binHeader));
const align = n => (n + 3) & ~3;
const imageOffset = align(json.buffers[0].byteLength), combined = Buffer.alloc(align(imageOffset + artwork.length));
binary.copy(combined); artwork.copy(combined, imageOffset);
json.bufferViews ??= []; const imageView = json.bufferViews.push({ buffer: 0, byteOffset: imageOffset, byteLength: artwork.length }) - 1;
json.images = [{ mimeType: 'image/png', bufferView: imageView }];
json.samplers = [{ magFilter: 9729, minFilter: 9987, wrapS: 33071, wrapT: 33071 }];
json.textures = [{ source: 0, sampler: 0 }];
json.materials.find(m => m.name === faceMaterial.name).pbrMetallicRoughness.baseColorTexture = { index: 0 };
json.buffers[0].byteLength = combined.length;
const raw = Buffer.from(JSON.stringify(json)), padded = Buffer.alloc(align(raw.length), 32); raw.copy(padded);
const result = Buffer.alloc(12 + 8 + padded.length + 8 + combined.length);
result.writeUInt32LE(0x46546c67, 0); result.writeUInt32LE(2, 4); result.writeUInt32LE(result.length, 8);
result.writeUInt32LE(padded.length, 12); result.writeUInt32LE(0x4e4f534a, 16); padded.copy(result, 20);
const b = 20 + padded.length; result.writeUInt32LE(combined.length, b); result.writeUInt32LE(0x004e4942, b + 4); combined.copy(result, b + 8);
await writeFile(output, result);
console.log(JSON.stringify({ output, bytes: result.length, meshes: json.meshes.length, embeddedImages: json.images.length }));
