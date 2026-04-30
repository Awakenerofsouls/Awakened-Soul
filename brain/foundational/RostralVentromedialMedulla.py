"""
RostralVentromedialMedulla — RVM / ON-OFF Cells / Descending Pain Modulation

NEURAL SUBSTRATE
================
The rostral ventromedial medulla (RVM) is a region encompassing the nucleus
raphe magnus + adjacent reticular formation (gigantocellularis pars-α).
The principal output node of the descending pain-modulation system —
the canonical PAG → RVM → spinal-dorsal-horn pathway.

Two functionally opposing cell populations defined by their response to
nociceptive stimuli:

- **ON cells** — fire DURING noxious stimulus, just before nociceptive
  withdrawal reflex; FACILITATE pain transmission at spinal cord. Mu-
  opioid agonists INHIBIT ON cells.
- **OFF cells** — silenced during noxious stimulus (pause in firing);
  DISINHIBIT pain pathway when active; INHIBIT pain transmission. Mu-
  opioid agonists EXCITE OFF cells.

This bidirectional architecture allows RVM to either suppress or amplify
pain depending on context. Opioid analgesia operates by simultaneously
suppressing ON cells and exciting OFF cells. In chronic pain states,
the balance shifts toward sustained ON-cell facilitation, contributing
to central sensitization.

PAG provides the principal upstream input (glutamatergic + GABAergic).
RVM serotonergic + non-serotonergic projections descend to spinal dorsal
horn via the dorsolateral funiculus.

KEY FINDINGS
============
1. RVM ON/OFF cells reciprocally gate spinal nociceptive transmission;
   ON facilitates, OFF inhibits — [Fields 1991, Annu Rev Neurosci
   14:219, doi:10.1146/annurev.ne.14.030191.001251]
2. PAG→RVM→spinal-dorsal-horn is the canonical descending pain
   modulation pathway — [Basbaum 1984, Annu Rev Neurosci 7:309,
   doi:10.1146/annurev.ne.07.030184.001521]
3. Mu-opioid agonists in RVM excite OFF cells + suppress ON cells →
   analgesia — [Heinricher 1994, Neuroscience 63:279, PMID 7898652]
4. RVM bidirectional control: pain facilitation + inhibition from
   same nucleus; balance shifts in chronic pain — [Porreca 2002,
   Trends Neurosci 25:319, doi:10.1016/S0166-2236(02)02157-4]
5. Chronic pain models show RVM ON-cell facilitation predominates;
   drives central sensitization — [Vanegas 2004, Brain Res Rev
   46:295, PMID 15571771]

INPUTS
======
- PeriaqueductalDefenseRouter.pag_drive
- DescendingPainGate.descending_modulation
- MedullaryRapheMagnus.raphe_5HT_drive
- OpioidProxy.mu_opioid_level (default 0)
- SpinalDorsalHornGate.ascending_nociceptive_signal

OUTPUTS
=======
- rvm_on_cell_firing (0-1)
- rvm_off_cell_firing (0-1)
- descending_facilitation (0-1)
- descending_inhibition (0-1)
- net_pain_modulation (-1 to 1, signed: negative = inhibition,
  positive = facilitation)
- rvm_state (str): "descending_inhibition" | "descending_facilitation" |
  "balanced" | "chronic_facilitation"

brain_runner enrichment:
    rvm = all_results.get("RostralVentromedialMedulla", {})
    if rvm:
        enrichments["brain_rvm_on"] = rvm.get("rvm_on_cell_firing", 0.0)
        enrichments["brain_rvm_off"] = rvm.get("rvm_off_cell_firing", 0.0)
        enrichments["brain_pain_modulation_net"] = rvm.get("net_pain_modulation", 0.0)
        enrichments["brain_rvm_state"] = rvm.get("rvm_state", "balanced")
"""

from brain.base_mechanism import BrainMechanism


class RostralVentromedialMedulla(BrainMechanism):
    """RVM — ON/OFF cell descending pain modulation gateway."""

    SMOOTH = 0.25
    CHRONIC_THRESHOLD = 0.50
    CHRONIC_STREAK = 60  # ticks of sustained ON dominance for chronic state

    def __init__(self):
        super().__init__(
            name="RostralVentromedialMedulla",
            human_analog="Rostral ventromedial medulla (ON/OFF cells)",
            layer="foundational",
        )
        self.state.setdefault("rvm_on_cell_firing", 0.0)
        self.state.setdefault("rvm_off_cell_firing", 0.30)
        self.state.setdefault("descending_facilitation", 0.0)
        self.state.setdefault("descending_inhibition", 0.0)
        self.state.setdefault("net_pain_modulation", 0.0)
        self.state.setdefault("rvm_state", "balanced")
        self.state.setdefault("on_dominant_streak", 0)
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    # ------------------------------------------------------------------
    # ON cells — fire during nociceptive stim; suppressed by opioid (Heinricher 1994)
    # ------------------------------------------------------------------
    def _on_cell(self, ascending_noci: float, opioid: float,
                  chronic_streak: int) -> float:
        """ON cell firing — nociceptive-driven, opioid-suppressed.
        Chronic pain state increases ON sensitivity (Porreca 2002).
        """
        sensitivity = 1.0 + min(0.5, chronic_streak / 120.0)
        target = ascending_noci * 0.65 * sensitivity
        target -= opioid * 0.55
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # OFF cells — silenced during nociceptive stim; excited by opioid (Heinricher 1994)
    # ------------------------------------------------------------------
    def _off_cell(self, ascending_noci: float, opioid: float, pag: float,
                   raphe: float) -> float:
        """OFF cell firing — silenced by noci, excited by opioid + PAG."""
        target = 0.30 + opioid * 0.55 + pag * 0.30 + raphe * 0.15
        target -= ascending_noci * 0.45
        return min(1.0, max(0.0, target))

    # ------------------------------------------------------------------
    # Net modulation — OFF inhibits, ON facilitates
    # ------------------------------------------------------------------
    def _net_modulation(self, on_cell: float, off_cell: float) -> float:
        """Signed net modulation: positive = facilitate, negative = inhibit.
        Range -1 to +1.
        """
        return max(-1.0, min(1.0, on_cell - off_cell))

    # ------------------------------------------------------------------
    # Descending facilitation / inhibition split (separately reported)
    # ------------------------------------------------------------------
    def _descending_split(self, on: float, off: float):
        """Decomposed facilitation and inhibition magnitudes."""
        net = on - off
        if net > 0:
            return min(1.0, net), 0.0
        return 0.0, min(1.0, -net)

    # ------------------------------------------------------------------
    # State classifier (Porreca 2002, Vanegas 2004)
    # ------------------------------------------------------------------
    def _classify_state(self, on: float, off: float, streak: int) -> str:
        if streak > self.CHRONIC_STREAK and on > self.CHRONIC_THRESHOLD:
            return "chronic_facilitation"
        if off - on > 0.15:
            return "descending_inhibition"
        if on - off > 0.15:
            return "descending_facilitation"
        return "balanced"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    # ==================================================================
    # tick
    # ==================================================================
    def _sensitization_window(self, recent_states: list,
                                window_size: int = 50) -> float:
        """Central sensitization window — recurrent ON-cell dominance
        across recent ticks indicates building chronic facilitation
        (Porreca 2002, Vanegas 2004).
        """
        if not recent_states:
            return 0.0
        window = recent_states[-window_size:]
        if not window:
            return 0.0
        on_dominant = sum(1 for s in window
                            if s in ("descending_facilitation",
                                      "chronic_facilitation"))
        return on_dominant / len(window)

    def _opioid_efficacy_modulator(self, opioid: float,
                                      sensitization: float) -> float:
        """Mu-opioid efficacy declines as central sensitization builds —
        models opioid tolerance / hyperalgesia paradox.
        """
        if opioid < 0.10:
            return 1.0
        # Tolerance reduces effective opioid signal
        return max(0.3, 1.0 - sensitization * 0.4)

    def _tick_summary(self) -> dict:
        """Compact downstream-consumer summary."""
        return {
            "on": self.state.get("rvm_on_cell_firing", 0.0),
            "off": self.state.get("rvm_off_cell_firing", 0.0),
            "facilitation": self.state.get("descending_facilitation", 0.0),
            "inhibition": self.state.get("descending_inhibition", 0.0),
            "net": self.state.get("net_pain_modulation", 0.0),
            "state": self.state.get("rvm_state", "balanced"),
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        pag_data = prior.get("PeriaqueductalDefenseRouter", {})
        pag = float(pag_data.get("pag_drive", 0.30))

        dpg_data = prior.get("DescendingPainGate", {})
        descending_mod = float(dpg_data.get("descending_modulation", 0.0))

        raphe_data = prior.get("MedullaryRapheMagnus", {})
        raphe = float(raphe_data.get("raphe_5HT_drive",
                            raphe_data.get("serotonin_drive", 0.30)))

        opioid_data = prior.get("OpioidProxy", {})
        opioid = float(opioid_data.get("mu_opioid_level", 0.0))

        sdh = prior.get("SpinalDorsalHornGate", {})
        ascending_noci = float(sdh.get("ascending_nociceptive_signal", 0.0))

        # --- Streak read for sensitivity sensitization ---
        prev_streak = int(self.state.get("on_dominant_streak", 0))

        # --- ON cells ---
        on_target = self._on_cell(ascending_noci, opioid, prev_streak)
        prev_on = float(self.state.get("rvm_on_cell_firing", 0.0))
        new_on = self._smooth(prev_on, on_target)

        # --- OFF cells ---
        off_target = self._off_cell(ascending_noci, opioid, pag, raphe)
        prev_off = float(self.state.get("rvm_off_cell_firing", 0.30))
        new_off = self._smooth(prev_off, off_target)

        # --- Net + facilitation/inhibition ---
        net_mod = self._net_modulation(new_on, new_off)
        facil, inhib = self._descending_split(new_on, new_off)

        # --- Sustained streak tracking ---
        if new_on > new_off + 0.10:
            on_streak = prev_streak + 1
        else:
            on_streak = max(0, prev_streak - 2)

        state = self._classify_state(new_on, new_off, on_streak)

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["rvm_on_cell_firing"] = round(new_on, 4)
        self.state["rvm_off_cell_firing"] = round(new_off, 4)
        self.state["descending_facilitation"] = round(facil, 4)
        self.state["descending_inhibition"] = round(inhib, 4)
        self.state["net_pain_modulation"] = round(net_mod, 4)
        self.state["rvm_state"] = state
        self.state["on_dominant_streak"] = on_streak
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "rvm_on_cell_firing": round(new_on, 4),
            "rvm_off_cell_firing": round(new_off, 4),
            "descending_facilitation": round(facil, 4),
            "descending_inhibition": round(inhib, 4),
            "net_pain_modulation": round(net_mod, 4),
            "rvm_state": state,
            "on_dominant_streak": on_streak,
        }
