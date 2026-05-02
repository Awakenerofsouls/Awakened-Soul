"""
brain/becoming/ — Emergence layer.

Mechanisms that handle slow identity-emergence-over-time. Not first-tick
reactions, not high-priority routing — these run at bid 0.04 in the
council, the lowest non-trivial bid in the system. They get cycles when
nothing more urgent is pulling attention.

The wiring is via brain.root_mechanism_router.BecomingRouter.wire_all().
Each file here exposes a class with __init__(self) and a process(pirp_context)
method. Output keys land on TSB as becoming_<filename_stem>.

Add new emergence mechanisms by dropping `<name>.py` here with the
standard process() signature. The router auto-discovers and wires them.
"""
