import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import type { Group } from 'three'
import { COLORS } from '../../lib/colors'

/** Procedural low-poly quadcopter — no external asset, zero network dependency,
 * zero licensing risk. Flat-shaded primitives, clean geometric silhouette rather
 * than a cluttered "realistic" model — reads clearly at a glance, which matters
 * more than fidelity for a live demo judges are watching from a few feet away. */
export function ScoutDrone({ statusColor }: { statusColor: string }) {
  const rotorsRef = useRef<Group>(null)

  useFrame((_, delta) => {
    if (rotorsRef.current) {
      rotorsRef.current.children.forEach((rotor, i) => {
        rotor.rotation.y += delta * (14 + i * 0.3)
      })
    }
  })

  const armOffsets: [number, number][] = [
    [0.55, 0.55],
    [-0.55, 0.55],
    [0.55, -0.55],
    [-0.55, -0.55],
  ]

  return (
    <group>
      {/* Body */}
      <mesh castShadow position={[0, 0, 0]}>
        <boxGeometry args={[0.5, 0.18, 0.5]} />
        <meshStandardMaterial color={COLORS.paper} flatShading />
      </mesh>
      <mesh position={[0, 0.03, 0]}>
        <boxGeometry args={[0.2, 0.1, 0.2]} />
        <meshStandardMaterial color={statusColor} emissive={statusColor} emissiveIntensity={0.6} flatShading />
      </mesh>

      {/* Arms + rotors */}
      {armOffsets.map(([x, z], i) => (
        <group key={i}>
          <mesh position={[x * 0.5, 0, z * 0.5]} rotation={[0, Math.atan2(x, z), 0]} castShadow>
            <boxGeometry args={[0.08, 0.08, Math.hypot(x, z)]} />
            <meshStandardMaterial color={COLORS.panel} flatShading />
          </mesh>
        </group>
      ))}

      <group ref={rotorsRef}>
        {armOffsets.map(([x, z], i) => (
          <mesh key={i} position={[x, 0.08, z]} castShadow>
            <cylinderGeometry args={[0.32, 0.32, 0.03, 8]} />
            <meshStandardMaterial color={COLORS.ink} flatShading transparent opacity={0.75} />
          </mesh>
        ))}
      </group>
    </group>
  )
}
