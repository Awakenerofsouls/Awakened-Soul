"""
Build 56: Foundational056ParaventricularAutonomic — PVN Autonomic Integration
==========================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — paraventricular nucleus, PVN)
  Filename: brain/foundational/Foundational056ParaventricularAutonomic.py
  Instance name: ParaventricularAutonomic

NEURAL SUBSTRATE:
  Paraventricular nucleus (PVN) — the master autonomic integrator in the
  hypothalamus. PVN contains multiple cell types:
  - Parvocellular neurosecretory: CRH → anterior pituitary (HPA axis)
  - Parvocellular pre-autonomic: projects to NTS, RVLM, IML (sympathetic)
  - Magnocellular neurosecretory: oxytocin/vasopressin → posterior pituitary
  - Parvicellular autonomic: descending control of autonomic tone

  KEY PVN PROJECTIONS:
  - PVN → NTS: modulates baroreflex sensitivity
  - PVN → RVLM: drives sympathetic output
  - PVN → dorsal motor nucleus of vagus: parasympathetic control
  - PVN → spinal cord IML (T1-L2): preganglionic sympathetic

  PVN integrates: limbic (stress), osmolality (ADH), energy state (CRH),
  and circadian signals.

  Human analog: stress response, autonomic integration, PVN dysfunction.

Output keys:
  pvn_autonomic_output: float [0.0–1.0] — composite PVN autonomic drive
  hpa_axis_command: float [0.0–1.0] — HPA axis CRH output
  sympathetic_pvn_drive: float [0.0–1.0] — PVN → RVLM sympathetic command
  parasympathetic_pvn_drive: float [0.0–1.0] — PVN → DMNV parasympathetic command
  pvn_integrator: float [0.0–1.0] — PVN overall state

CITATIONS:
    PMC5451722 — Kania A, Gugula A, Grabowiecka A et al. (2017). Inhibition of
        Oxytocin and Vasopressin Neuron Activity in Rat Hypothalamic Paraventricular
        Nucleus by Relaxin-3-RXFP3 Signalling. J Neurosci.
    PMC6579083 — Wotjak CT, Kubota M, Liebsch G et al. (1996). Release of
        Vasopressin Within the Rat Paraventricular Nucleus in Response to Emotional
        Stress. Eur J Neurosci.
"""

from brain.base_mechanism import BrainMechanism


class ParaventricularAutonomic(BrainMechanism):
    """
    PVN: autonomic integration, HPA axis, autonomic command.

    Models PVN as the master autonomic integrator.
    """

    STATE_FIELDS = [
        "pvn_autonomic_output", "hpa_axis_command", "sympathetic_pvn_drive",
        "parasympathetic_pvn_drive", "pvn_integrator", "tick_count",
    ]

    SYMPATHETIC_GAIN = 0.55
    PARASYMPATHETIC_GAIN = 0.40

    def __init__(self, name: str = "ParaventricularAutonomic",
                 human_analog: str = "PVN — master autonomic integrator",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["pvn_autonomic_output"] = 0.40
        self.state["hpa_axis_command"] = 0.30
        self.state["sympathetic_pvn_drive"] = 0.30
        self.state["parasympathetic_pvn_drive"] = 0.20
        self.state["pvn_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        crh = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        stress = prior.get("CRHStressDispatcher", {}).get("crh_level", 0.0)
        limbic = prior.get("AmygdalaOutput", {}).get("fear_signal", 0.0)
        osmolality = prior.get("FacialGradientSensor", {}).get("osmolality_signal", 0.50)
        baroreflex = prior.get("BaroreflexBalancer", {}).get("baroreflex_activity", 0.50)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)

        # Sympathetic PVN drive: stress + limbic + circadian
        sympathetic_pvn = (stress * 0.40) + (limbic * 0.30) + (circadian * 0.30)
        sympathetic_pvn_drive = min(1.0, sympathetic_pvn)

        # Parasympathetic PVN drive: baroreflex activates vagal PVN pathway
        parasympathetic_pvn = baroreflex * self.PARASYMPATHETIC_GAIN
        parasympathetic_pvn_drive = min(1.0, parasympathetic_pvn)

        # HPA axis command: CRH output
        hpa_axis_command = min(1.0, crh * 0.60 + stress * 0.40)

        # PVN autonomic output: balance of sympathetic and parasympathetic
        pvn_autonomic_output = sympathetic_pvn_drive - parasympathetic_pvn_drive
        pvn_autonomic_output = max(0.0, min(1.0, 0.30 + pvn_autonomic_output * 0.70))

        # PVN integrator
        pvn_integrator = (pvn_autonomic_output + hpa_axis_command + sympathetic_pvn_drive) / 3.0

        # --- Persist ---
        self.state["pvn_autonomic_output"] = round(pvn_autonomic_output, 4)
        self.state["hpa_axis_command"] = round(hpa_axis_command, 4)
        self.state["sympathetic_pvn_drive"] = round(sympathetic_pvn_drive, 4)
        self.state["parasympathetic_pvn_drive"] = round(parasympathetic_pvn_drive, 4)
        self.state["pvn_integrator"] = round(pvn_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "pvn_autonomic_output": round(pvn_autonomic_output, 4),
            "hpa_axis_command": round(hpa_axis_command, 4),
            "sympathetic_pvn_drive": round(sympathetic_pvn_drive, 4),
            "parasympathetic_pvn_drive": round(parasympathetic_pvn_drive, 4),
            "pvn_integrator": round(pvn_integrator, 4),
        }
