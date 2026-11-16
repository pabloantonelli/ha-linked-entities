# Contributing

## Development setup

```bash
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest -q
```

## How it works (short version)

- Each link is a config entry; options hold `members`, `triggers`, `primary`, `debounce_ms`, `step_delay_ms`, `reverse_off` and `event_types`. Propagation commands members in list order, one `async_call_later` step at a time when `step_delay_ms > 0`; any new propagation cancels the queue.
- `coordinator.py` (`LinkGroup`) listens to state changes and propagates on/off to the other members.
- Loop prevention: contexts created by the integration are remembered and ignored; members already in the target state are never commanded; reports that contradict a command within a short echo window are re-checked before propagating.
- `unavailable` / `unknown` are never propagated; members re-sync when they come back.

## Releasing

1. Bump `version` in `custom_components/linked_entities/manifest.json`.
2. Push to `main` and wait for the Validate and Tests workflows to pass.
3. Create a GitHub release (`vX.Y.Z`).
