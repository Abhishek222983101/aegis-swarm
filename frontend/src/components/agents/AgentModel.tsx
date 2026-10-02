import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import { Billboard, Text } from '@react-three/drei'
import { Group, Vector3 } from 'three'
import type { AgentState } from '../../types'
import { STATUS_COLOR, COLORS } from '../../lib/colors'
import { ScoutDrone } from './ScoutDrone'
import { HeavyRover } from './HeavyRover'
import { CommRelay } from './CommRelay'
import { useAegisStore } from '../../store'

// World (backend) -> Scene (three.js, Y-up) axis mapping, used everywhere an
// agent/zone position is placed in 3D, so every component agrees on it.
export function toScene(x: number, y: number, z: number): [number, number, number] {
  return [x / 10 - 20, z / 5, y / 10 - 20]
}

export function AgentModel({ agent }: { agent: AgentState }) {
  const groupRef = useRef<Group>(null)
  const selectAgent = useAegisStore((s) => s.selectAgent)
  const selected = useAegisStore((s) => s.selectedAgentId === agent.id)
  const target = useRef(new Vector3(...toScene(...agent.position)))
  target.current.set(...toScene(...agent.position))

  useFrame((_, delta) => {
    if (!groupRef.current) return
    // Smooth toward the latest server position instead of teleporting on each
    // ~0.5s state push — ticks arrive slower than the render rate.
    groupRef.current.position.lerp(target.current, Math.min(1, delta * 4))
  })

  const statusColor = STATUS_COLOR[agent.status] ?? COLORS.paper
  const altitude = agent.position[2]
  const groundY = 0

  return (
    <group>
      <group
        ref={groupRef}
        onClick={(e) => {
          e.stopPropagation()
          selectAgent(agent.id)
        }}
      >
        {agent.type === 'scout_drone' && <ScoutDrone statusColor={statusColor} />}
        {agent.type === 'heavy_rover' && <HeavyRover statusColor={statusColor} />}
        {agent.type === 'comm_relay' && <CommRelay statusColor={statusColor} />}

        {selected && (
          <mesh position={[0, -0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[0.7, 0.8, 24]} />
            <meshBasicMaterial color={COLORS.amber} />
          </mesh>
        )}

        <Billboard position={[0, 1.0, 0]}>
          <Text fontSize={0.22} color={COLORS.paper} outlineWidth={0.015} outlineColor={COLORS.ink} anchorX="center">
            {agent.id}
          </Text>
          <Text
            fontSize={0.16}
            color={statusColor}
            outlineWidth={0.01}
            outlineColor={COLORS.ink}
            position={[0, -0.24, 0]}
            anchorX="center"
          >
            {Math.round(agent.battery)}%
          </Text>
        </Billboard>
      </group>

      {/* Ground-contact indicator — makes altitude legible without requiring the
          viewer to study camera angle; fades/shrinks with height per the 3D audit. */}
      {altitude > 0.5 && (
        <mesh
          position={[target.current.x, groundY + 0.01, target.current.z]}
          rotation={[-Math.PI / 2, 0, 0]}
        >
          <circleGeometry args={[0.35 / (1 + altitude / 20), 16]} />
          <meshBasicMaterial color={COLORS.ink} transparent opacity={0.35} />
        </mesh>
      )}
    </group>
  )
}
