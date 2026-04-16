# Runtime Contract

Use this file when the loop promotes from `t0` discussion mode to `t3` runtime mode.

The natural-language workflow in `SKILL.md` remains useful for framing the task, but once real generator, critic, and refiner handoffs begin, this contract becomes the authoritative source for shared machine state.

## Machine contract

```text
Machine contract:
- runtime: aclx-runtime
- mode: t3
- authority:
  - only_main_thread_mutates(loop_state)
  - subagents_consume_packets_and_emit_artifacts_only
- terminals:
  - terminal_accept
  - terminal_fail
```

## Artifacts

### loop_state

```text
loop_state:
- task_id
- loop_id
- mode = t3
- phase
- current_round
- release_candidate_id
- current_execution_plan_id
- current_repair_plan_id
- issue_ledger_id
- clean_pass_streak
- fail_streak
- last_verdict
- next_dispatch_role
- checkpoint_id
```

### generator_run

```text
generator_run:
- round
- input_packet_id
- changed_files
- verification_evidence
- risks
- result_ref
```

### critic_audit

```text
critic_audit:
- round
- candidate_ref
- verdict
- findings
- evidence_refs
- audit_log_ref
```

### refiner_plan

```text
refiner_plan:
- round
- source_findings_ref
- failure_diagnosis
- target_files
- edit_actions
- verification_steps
- blockers
- plan_complete
```

### event_log

```text
event_log:
- append_only = true
- each_event_contains:
  - round
  - phase
  - actor
  - artifact_ref
  - timestamp
  - outcome
```

## Loop invariants

```text
Loop invariants:
- only_main_thread_mutates(loop_state)
- generator_never_self_approves
- critic_never_generates_fix
- refiner_never_executes_fix
- generator_never_runs_without(current_execution_plan_id)
- refiner_plan.plan_complete != true => next_dispatch_role != generator
- raw_critic_output_never_flows_directly_to_generator
- refiner_receives_reviewed_findings_only
```

If the main agent needs to attach unreviewed critic output for evidence, mark it as an evidence attachment rather than as the reviewed findings source.

## Transition rules

Use only these core phase values:

```text
phase:
- dispatch_generator
- await_generator
- dispatch_critic
- await_critic
- review_critic
- dispatch_refiner
- await_refiner
- validate_refiner
- terminal_accept
- terminal_fail
```

Do not rename these phases. New helper markers may exist as secondary fields, but they must not replace the core phase field.

Core transitions:

```text
Transition rules:
- dispatch_generator -> await_generator
- await_generator + generator_run -> dispatch_critic
- dispatch_critic -> await_critic
- await_critic + critic_audit -> review_critic
- review_critic + verdict=PASS -> dispatch_generator
- review_critic + verdict=FAIL -> dispatch_refiner
- dispatch_refiner -> await_refiner
- await_refiner + refiner_plan -> validate_refiner
- validate_refiner + plan_complete=true -> dispatch_generator
- validate_refiner + plan_complete=false -> dispatch_refiner
- clean_pass_streak == 5 -> terminal_accept
- fail_streak == 10 -> terminal_fail
```

Counter rules:

```text
- verdict=PASS => clean_pass_streak += 1; fail_streak = 0
- verdict=FAIL => fail_streak += 1; clean_pass_streak = 0
```

Repeated-issue escalation:

```text
- same_blocking_issue_survives_two_failed_rounds => mark(strategy_change_required)
```

## Acceptance checks

```text
Acceptance checks:
- five_consecutive_passes_required_for_accept
- ten_consecutive_failures_required_for_fail
- refiner_plan_requires:
  - failure_diagnosis
  - target_files
  - edit_actions
  - verification_steps
  - blockers
- missing_any_required_refiner_field => plan_complete = false
- plan_complete = false => phase = validate_refiner and no_generator_dispatch
```

## Checkpoint, resume, replay

```text
Checkpoint rules:
- write_checkpoint_after_every_phase_transition
- checkpoint_minimum_payload:
  - loop_state
  - latest_event
  - latest_artifact_refs
```

```text
Resume rules:
- restore_from(phase, current_round)
- never_guess_round_from_conversation_history
- if phase is await_generator or await_critic or await_refiner:
  - read latest successful dispatch packet
  - read latest full checkpoint
  - then decide whether to re-dispatch
```

```text
Replay rules:
- event_log_is_authoritative
- do_not_rebuild_machine_state_from_free_text_dialogue
- after_resume:
  - reconcile(latest_artifacts, loop_state)
  - if mismatch:
    - move_to(review_critic) or move_to(validate_refiner)
    - do_not_dispatch_generator_until_reconciled
```
