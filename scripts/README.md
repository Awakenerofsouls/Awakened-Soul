# scripts/

Repo automation. Two categories: **identity protection** and the
**adapter / collision toolchain** that brings every mechanism file in
`legacy/` and `brain/ root` under the five-layer `BrainMechanism`
contract that `brain_runner` walks.

---

## Identity protection

### `protect_identity.py`
Stores SHA-256 hashes of `SOUL.md`, `IDENTITY.md`, `USER.md`, `AGENTS.md`
in the workspace's `state/identity_hashes.json` and alerts on any silent
modification. Does **not** auto-restore — the agent decides.

```
python3 scripts/protect_identity.py store    # snapshot current hashes
python3 scripts/protect_identity.py check    # compare and alert (default)
python3 scripts/protect_identity.py status   # quick OK / issues summary
```

---

## Adapter / collision toolchain

These five scripts together brought the mechanism count from **365 →
917** by wrapping every orphaned file in `legacy/` and at `brain/` root
into a `BrainMechanism` adapter that `brain_runner` can register and
tick. Run order matters when reproducing from a fresh clone:

| # | Script | What it does |
|---|--------|--------------|
| 1 | `legacy_adapter_generator.py` | Walks `legacy/` and writes one adapter per class with the old `process(pirp_context)` shape into the right layer in `brain/{layer}/{Class}Adapter.py`. |
| 2 | `brain_root_adapter_generator.py` | Same idea for files sitting loose at `brain/` root that aren't already in a layer. Skips files identical to a `legacy/` counterpart (already covered by #1). |
| 3 | `tick_pattern_adapter_generator.py` | Final fold pass for newer-pattern classes whose `tick()` signature isn't `async tick(input_data)`. Generates adapters for sync no-arg, sync with-args, async no-arg, and async non-input variants. Uses **lazy imports** inside `__init__` so the wrapped class isn't picked up by `brain_runner`'s class scanner as a separate mechanism. |
| 4 | `resolve_layer_collisions.py` | Renames the 23 known unnumbered scaffold files that collide with their numbered counterparts (Foundational#, Limbic#, etc.). Suffixes are `Driver` (foundational/subcortical) or `Variant` (integration). |
| 5 | `resolve_runtime_collisions.py` | Catch-all: instantiates every class in every layer, finds any registry-name collision, and renames the loser's `name=` (or `super().__init__("X", ...)` / `name: str = "X"`) to `{name}_{modname}`. Picks the numbered scaffold as winner when present, otherwise alphabetical first. |

### Re-running the toolchain after an import

If new files are dropped into `legacy/` or at `brain/` root, run:

```
python3 scripts/legacy_adapter_generator.py
python3 scripts/brain_root_adapter_generator.py
python3 scripts/tick_pattern_adapter_generator.py
python3 scripts/resolve_runtime_collisions.py
```

Then verify the runner state:

```
python3 -c "
import sys, pkgutil, importlib
sys.path.insert(0, '.')
total = 0
for layer in ['foundational','limbic','subcortical','neocortical','integration']:
    for _, m, ispkg in pkgutil.iter_modules(['brain/' + layer]):
        if ispkg or m.startswith('_'): continue
        importlib.import_module('brain.' + layer + '.' + m)
        total += 1
print(total, 'modules importable')
"
```

A working state is **0 import fails, 0 init fails, 0 collisions**.

---

## Migration / one-shots

### `migrate_outputs.py` (at repo root)
One-shot mover from the Cowork `outputs/` scratchpad into the repo. Reads
the `layer="..."` keyword in each module's `__init__` to decide which
`brain/{layer}/` subfolder to drop it into. Test files always go to
`brain/tests/`. Auto-collapses multi-line citations into single lines so
the verify_build regex matches. `--dry-run` to preview, `--force` to
overwrite.
