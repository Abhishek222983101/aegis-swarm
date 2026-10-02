import { create } from 'zustand'
import type { DecisionRecord, EscalationState, MissionPlan, WorldState } from './types'

const MAX_DECISIONS = 40

interface AegisStore {
  worldState: WorldState | null
  connectionStatus: 'connecting' | 'open' | 'closed'
  decisions: DecisionRecord[]
  escalations: Record<string, EscalationState>
  missionPlan: MissionPlan | null
  selectedAgentId: string | null
  replayMode: boolean

  setWorldState: (s: WorldState) => void
  setConnectionStatus: (s: AegisStore['connectionStatus']) => void
  pushDecision: (d: DecisionRecord) => void
  resolveEscalation: (id: string, decision: string) => void
  setMissionPlan: (p: MissionPlan) => void
  selectAgent: (id: string | null) => void
  setReplayMode: (on: boolean) => void
}

export const useAegisStore = create<AegisStore>((set) => ({
  worldState: null,
  connectionStatus: 'connecting',
  decisions: [],
  escalations: {},
  missionPlan: null,
  selectedAgentId: null,
  replayMode: false,

  setWorldState: (s) => set({ worldState: s }),
  setConnectionStatus: (status) => set({ connectionStatus: status }),
  pushDecision: (d) =>
    set((state) => {
      const next = [d, ...state.decisions].slice(0, MAX_DECISIONS)
      const escalations = { ...state.escalations }
      if (d.decision === 'escalate' && d.escalation_id) {
        escalations[d.escalation_id] = {
          id: d.escalation_id,
          reasoning: d.reasoning_text,
          resolved: false,
          operator_decision: null,
        }
      }
      return { decisions: next, escalations }
    }),
  resolveEscalation: (id, decision) =>
    set((state) => ({
      escalations: {
        ...state.escalations,
        [id]: { ...(state.escalations[id] ?? { id, reasoning: '' }), resolved: true, operator_decision: decision },
      },
    })),
  setMissionPlan: (p) => set({ missionPlan: p }),
  selectAgent: (id) => set({ selectedAgentId: id }),
  setReplayMode: (on) => set({ replayMode: on }),
}))
