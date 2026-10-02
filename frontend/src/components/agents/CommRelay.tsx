import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import type { Mesh } from 'three'
import { COLORS } from '../../lib/colors'

/** Comm relay — a mast with a rotating signal ring, fixed at a mid-altitude
 * cruise height. The pulsing ring is the one piece of non-user-triggered
 * motion in the scene, used deliberately (per the frontend-design guidance:
 * motion should draw attention or respond to state, not decorate) — it signals
 * "this is actively relaying" at a glance, which matters during the comm-loss
 * demo scenario where this agent's job is to visibly go do something. */
export function CommRelay({ statusColor }: { statusColor: string }) {
  const ringRef = useRef<Mesh>(null)

  useFrame((_, delta) => {
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 1.2
      const s = 1 + Math.sin(performance.now() / 400) * 0.08
      ringRef.current.scale.set(s, s, 1)
    }
  })

  return (
    <group>
      {/* Mast */}
      <mesh castShadow position={[0, 0, 0]}>
        <cylinderGeometry args={[0.05, 0.08, 0.9, 8]} />
        <meshStandardMaterial color={COLORS.panel} flatShading />
      </mesh>
      {/* Head */}
      <mesh castShadow position={[0, 0.5, 0]}>
        <boxGeometry args={[0.22, 0.14, 0.22]} />
        <meshStandardMaterial color={COLORS.paper} flatShading />
      </mesh>
      <mesh position={[0, 0.5, 0]}>
        <sphereGeometry args={[0.06, 8, 8]} />
        <meshStandardMaterial color={statusColor} emissive={statusColor} emissiveIntensity={0.8} flatShading />
      </mesh>
      {/* Signal ring */}
      <mesh ref={ringRef} position={[0, 0.5, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.25, 0.3, 16]} />
        <meshBasicMaterial color={COLORS.amber} transparent opacity={0.55} />
      </mesh>
    </group>
  )
}
