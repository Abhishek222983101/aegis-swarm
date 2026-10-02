import { COLORS } from '../../lib/colors'

/** Ground-bound rover — boxy chassis on six wheels plus a sensor mast. Sits
 * at z=0 always (see entities.py AGENT_SPECS), which is the reference point
 * everything else's altitude reads against. */
export function HeavyRover({ statusColor }: { statusColor: string }) {
  const wheelPositions: [number, number][] = [
    [0.45, 0.35],
    [0.45, -0.35],
    [0, 0.35],
    [0, -0.35],
    [-0.45, 0.35],
    [-0.45, -0.35],
  ]

  return (
    <group>
      {/* Chassis */}
      <mesh castShadow position={[0, 0.22, 0]}>
        <boxGeometry args={[1.1, 0.3, 0.6]} />
        <meshStandardMaterial color={COLORS.paper} flatShading />
      </mesh>
      <mesh position={[0, 0.26, 0]}>
        <boxGeometry args={[0.3, 0.08, 0.25]} />
        <meshStandardMaterial color={statusColor} emissive={statusColor} emissiveIntensity={0.6} flatShading />
      </mesh>

      {/* Sensor mast */}
      <mesh position={[-0.35, 0.5, 0]} castShadow>
        <cylinderGeometry args={[0.03, 0.03, 0.35, 6]} />
        <meshStandardMaterial color={COLORS.panel} flatShading />
      </mesh>
      <mesh position={[-0.35, 0.68, 0]} castShadow>
        <boxGeometry args={[0.14, 0.08, 0.08]} />
        <meshStandardMaterial color={COLORS.ink} flatShading />
      </mesh>

      {/* Wheels */}
      {wheelPositions.map(([x, z], i) => (
        <mesh key={i} position={[x, 0.12, z]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <cylinderGeometry args={[0.12, 0.12, 0.12, 10]} />
          <meshStandardMaterial color={COLORS.ink} flatShading />
        </mesh>
      ))}
    </group>
  )
}
