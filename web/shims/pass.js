// Minimal stand-in for three/examples/jsm/postprocessing/Pass.js.
// spark.module.min.js statically imports { FullScreenQuad } from this path;
// that file isn't vendored, so this shim provides a compatible implementation
// (a fullscreen triangle rendered with an orthographic camera).
import { Mesh, BufferGeometry, Float32BufferAttribute, OrthographicCamera } from "three";

class FullscreenTriangleGeometry extends BufferGeometry {
  constructor() {
    super();
    this.setAttribute("position", new Float32BufferAttribute([-1, 3, 0, -1, -1, 0, 3, -1, 0], 3));
    this.setAttribute("uv", new Float32BufferAttribute([0, 2, 0, 0, 2, 0], 2));
  }
}

const _geometry = new FullscreenTriangleGeometry();
const _camera = new OrthographicCamera(-1, 1, 1, -1, 0, 1);

export class FullScreenQuad {
  constructor(material) {
    this._mesh = new Mesh(_geometry, material);
  }
  dispose() {
    this._mesh.geometry.dispose();
  }
  render(renderer) {
    renderer.render(this._mesh, _camera);
  }
  get material() {
    return this._mesh.material;
  }
  set material(value) {
    this._mesh.material = value;
  }
}
