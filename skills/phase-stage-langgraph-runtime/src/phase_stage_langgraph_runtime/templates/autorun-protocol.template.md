# Autorun Protocol

runId: {{run_id}}
title: {{title}}
generatedAt: {{generated_at}}
projectRoot: {{project_root}}
planningRoot: {{planning_root}}
runtimeRoot: {{runtime_root}}
planningStatePath: {{planning_state_path}}
approvalStatus: {{approval_status}}
planningMode: {{planning_mode}}
currentPhaseId: {{current_phase_id}}
currentExecutablePhaseId: {{current_executable_phase_id}}

## Control Plane

- authoritativePlanningState: `{{planning_state_path}}`
- authoritativeRuntime: `LangGraph thread state`
- compatibilityRuntimeRoot: `{{runtime_root}}`
- approvalStatus: `{{approval_status}}`
- currentPhaseId: `{{current_phase_id}}`
- currentExecutablePhaseId: `{{current_executable_phase_id}}`

## Current Executable Stage Queue

{{current_stage_queue_lines}}
