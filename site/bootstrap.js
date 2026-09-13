import * as THREE from 'three';

// FlyCity's fly model faces local -Z. app.js computes a correct target yaw,
// but ordinary linear interpolation can rotate the long way around when the
// angle crosses -PI/PI (for example 0 -> 2PI). During that long turn a fly
// can look like it is flying backwards. Use shortest-arc interpolation for
// the one MathUtils.lerp call used by fly heading, then load the city.
THREE.MathUtils.lerp = (start, end, alpha) => {
  const delta = Math.atan2(Math.sin(end - start), Math.cos(end - start));
  return start + delta * alpha;
};

import('./app.js?v=frontfix-20260913-2');
