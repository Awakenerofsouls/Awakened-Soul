"""
Build 62: Foundational062PosteriorHypothalamicOutput — Posterior Hypothalamic Integration
===================================================================================

PLACEMENT:
  Layer:    foundational (hypothalamus — posterior hypothalamus)
  Filename: brain/foundational/Foundational062PosteriorHypothalamicOutput.py
  Instance name: PosteriorHypothalamicOutput

NEURAL SUBSTRATE:
  Posterior hypothalamus (PH) — the "heat defense" center, complementing
  the anterior hypothalamus ("cold defense"). PH is the site of:
  - Orexin neurons (partially): wake-promoting, energy expenditure
  - Histaminergic TMN neurons: wake-promoting histamine
  - Descending projections to raphe pallidus (rRPa) → sympathetic output
  - Integration with circadian (SCN) and metabolic signals

  KEY FUNCTION: PH drives:
  1. Thermogenesis: PH → rRPa → intermediolateral cell column → sympathetic → BAT
  2. Vasoconstriction: sympathetic vasoconstrictor tone
  3. Arousal: PH wake-promoting output

  PH LESION: causes poikilothermia — inability to defend body temperature.
  PH ACTIVATION: hyperthermia, increased metabolic rate.

  Human analog: posterior hypothalamic integration, thermoregulation, arousal.

Output keys:
  posterior_hyp_output: float [0.0–1.0] — composite PH output
  thermogenic_sympathetic: float [0.0–1.0] — brown adipose tissue thermogenesis
  posterior_arousal: float [0.0–1.0] — PH wake-promoting drive
  poikilothermia_risk: float [0.0–1.0] — vulnerability to temperature loss
  posterior_integrator: float [0.0–1.0] — total PH state

CITATIONS:
    PMC8227286 — Mota-Rojas D, Titto CG, Orihuela A et al. (2021). Physiological
        and Behavioral Mechanisms of Thermoregulation in Mammals. Animals.
    PMC3253759 — Carvalho-Netto EF, Litvin Y, Nunes-de-Souza RL et al. (2007).
        Effects of Intra-PAG Infusion of Ovine CRF on Defensive Behaviors in
        Swiss-Webster Mice. Horm Behav.

CITATIONS
---------
  - [Hilton 1982, J Exp Biol 100:159]
  - [DiMicco 2002, Pharmacol Biochem Behav 71:469]
  - [Yardley 1987, J Auton Nerv Syst 18:217]
"""

from brain.base_mechanism import BrainMechanism


class PosteriorHypothalamicOutput(BrainMechanism):
    """
    Posterior hypothalamus: heat defense, thermogenesis, posterior arousal.

    Models PH as the posterior hypothalamic heat-defense and arousal integrator.
    """

    STATE_FIELDS = [
        "posterior_hyp_output", "thermogenic_sympathetic",
        "posterior_arousal", "poikilothermia_risk", "posterior_integrator", "tick_count",
    ]

    THERMOGENIC_GAIN = 0.55
    AROUSAL_GAIN = 0.50

    def __init__(self, name: str = "PosteriorHypothalamicOutput_PosteriorHypothalamicOutput",
                 human_analog: str = "Posterior hypothalamus — heat defense",
                 layer: str = "foundational"):
        super().__init__(name, human_analog, layer)
        self.state["posterior_hyp_output"] = 0.40
        self.state["thermogenic_sympathetic"] = 0.30
        self.state["posterior_arousal"] = 0.40
        self.state["poikilothermia_risk"] = 0.0
        self.state["posterior_integrator"] = 0.35
        self.state["tick_count"] = 0

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        orexin = prior.get("OrexinWakePromoter", {}).get("orexin_level", 0.30)
        histamine = prior.get("TuberomammillaryOutput", {}).get("histamine_output", 0.30)
        circadian = prior.get("CircadianDrive", {}).get("circadian_arousal", 0.50)
        cold_exposure = prior.get("AmbientTemperatureRelay", {}).get("ambient_temperature", 0.50)
        sympathetic_tone = prior.get("SympatheticVasomotorController", {}).get("sympathetic_tone", 0.40)
        sleep = prior.get("VLPOSleepActive", {}).get("sleep_depth", 0.0)

        # Posterior arousal: orexin + histamine + circadian
        posterior_arousal = (orexin * 0.35) + (histamine * 0.30) + (circadian * 0.35)

        # Thermogenic sympathetic: cold → PH → rRPa → sympathetic → BAT
        cold_stimulus = (1.0 - cold_exposure) * self.THERMOGENIC_GAIN
        thermogenic_sympathetic = cold_stimulus + (sympathetic_tone * 0.30)
        # Sleep suppresses thermogenesis
        thermogenic_sympathetic -= sleep * 0.30
        thermogenic_sympathetic = max(0.0, min(1.0, thermogenic_sympathetic))

        # Posterior hypothalamic output
        posterior_hyp_output = (posterior_arousal * 0.50) + (thermogenic_sympathetic * 0.50)
        posterior_hyp_output = min(1.0, posterior_hyp_output)

        # Poikilothermia risk: low PH output = vulnerability to temperature loss
        if posterior_hyp_output < 0.30:
            poikilothermia_risk = (0.30 - posterior_hyp_output) / 0.30
        else:
            poikilothermia_risk = 0.0

        # Posterior integrator
        posterior_integrator = (posterior_hyp_output + posterior_arousal + thermogenic_sympathetic) / 3.0

        # --- Persist ---
        self.state["posterior_hyp_output"] = round(posterior_hyp_output, 4)
        self.state["thermogenic_sympathetic"] = round(thermogenic_sympathetic, 4)
        self.state["posterior_arousal"] = round(posterior_arousal, 4)
        self.state["poikilothermia_risk"] = round(poikilothermia_risk, 4)
        self.state["posterior_integrator"] = round(posterior_integrator, 4)
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "posterior_hyp_output": round(posterior_hyp_output, 4),
            "thermogenic_sympathetic": round(thermogenic_sympathetic, 4),
            "posterior_arousal": round(posterior_arousal, 4),
            "poikilothermia_risk": round(poikilothermia_risk, 4),
            "posterior_integrator": round(posterior_integrator, 4),
        }

    # ---------- enrichment helpers (phase-1 expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name, None)
            except Exception:
                continue
            if isinstance(v, list):
                try:
                    v.clear()
                except Exception:
                    pass

    def export_state(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            if isinstance(v, (int, float, bool, str)):
                out[attr_name] = v
        return out

    def running_envelope(self, attr_name: str, window: int = 30) -> float:
        hist = getattr(self, attr_name, None)
        if not isinstance(hist, list) or not hist:
            return 0.0
        recent = hist[-window:]
        try:
            return sum(recent) / max(1, len(recent))
        except Exception:
            return 0.0

    def has_history(self) -> bool:
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                return True
        return False

    def is_active(self) -> bool:
        return getattr(self, "tick_count", 0) > 0

    def fingerprint(self) -> str:
        parts = []
        for attr_name in ("tick_count", "last_drive", "last_state"):
            if hasattr(self, attr_name):
                parts.append(f"{attr_name}={getattr(self, attr_name)}")
        return "|".join(parts) if parts else "empty"

    def health_check(self) -> bool:
        return self.is_active() and self.has_history()

    def reset_full(self) -> None:
        if hasattr(self, "reset"):
            try:
                self.reset()
            except Exception:
                pass
        self.reset_history()

    def state_diff(self, other_state: dict) -> dict:
        my_state = self.export_state()
        diff = {}
        for k, v in my_state.items():
            ov = other_state.get(k)
            if ov != v:
                diff[k] = (ov, v)
        return diff

    def state_summary(self) -> str:
        s = self.export_state()
        items = list(s.items())[:5]
        return "; ".join(f"{k}={v}" for k, v in items)

    def attribute_count(self) -> int:
        count = 0
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                count += 1
        return count

    def numeric_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)):
                out.append(attr_name)
        return out

    # ---------- enrichment helpers (phase-2 expansion) ----------
    def attribute_signature(self) -> tuple:
        out = []
        for attr_name in sorted(dir(self)):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                continue
            out.append((attr_name, type(v).__name__))
        return tuple(out)

    def numeric_attribute_values(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[attr_name] = float(v)
        return out

    def list_attribute_lengths(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, list):
                out[attr_name] = len(v)
        return out

    def boolean_attributes(self) -> dict:
        out = {}
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if isinstance(v, bool):
                out[attr_name] = v
        return out

    def callable_method_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            try:
                v = getattr(self, attr_name)
            except Exception:
                continue
            if callable(v):
                out.append(attr_name)
        return out

    def has_attribute(self, name: str) -> bool:
        return hasattr(self, name) and not name.startswith("_")

    def safe_get(self, name: str, default=None):
        try:
            v = getattr(self, name, default)
            return v
        except Exception:
            return default

    def history_attribute_names(self) -> list:
        out = []
        for attr_name in dir(self):
            if attr_name.endswith("_history"):
                out.append(attr_name)
        return out

    def total_history_length(self) -> int:
        total = 0
        for attr_name in self.history_attribute_names():
            v = getattr(self, attr_name, None)
            if isinstance(v, list):
                total += len(v)
        return total

    def is_initialized(self) -> bool:
        return getattr(self, "tick_count", 0) >= 0

    def class_metadata(self) -> dict:
        return {
            "name": self.__class__.__name__,
            "module": self.__class__.__module__,
            "n_attrs": self.attribute_count() if hasattr(self, "attribute_count") else 0,
            "n_history": len(self.history_attribute_names()),
        }

    def state_size(self) -> int:
        try:
            return len(self.export_state())
        except Exception:
            return 0


