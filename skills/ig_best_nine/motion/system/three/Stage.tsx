// The camera's space a film is shot in: one WebGL canvas the size of the frame, a camera set for each frame from a
// pose, the frame held until every texture and font is in, drawn again after every effect has run, and a finishing
// pass (bloom on what is brighter than white, then the travel pass).
import {useThree} from '@react-three/fiber';
import {Bloom, EffectComposer} from '@react-three/postprocessing';
import {ThreeCanvas} from '@remotion/three';
import {Suspense, useLayoutEffect, useMemo, type ReactNode} from 'react';
import {continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import * as THREE from 'three';
import type {Vec3} from './motion';
import {TravelEffect, type Travel} from './travel';

/** Where the camera stands, what it looks at, its roll in radians, and its vertical field of view in degrees. */
export type Pose = {position: Vec3; target: Vec3; roll: number; fov: number};

/** Sets the camera for this frame before the frame is drawn. */
const Rig: React.FC<{pose: Pose; near: number; far: number}> = ({pose, near, far}) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const gl = useThree((s) => s.gl);
  useLayoutEffect(() => {
    gl.localClippingEnabled = true;
    const [px, py, pz] = pose.position;
    const [tx, ty, tz] = pose.target;
    const fwd = new THREE.Vector3(tx - px, ty - py, tz - pz).normalize();
    const up = new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -pose.roll);
    camera.position.set(px, py, pz);
    camera.up.copy(up);
    camera.lookAt(tx, ty, tz);
    camera.fov = pose.fov;
    camera.near = near;
    camera.far = far;
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
  }, [camera, gl, pose, near, far]);
  return null;
};

/** Holds the frame while anything in the scene is still loading. */
const Hold: React.FC = () => {
  useLayoutEffect(() => {
    const handle = delayRender('stage: loading');
    return () => continueRender(handle);
  }, []);
  return null;
};

/**
 * Draws the frame after every effect in the scene has run, and again on the next animation frames before the capture,
 * so a texture that arrived late or a render target the composer made on its first pass is on the captured frame.
 */
const Settle: React.FC = () => {
  const frame = useCurrentFrame();
  const advance = useThree((s) => s.advance);
  const size = useThree((s) => s.size);
  const gl = useThree((s) => s.gl);
  useLayoutEffect(() => {
    const handle = delayRender('stage: settle');
    let id = 0;
    let passes = 0;
    let done = false;
    // the frame is captured only once the renderer has drawn the scene at least twice since this frame mounted
    const drawnFrom = gl.info.render.frame;
    const finish = () => {
      if (!done) continueRender(handle);
      done = true;
    };
    const draw = () => {
      advance(performance.now());
      passes += 1;
      const drawn = gl.info.render.frame - drawnFrom;
      if (passes < 3 || ((size.width === 0 || drawn < 2) && passes < 120)) id = requestAnimationFrame(draw);
      else finish();
    };
    draw();
    return () => {
      cancelAnimationFrame(id);
      finish();
    };
  }, [frame, advance, size, gl]);
  return null;
};

const Post: React.FC<{travel: Travel; bloom: number}> = ({travel, bloom}) => {
  const effect = useMemo(() => new TravelEffect(), []);
  effect.set(travel);
  return (
    <EffectComposer multisampling={4} frameBufferType={THREE.HalfFloatType}>
      <Bloom intensity={bloom} luminanceThreshold={1.0} luminanceSmoothing={0.15} mipmapBlur radius={0.7} />
      <primitive object={effect} />
    </EffectComposer>
  );
};

/**
 * The stage: `pose` for this frame, `travel` the finishing pass's values for it, `bloom` the glow on light brighter
 * than white, `background` the colour behind everything. Colours are drawn as given: no tone mapping.
 */
export const Stage: React.FC<{pose: Pose; travel: Travel; bloom?: number; background: string; near?: number; far?: number; children: ReactNode}> = ({
  pose, travel, bloom = 0.7, background, near = 5, far = 40000, children,
}) => {
  const {width, height} = useVideoConfig();
  return (
    <ThreeCanvas
      width={width}
      height={height}
      dpr={1}
      flat
      shadows
      gl={{antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance'}}
      camera={{fov: pose.fov, position: pose.position, near, far}}
      style={{position: 'absolute', inset: 0}}
    >
      <color attach="background" args={[background]} />
      <Suspense fallback={<Hold />}>
        <Rig pose={pose} near={near} far={far} />
        {children}
        <Post travel={travel} bloom={bloom} />
        <Settle />
      </Suspense>
    </ThreeCanvas>
  );
};
