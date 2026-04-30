"""
PosteriorParietalCortex — PPC / Brodmann 5, 7 (Areas 5, 7a, 7b)

NEURAL SUBSTRATE
================
The posterior parietal cortex (PPC) — Brodmann areas 5 and 7 in the
human, with subdivisions 7a and 7b — sits between somatosensory cortex
anteriorly and visual cortex posteriorly, serving as the major
multimodal association region for spatial behavior. PPC neurons combine
sensory signals from many modalities (visual, somatosensory, vestibular,
auditory) with efference-copy motor signals, and the resulting
representation supports spatial coordinate transformations needed for
movement planning (Andersen et al. 1997).

PPC carries the body schema — a continuously updated multisensory map
of the body in space — and "command" signals that originate when the
animal intends to act in extrapersonal space (Mountcastle et al. 1975).
Lesions of PPC produce hemispatial neglect: the patient ignores the
contralesional half of space without primary sensory loss. PPC
projects topographically into prefrontal cortex (Goldman-Rakic 1988)
and is interleaved with retinotopic IPS maps (Sereno 2001), placing it
at the apex of the dorsal "where/how" stream that supports visually
guided action (Goodale & Milner 1992).

KEY FINDINGS
============
1. PPC neurons fire as command signals before reaching/manipulating in
   extrapersonal space — substrate for goal-directed action —
   [Mountcastle V 1975, J Neurophysiol 38:871, PMID 808592]
2. PPC integrates sensory and motor signals across modalities into
   common spatial frames for movement planning —
   [Andersen R 1997, Annu Rev Neurosci 20:303, doi:10.1146/annurev.neuro.20.1.303]
3. Topographic prefrontal-parietal connectivity supports distributed
   spatial cognition networks in primate association cortex —
   [Goldman-Rakic P 1988, Annu Rev Neurosci 11:137, PMID 3284439]
4. Retinotopic maps in human IPS (IPS1, IPS2) anchor PPC's spatial
   representations — topographic parietal organization —
   [Sereno M 2001, Science 294:1350, doi:10.1126/science.1063695]
5. Dorsal-stream parietal cortex transforms vision into action,
   dissociated from ventral perception —
   [Goodale M 1992, Trends Neurosci 15:20, doi:10.1016/0166-2236(92)90344-8]

INPUTS
======
- VisualCortexV1.v1_drive (visual)
- PrimarySomatosensoryCortex.s1_drive (somatosensory)
- IntraparietalSulcus.ips_drive (IPS partner)
- VestibularNuclei.vestibular_drive (head/body in space)
- PrimaryAuditoryCortex.a1_drive (auditory spatial)

OUTPUTS
=======
- ppc_drive (0-1) — overall PPC activation
- spatial_signal (0-1) — composite spatial representation
- body_schema_signal (0-1) — body-in-space schema
- multimodal_integration (0-1) — multisensory binding strength
- spatial_direction (str) — direction of attended/intended target
- neglect_index (0-1) — asymmetry between hemifields (proxy)
- ppc_state (str): "spatial_attention" | "body_schema_active" |
                   "intention" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class PosteriorParietalCortex(BrainMechanism):
    """PPC — multimodal spatial integration / body schema."""

    BASELINE = 0.07
    SMOOTH = 0.20
    ACTIVE_THRESHOLD = 0.20
    INTENTION_THRESHOLD = 0.40
    DIRECTIONS = ("up", "down", "left", "right", "forward", "back")

    def __init__(self):
        super().__init__(
            name="PosteriorParietalCortex",
            human_analog="Posterior parietal cortex (Brodmann 5, 7a, 7b)",
            layer="neocortical",
        )
        self.state.setdefault("ppc_drive", self.BASELINE)
        self.state.setdefault("spatial_signal", 0.0)
        self.state.setdefault("body_schema_signal", 0.0)
        self.state.setdefault("multimodal_integration", 0.0)
        self.state.setdefault("spatial_direction", "none")
        self.state.setdefault("neglect_index", 0.0)
        self.state.setdefault("ppc_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ----- helpers ----------------------------------------------------------

    def _drive_target(self, v1: float, s1: float, ips: float,
                      vest: float, a1: float) -> float:
        """Composite PPC drive (Andersen 1997 — multimodal pooling)."""
        target = (self.BASELINE
                  + v1 * 0.25
                  + s1 * 0.20
                  + ips * 0.20
                  + vest * 0.15
                  + a1 * 0.10)
        return min(1.0, target)

    def _spatial_signal(self, drive: float, v1: float, ips: float) -> float:
        """Composite spatial representation (Mountcastle 1975, Goodale 1992)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.4 + v1 * 0.3 + ips * 0.3)

    def _body_schema(self, drive: float, s1: float, vest: float) -> float:
        """Body schema from somatosensory + vestibular (Andersen 1997)."""
        if drive < 0.15:
            return 0.0
        return min(1.0, drive * 0.3 + s1 * 0.4 + vest * 0.4)

    def _multimodal_integration(self, drive: float, v1: float,
                                  s1: float, a1: float) -> float:
        """Multisensory binding strength: requires multiple active modalities."""
        if drive < 0.15:
            return 0.0
        active_modalities = sum(1 for x in (v1, s1, a1) if x > 0.10)
        if active_modalities < 2:
            return drive * 0.3
        # bonus when multiple modalities co-active
        return min(1.0, drive * 0.4 + active_modalities * 0.20)

    def _select_direction(self, spatial: float, ips_dir: str,
                          v1_dir: str) -> str:
        if spatial < 0.15:
            return "none"
        if ips_dir and ips_dir in self.DIRECTIONS:
            return ips_dir
        if v1_dir and v1_dir in self.DIRECTIONS:
            return v1_dir
        return "forward"

    def _neglect_index(self, left: float, right: float) -> float:
        """Asymmetry between hemifield drives (proxy for neglect)."""
        denom = left + right
        if denom < 0.05:
            return 0.0
        return abs(left - right) / denom

    def _classify_state(self, drive: float, intent: float,
                         body: float) -> str:
        if drive < self.ACTIVE_THRESHOLD:
            return "quiet"
        if intent > self.INTENTION_THRESHOLD:
            return "intention"
        if body > 0.30:
            return "body_schema_active"
        return "spatial_attention"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ----- main tick --------------------------------------------------------

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        v1_data = prior.get("VisualCortexV1", {})
        if not v1_data:
            v1_data = prior.get("PrimaryVisualCortex", {})
        v1 = float(v1_data.get("v1_drive",
                          v1_data.get("v1_signal", 0.0)))
        v1_dir = v1_data.get("salient_direction", "")
        # optional left/right hemifield drives for neglect proxy
        v1_left = float(v1_data.get("left_hemifield",
                          v1_data.get("contralateral_drive", 0.0)))
        v1_right = float(v1_data.get("right_hemifield",
                          v1_data.get("ipsilateral_drive", 0.0)))

        s1_data = prior.get("PrimarySomatosensoryCortex", {})
        s1 = float(s1_data.get("s1_drive", 0.0))

        ips_data = prior.get("IntraparietalSulcus", {})
        ips = float(ips_data.get("ips_drive", 0.0))
        ips_dir = ips_data.get("reach_direction", "")

        vest_data = prior.get("VestibularNuclei", {})
        vest = float(vest_data.get("vestibular_drive",
                            vest_data.get("vest_signal", 0.0)))

        a1_data = prior.get("PrimaryAuditoryCortex", {})
        a1 = float(a1_data.get("a1_drive", 0.0))

        target = self._drive_target(v1, s1, ips, vest, a1)
        prev_drive = float(self.state.get("ppc_drive", self.BASELINE))
        new_drive = self._smooth(prev_drive, target)

        spatial = self._spatial_signal(new_drive, v1, ips)
        body = self._body_schema(new_drive, s1, vest)
        multim = self._multimodal_integration(new_drive, v1, s1, a1)
        direction = self._select_direction(spatial, str(ips_dir), str(v1_dir))
        neglect = self._neglect_index(v1_left, v1_right)
        state = self._classify_state(new_drive, spatial, body)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["ppc_drive"] = round(new_drive, 4)
        self.state["spatial_signal"] = round(spatial, 4)
        self.state["body_schema_signal"] = round(body, 4)
        self.state["multimodal_integration"] = round(multim, 4)
        self.state["spatial_direction"] = direction
        self.state["neglect_index"] = round(neglect, 4)
        self.state["ppc_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "ppc_drive": round(new_drive, 4),
            "spatial_signal": round(spatial, 4),
            "body_schema_signal": round(body, 4),
            "multimodal_integration": round(multim, 4),
            "spatial_direction": direction,
            "neglect_index": round(neglect, 4),
            "ppc_state": state,
        }

    # ----- summary helpers --------------------------------------------------

    def _engagement_ratio(self) -> float:
        recent = self.state.get("recent_states", [])
        if not recent:
            return 0.0
        return sum(1 for s in recent if s != "quiet") / max(1, len(recent))

    def _summary(self) -> dict:
        return {
            "drive": self.state.get("ppc_drive", 0.0),
            "spatial": self.state.get("spatial_signal", 0.0),
            "body": self.state.get("body_schema_signal", 0.0),
            "direction": self.state.get("spatial_direction", "none"),
            "state": self.state.get("ppc_state", "quiet"),
        }
