# Bug-fixing instruction

Read the repository specification from `docs/SPEC.md` first. If a bug is already described in the spec, treat that document as the authoritative decomposition of the failing case and use it to anchor your investigation, tests, and final explanation.

When working on a mismatch, make the evidence trail explicit:

- identify the reproducing input or failing test.
- show the parsing or normalization branch that turns the raw field into the wrong normalized value.
- confirm the affected path with the smallest runnable proof.
- keep the explanation tied to the data flow rather than to a guessed file or module.

Do not invent a new fix shape when the project already records the intended scope, verification sequence, and ruled-out causes in the spec. Prefer the spec’s definitions of the root cause, the expected behavior, and the regression guard over ad-hoc diagnosis.
