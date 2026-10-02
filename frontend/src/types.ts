export type AgentType = 'scout_drone' | 'heavy_rover' | 'comm_relay'
export type AgentStatus = 'nominal' | 'degraded' | 'lost'

export interface AgentState {
  id: string
  type: AgentType
  position: [number, number, number]
  battery: number
  status: AgentStatus
  current_task: string | null
  comm_lost: boolean
  comm_range: number
}

export interface BlockedZone {
  id: string
  center: [number, number]
  radius: number
}

export interface WorldState {
  tick: number
  weather: 'clear' | 'degraded' | 'severe'
  agents: AgentState[]
  blocked_zones: BlockedZone[]
  comm_graph: Record<string, string[]>
}

export interface DecisionRecord {
  trigger_event: string
  agent_id: string | null
  decision: 'reassign' | 'reposition' | 'escalate' | 'terminate' | 'acknowledge'
  reasoning_text: string
  confidence_score: number | null
  escalated: boolean
  timestamp: number
}

export interface EscalationState {
  id: string
  reasoning: string
  resolved: boolean
  operator_decision: string | null
}

export interface MissionTask {
  id: string
  description: string
  required_type: AgentType | null
  priority: number
  depends_on: string[]
}

export interface MissionPlan {
  objective: string
  source: 'llm' | 'template'
  tasks: MissionTask[]
}

export type ServerMessage =
  | { type: 'state'; data: WorldState }
  | { type: 'decision'; data: DecisionRecord }
  | { type: 'escalation_resolved'; data: { id: string; operator_decision: string } }
  | { type: 'mission_plan'; data: MissionPlan }
  | { type: 'event'; data: Record<string, unknown> }
