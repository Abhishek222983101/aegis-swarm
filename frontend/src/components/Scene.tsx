import { Canvas } from '@react-three/fiber'
import { Grid, Line, OrbitControls } from '@react-three/drei'
import { useAegisStore } from '../store'
import { AgentModel, toScene } from './agents/AgentModel'
import { COLORS, STATUS_COLOR } from '../lib/colors'

function CommLinks() {
  const worldState = useAegisStore((s) => s.worldState)
  if (!worldState) return null

  const agentById = Object.fromEntries(worldState.agents.map((a) => [a.id, a]))
  const seen = new Set<string>()
  const links: { from: string; to: string }[] = []

  for (const [from, tos] of Object.entries(worldState.comm_graph)) {
    for (const to of tos) {
      const key = [from, to].sort().join('|')
      if (seen.has(key)) continue
      seen.add(key)
      links.push({ from, to })
    }
  }

  return (
    <>
      {links.map(({ from, to }) => {
        const a = agentById[from]
        const b = agentById[to]
        if (!a || !b) return null
        return (
          <Line
            key={`${from}-${to}`}
            points={[toScene(...a.position), toScene(...b.position)]}
            color={COLORS.amber}
            lineWidth={1.2}
            transparent
            opacity={0.45}
            dashed
            dashSize={0.15}
            gapSize={0.1}
          />
        )
      })}
    </>
  )
}

function BlockedZones() {
  const worldState = useAegisStore((s) => s.worldState)
  if (!worldState) return null

  return (
    <>
      {worldState.blocked_zones.map((zone) => {
        const [x, , z] = toScene(zone.center[0], zone.center[1], 0)
        return (
          <mesh key={zone.id} position={[x, 0.02, z]} rotation={[-Math.PI / 2, 0, 0]}>
            <ringGeometry args={[zone.radius / 10 - 0.3, zone.radius / 10, 24]} />
            <meshBasicMaterial color={STATUS_COLOR.lost} transparent opacity={0.55} />
          </mesh>
        )
      })}
    </>
  )
}

function Agents() {
  const worldState = useAegisStore((s) => s.worldState)
  if (!worldState) return null
  return (
    <>
      {worldState.agents.map((agent) => (
        <AgentModel key={agent.id} agent={agent} />
      ))}
    </>
  )
}

export function Scene() {
  return (
    <Canvas shadows camera={{ position: [14, 11, 16], fov: 45 }}>
      <color attach="background" args={[COLORS.ink]} />
      <fog attach="fog" args={[COLORS.ink, 25, 60]} />

      <ambientLight intensity={0.55} />
      <directionalLight
        position={[12, 18, 8]}
        intensity={1.4}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />

      {/* Ground plane — the depth reference frame altitude is read against.
          Without this, floating agents have no legible height cue. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
        <planeGeometry args={[60, 60]} />
        <meshStandardMaterial color={COLORS.panel} />
      </mesh>
      <Grid
        args={[60, 60]}
        cellColor={COLORS.line}
        sectionColor={COLORS.amber}
        sectionThickness={0.6}
        cellThickness={0.3}
        fadeDistance={45}
        position={[0, 0.001, 0]}
      />

      <CommLinks />
      <BlockedZones />
      <Agents />

      {/* Deliberately NOT a locked top-down view — an angled perspective is
          required for altitude differences between agent types to read as
          "above," not just "offset." See BUILD-PLAN.md Phase 4.9. */}
      <OrbitControls
        minDistance={6}
        maxDistance={40}
        maxPolarAngle={Math.PI / 2.1}
        target={[0, 1, 0]}
      />
    </Canvas>
  )
}
