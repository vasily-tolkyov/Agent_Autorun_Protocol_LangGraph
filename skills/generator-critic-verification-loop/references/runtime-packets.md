# Runtime Packets

Use these packet schemas once the loop enters `t3` runtime mode.

The main agent dispatches only one role packet at a time. Each packet is machine-first and should stay compact. Add a short natural-language summary only when it clarifies intent without duplicating the structured fields.

## Generator packet

```text
generator_packet:
- goal
- constraints
- acceptance_checks
- execution_plan_ref
- project_files
- relevant_logs
- round
- reply_contract = generator_run
```

Rules:

- Do not dispatch this packet without `execution_plan_ref`.
- Send only the project files the generator needs for the current execution slice.
- If the generator needs more context, it should request missing files or constraints instead of guessing.

## Critic packet

```text
critic_packet:
- goal
- constraints
- acceptance_checks
- candidate_ref
- changed_files
- project_files
- verification_commands_or_evidence
- round
- reply_contract = critic_audit
```

Rules:

- Send the critic only the current candidate, affected files, and the evidence needed to audit the work.
- The critic may emit findings and evidence references, but it must not generate fixes or alternative implementation plans.

## Refiner packet

```text
refiner_packet:
- goal
- constraints
- acceptance_checks
- candidate_ref
- reviewed_findings_ref
- project_files
- repeated_issue_history
- round
- reply_contract = refiner_plan
```

Rules:

- Send the refiner reviewed findings, not raw critic output, unless the raw output is attached only as evidence.
- The refiner must produce a complete plan with target files, edit actions, verification steps, blockers, and failure diagnosis.
- If the plan is incomplete, keep the loop in `validate_refiner` and send the next packet back to the refiner rather than the generator.
