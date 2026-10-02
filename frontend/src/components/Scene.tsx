import { useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { Grid, Line, OrbitControls } from '@react-three/drei'
import { Vector3 } from 'three'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import { useAegisStore } from '../store'
import { AgentModel, toScene } from './agents/AgentModel'
import { COLORS, STATUS_COLOR } from '../lib/colors'

const DEFAULT_CAMERA_POS: [number, number, number] = [14, 11, 16]
const DEFAULT_TARGET: [number, number, number] = [0, 1, 0]
const TOP_DOWN_POS: [number, number, number] = [0.01, 32, 0.01]

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

/** Smoothly pans the whole camera rig (target + position together, preserving
 * the user's current zoom/angle) toward the followed agent each frame. Not a
 * hard snap — a snap would be disorienting every tick the agent moves. */
function FollowCamera({ controlsRef, followId }: { controlsRef: React.RefObject<OrbitControlsImpl | null>; followId: string | null }) {
  const worldState = useAegisStore((s) => s.worldState)
  const { camera } = useThree()

  useFrame(() => {
    if (!followId || !controlsRef.current || !worldState) return
    const agent = worldState.agents.find((a) => a.id === followId)
    if (!agent) return
    const [x, y, z] = toScene(...agent.position)
    const desired = new Vector3(x, y, z)
    const delta = desired.clone().sub(controlsRef.current.target).multiplyScalar(0.08)
    controlsRef.current.target.add(delta)
    camera.position.add(delta)
    controlsRef.current.update()
  })
  return null
}

function CameraToolbar({
  controlsRef,
  followId,
  setFollowId,
}: {
  controlsRef: React.RefObject<OrbitControlsImpl | null>
  followId: string | null
  setFollowId: (id: string | null) => void
}) {
  const selectedAgentId = useAegisStore((s) => s.selectedAgentId)

  function resetView() {
    setFollowId(null)
    const controls = controlsRef.current
    if (!controls) return
    controls.target.set(...DEFAULT_TARGET)
    controls.object.position.set(...DEFAULT_CAMERA_POS)
    controls.update()
  }

  function topDown() {
    setFollowId(null)
    const controls = controlsRef.current
    if (!controls) return
    controls.target.set(0, 0, 0)
    controls.object.position.set(...TOP_DOWN_POS)
    controls.update()
  }

  function toggleFollow() {
    if (followId) {
      setFollowId(null)
      return
    }
    if (selectedAgentId) setFollowId(selectedAgentId)
  }

  return (
    <div className="absolute left-2 top-2 z-10 flex gap-1.5">
      <button className="btn-brutal px-2 py-1 text-[10px]" onClick={resetView} title="Reset camera to the default angle">
        ⟲ RESET VIEW
      </button>
      <button className="btn-brutal px-2 py-1 text-[10px]" onClick={topDown} title="Switch to a top-down tactical view">
        ⬒ TOP-DOWN
      </button>
      <button
        className={followId ? 'btn-brutal-amber px-2 py-1 text-[10px]' : 'btn-brutal px-2 py-1 text-[10px]'}
        onClick={toggleFollow}
        disabled={!followId && !selectedAgentId}
        title={selectedAgentId ? `Follow ${selectedAgentId}` : 'Select an agent in SWARM STATUS first'}
      >
        {followId ? `● FOLLOWING ${followId}` : '◎ FOLLOW SELECTED'}
      </button>
    </div>
  )
}

export function Scene() {
  const controlsRef = useRef<OrbitControlsImpl | null>(null)
  const [followId, setFollowId] = useState<string | null>(null)

  return (
    <div className="relative h-full w-full">
      <CameraToolbar controlsRef={controlsRef} followId={followId} setFollowId={setFollowId} />
      <Canvas shadows camera={{ position: DEFAULT_CAMERA_POS, fov: 45 }}>
        <color attach="background" args={[COLORS.ink]} />
        <fog attach="fog" args={[COLORS.ink, 25, 70]} />

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
          fadeDistance={55}
          position={[0, 0.001, 0]}
        />

        <CommLinks />
        <BlockedZones />
        <Agents />
        <FollowCamera controlsRef={controlsRef} followId={followId} />

        {/* Deliberately NOT a locked top-down view by default — an angled
            perspective is required for altitude differences between agent
            types to read as "above," not just "offset." See BUILD-PLAN.md
            Phase 4.9. TOP-DOWN is available as an explicit toolbar choice. */}
        <OrbitControls
          ref={controlsRef}
          minDistance={4}
          maxDistance={55}
          maxPolarAngle={Math.PI / 2.05}
          target={DEFAULT_TARGET}
          enableDamping
          dampingFactor={0.12}
        />
      </Canvas>
    </div>
  )
}
