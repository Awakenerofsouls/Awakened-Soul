"""
RespiratoryPacemaker — Pre-Bötzinger Complex Inspiratory Rhythm Generator

NEURAL SUBSTRATE
================
The pre-Bötzinger complex (preBötC) is a bilateral cluster of approximately
600 glutamatergic neurons in the ventrolateral medulla, just rostral to the
lateral reticular nucleus. It is the kernel rhythm-generating region for
inspiratory drive in mammals. preBötC lesion or focal silencing abolishes
breathing; the complex is necessary AND sufficient for inspiratory rhythm.

Rhythm emerges from the network rather than from a single dominant pacemaker
cell. A subset of preBötC neurons exhibit voltage-dependent intrinsic bursting
mediated principally by the persistent sodium current (I_NaP), which produces
the slow subthreshold pacemaker depolarization. A second biophysical mechanism,
the calcium-activated non-selective cationic current (I_CAN), shapes the
amplitude of the inspiratory burst rather than its rhythm period; pacemaker
rhythm can persist in pharmacological I_CAN block.

Burst frequency spans roughly an order of magnitude (~0.05–1 Hz) as a
monotonic function of baseline membrane potential, which is itself set by
neuromodulatory drive from raphe serotonin, locus coeruleus norepinephrine,
and chemosensory input from the retrotrapezoid nucleus / parafacial respiratory
group (CO2 sensing). Excitatory synaptic drive is principally AMPA-mediated;
A-type potassium currents shape inspiratory burst termination.

KEY FINDINGS
============
1. preBötC is necessary and sufficient for inspiratory rhythm generation in
   mammals — [Smith Ellenberger Ballanyi Richter Feldman 1991, Science
    254:726-729]
2. Persistent sodium current (I_NaP) underlies voltage-dependent pacemaker
   bursting at the cellular level — [Del Negro Morgado-Valle Feldman 2005,
    J Neurosci 25:446-453]
3. preBötC pacemaker frequency varies as a monotonic function of baseline
   membrane potential — [Koshiya Smith 1999, Nature 400:360-363]
4. preBötC excitatory neurons synchronize through AMPA-mediated drive;
   A-type K+ currents shape burst termination — [Feldman Del Negro 2006,
    Nat Rev Neurosci 7:232-242]
5. Calcium-activated non-selective cationic current (I_CAN) primarily shapes
   inspiratory burst amplitude rather than rhythm period — [Phillips et al.
    2019, eLife PMC6433470]

INPUTS (from prior_results)
============================
- VitalCoreRegulator.vital_drive (0.0-1.0) — sets baseline membrane potential
- VitalCoreRegulator.sympathetic_tone (0.0-1.0) — boosts breath rate
- ArousalRegulator.tonic_level (0.0-1.0) — LC NE drive to preBötC
- ArousalRegulator.arousal_level (0.0-1.0) — composite arousal
- (optional) co2_proxy from upstream chemosensor

OUTPUTS (to brain_runner enrichment)
=====================================
- respiratory_phase (0.0-1.0): position within current breath cycle
- inspiratory_active (bool): true during inspiratory burst phase
- breath_rate_hz (0.05-1.0): current breaths per second
- inspiratory_drive_amplitude (0.0-1.0): I_CAN-analog burst amplitude
- respiratory_pacemaker_synchronized (bool): network coherent

brain_runner enrichment block:
    rp = all_results.get("RespiratoryPacemaker", {})
    if rp:
        enrichments["brain_respiratory_phase"] = rp.get("respiratory_phase", 0.0)
        enrichments["brain_inspiratory_active"] = rp.get("inspiratory_active", False)
        enrichments["brain_breath_rate_hz"] = rp.get("breath_rate_hz", 0.25)
        enrichments["brain_inspiratory_amplitude"] = rp.get("inspiratory_drive_amplitude", 0.5)
"""

from brain.base_mechanism import BrainMechanism


class RespiratoryPacemaker(BrainMechanism):
    """
    pre-Bötzinger complex analog. Maintains an internal inspiratory phase
    accumulator advanced at a rate set by vital_drive + arousal (membrane
    potential proxy), with burst threshold crossing flipping inspiratory_active
    and an amplitude shaped by drive intensity (I_CAN analog).
    """

    # Rate bounds in Hz (breaths per second). Mammalian human resting ~0.2 Hz
    # (12/min), peaks ~0.5-0.8 Hz under exertion. preBötC literature spans
    # 0.05-1 Hz pacemaker range.
    MIN_RATE_HZ = 0.10
    MAX_RATE_HZ = 0.80
    BASELINE_RATE_HZ = 0.25

    # Tick scaling assumes ~2-second tick interval (per heartbeat cadence)
    TICK_SECONDS = 2.0

    # Inspiratory burst is roughly 30-40% of cycle in normal breathing
    INSPIRATORY_FRACTION = 0.35

    # Synchronization holds when amplitude > threshold
    SYNCHRONIZED_AMPLITUDE_THRESHOLD = 0.30

    AMPLITUDE_BASELINE = 0.50
    AMPLITUDE_DRIVE_GAIN = 0.30

    SMOOTH_FACTOR = 0.30

    def __init__(self):
        super().__init__(
            name="RespiratoryPacemaker",
            human_analog="preBötzinger complex — inspiratory rhythm generator",
            layer="foundational",
        )
        self.state.setdefault("respiratory_phase", 0.0)
        self.state.setdefault("breath_rate_hz", self.BASELINE_RATE_HZ)
        self.state.setdefault("inspiratory_drive_amplitude", self.AMPLITUDE_BASELINE)
        self.state.setdefault("inspiratory_active", False)
        self.state.setdefault("respiratory_pacemaker_synchronized", True)
        self.state.setdefault("recent_breath_rates", [])
        self.state.setdefault("breath_count", 0)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # --- Read upstream membrane-potential-proxy signals ---
        vcr = prior.get("VitalCoreRegulator", {})
        vital_drive = float(vcr.get("vital_drive", 0.5))
        symp_tone = float(vcr.get("sympathetic_tone", 0.5))
        survival_threat = float(vcr.get("survival_threat_level", 0.0))

        arousal = prior.get("ArousalRegulator", {})
        tonic_level = float(arousal.get("tonic_level", 0.55))
        arousal_level = float(arousal.get("arousal_level", 0.55))

        # Optional CO2 proxy: high accumulated arousal/threat acts like CO2
        co2_proxy = max(0.0, (arousal_level - 0.5) * 0.5 + survival_threat * 0.5)

        # --- Compute target breath rate (Hz) ---
        # Membrane potential proxy = weighted sum of vital_drive + arousal + sympathetic
        # + CO2. Higher → higher firing rate per Koshiya & Smith.
        membrane_proxy = (
            vital_drive * 0.30
            + tonic_level * 0.25
            + symp_tone * 0.20
            + co2_proxy * 0.25
        )
        membrane_proxy = max(0.0, min(1.0, membrane_proxy))

        # Map [0, 1] membrane proxy to [MIN_RATE_HZ, MAX_RATE_HZ] log-linearly
        target_rate = (
            self.MIN_RATE_HZ
            + membrane_proxy * (self.MAX_RATE_HZ - self.MIN_RATE_HZ)
        )

        prev_rate = float(self.state["breath_rate_hz"])
        new_rate = prev_rate + (target_rate - prev_rate) * self.SMOOTH_FACTOR

        # --- Compute inspiratory amplitude (I_CAN analog) ---
        # Amplitude scales with drive intensity but not rate
        amp_target = (
            self.AMPLITUDE_BASELINE
            + (vital_drive - 0.5) * self.AMPLITUDE_DRIVE_GAIN
            + (arousal_level - 0.5) * 0.20
            + survival_threat * 0.20
        )
        amp_target = max(0.05, min(1.0, amp_target))

        prev_amp = float(self.state["inspiratory_drive_amplitude"])
        new_amp = prev_amp + (amp_target - prev_amp) * self.SMOOTH_FACTOR

        # --- Advance respiratory phase ---
        # phase increments by breath_rate * tick_seconds (cycles per tick)
        phase_advance = new_rate * self.TICK_SECONDS
        prev_phase = float(self.state["respiratory_phase"])
        new_phase = (prev_phase + phase_advance) % 1.0

        # Detect breath count rollover
        breath_count = int(self.state.get("breath_count", 0))
        if new_phase < prev_phase:
            breath_count += 1

        # --- Inspiratory burst flag (first INSPIRATORY_FRACTION of cycle) ---
        inspiratory_active = new_phase < self.INSPIRATORY_FRACTION

        # --- Synchronization: pacemaker is coherent when amplitude is sufficient ---
        synchronized = new_amp > self.SYNCHRONIZED_AMPLITUDE_THRESHOLD

        # --- Track recent rates (for drift monitoring) ---
        history = list(self.state.get("recent_breath_rates", []))
        history.append(round(new_rate, 4))
        if len(history) > 30:
            history = history[-30:]

        # --- Persist state ---
        self.state["respiratory_phase"] = round(new_phase, 4)
        self.state["breath_rate_hz"] = round(new_rate, 4)
        self.state["inspiratory_drive_amplitude"] = round(new_amp, 4)
        self.state["inspiratory_active"] = inspiratory_active
        self.state["respiratory_pacemaker_synchronized"] = synchronized
        self.state["recent_breath_rates"] = history
        self.state["breath_count"] = breath_count
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "respiratory_phase": round(new_phase, 4),
            "inspiratory_active": inspiratory_active,
            "breath_rate_hz": round(new_rate, 4),
            "inspiratory_drive_amplitude": round(new_amp, 4),
            "respiratory_pacemaker_synchronized": synchronized,
        }

    # ---------- enrichment helpers (phase-1 line expansion) ----------
    def reset_history(self) -> None:
        for attr_name in dir(self):
            if attr_name.startswith("_"):
                continue
            v = getattr(self, attr_name, None)
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


