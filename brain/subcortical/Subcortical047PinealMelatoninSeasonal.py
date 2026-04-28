"""
Subcortical047PinealMelatoninSeasonal.py — Wire 47: PinealMelatoninRegulation
================================================================================

Pineal gland. Melatonin secretion, circadian rhythm, seasonal affective
disorder (SAD), photoperiodic time measurement.

Neural substrate: The pineal gland (epiphysis cerebri) is a small
(~150 mg in humans), highly vascularized endocrine organ located in
the epithalamus, attached to the habenular commissure posteriorly.
Its primary function is the synthesis and secretion of melatonin
(N-acetyl-5-methoxytryptamine), a chronobiotic hormone that
serves as the body's internal signal for darkness and seasonal time.

Melatonin synthesis pathway: Tryptophan → serotonin → N-acetylserotonin
→ melatonin. The rate-limiting enzyme is arylalkylamine N-acetyltransferase
(AANAT), whose activity is controlled entirely by the circadian clock
in the suprachiasmatic nucleus (SCN). During darkness, the SCN inhibits
the superior cervical ganglion (SCG), reducing sympathetic tone to
the pineal, allowing AANAT to remain active and produce melatonin.
Light exposure (especially 460-480 nm, melanopsin spectrum) suppresses
melatonin within minutes via the retinohypothalamic tract → SCN →
spinal cord → SCG pathway. Daytime melatonin levels are <10 pg/mL;
nighttime levels peak at 100-200 pg/mL in humans.

Circadian rhythm: Melatonin is the hormonal hand of the circadian clock.
The rhythm is fundamentally binary: melatonin rises ~2-3 hours before
sleep onset (dim light melatonin onset, DLMO), stays elevated through
the night, and drops sharply at dawn. This rhythm entrains peripheral
clocks throughout the body (liver, immune system, metabolism) via
melatonin receptors (MT1, MT2) on nearly every organ. The pineal
itself receives no direct retinal input — all light information
is routed through the SCN.

Seasonal affective disorder and photoperiodism: Day length (photoperiod)
is measured by the duration of melatonin secretion. Short winter nights
→ long melatonin duration → associated with winter SAD in vulnerable
individuals; long summer nights → short melatonin duration → spring/summer
mania in bipolar patients. The seasonal signal is encoded in melatonin
duration, not amplitude. Melatonin acts on MT1 receptors in the pars
tuberalis of the pituitary to regulate thyroid-stimulating hormone (TSH),
which controls the reproductive axis — this is how seasonal breeding
animals time their reproduction to food availability. In humans, the
same circuitry underlies seasonal mood shifts.

Additional pineal functions: Anti-gonadal effects (melatonin inhibits
GnRH/LH/FSH), immune modulation (enhances natural killer cell activity
at night), antioxidant effects (melatonin crosses all membranes including
BBB; directly scavenges hydroxyl radicals), thermoregulation (melatonin
drops core body temperature by 0.5-1°C at sleep onset — the "thermal
gate" hypothesis).

Refs:
- Arendt 2005 J Neural Transm — comprehensive melatonin review
- Pevet 2016 J Pineal Res — melatonin and seasonal biology
- Arendt & Skene 2005 Sleep Med Rev — melatonin and circadian entrainment
- Cajochen et al. 1999 J Neurosci — light suppression of melatonin
- Pevet & Bothorel 2002 — melatonin duration as photoperiodic signal
- Dubocovich 2007 Pharmacol Rev — MT1/MT2 receptor pharmacology
- Lucas et al. 1999 — melanopsin and the photic suppression pathway
- Korf et al. 1998 J Pineal Res — AANAT regulation

CITATIONS:
    PMC6017004 — Tan DX, Xu B, Zhou X et al. (2018). Pineal Calcification, Melatonin
        Production, Aging, Associated Health Consequences and Rejuvenation of the
        Pineal Gland. Molecules.
    PMC11130361 — Reiter RJ, Sharma R, Tan DX et al. (2024). Dual Sources of Melatonin
        and Evidence for Different Primary Functions. Melatonin Res.
"""

from brain.base_mechanism import BrainMechanism
import math


class PinealMelatoninRegulation(BrainMechanism):
    """
    Pineal gland — melatonin secretion regulation.

    Models the pineal gland's endocrine function: receives circadian
    clock input (SCN-driven), light exposure signal (via retinohypothalamic
    tract proxy), computes melatonin synthesis rate, generates the
    circadian signal (melatonin level), and tracks seasonal photoperiod
    (day length → melatonin duration → seasonal modulation).

    Melatonin level drives:
      - Sleep propensity (thermal gate: core temperature drop)
      - Immune modulation (NK cell activity)
      - Seasonal mood (SAD risk in winter/low photoperiod)
      - Reproductive axis suppression

    Outputs:
      melatonin_level: current pineal melatonin concentration proxy
      circadian_signal: circadian phase from melatonin rhythm
      seasonal_modulation: photoperiodic seasonal signal
    """

    MELATONIN_RISE_RATE = 0.04   # rate at which melatonin rises in darkness
    MELATONIN_FALL_RATE = 0.08   # faster suppression by light
    CIRCADIAN_PERIOD_TICKS = 288 # ~24h at 5-min ticks (288 × 5min = 24h)
    SEASONAL_WINDOW = 72         # ticks over which photoperiod is averaged

    def __init__(self):
        super().__init__(
            name="PinealMelatoninRegulation",
            human_analog="Pineal gland — melatonin, circadian rhythm, photoperiod",
            layer="subcortical",
        )
        self.state.setdefault("melatonin_level", 0.1)
        self.state.setdefault("circadian_phase", 0.0)   # 0=noon, 0.5=midnight
        self.state.setdefault("light_exposure", 0.5)    # current ambient light proxy
        self.state.setdefault("night_duration_ticks", 0)
        self.state.setdefault("seasonal_day_length", 0.5)  # 0=short winter day, 1=long summer
        self.state.setdefault("melatonin_duration", 0.5)   # 0=short, 1=long night
        self.state.setdefault("dlmo_phase", 0.0)            # dim light melatonin onset phase
        self.state.setdefault("thermal_gate", 0.0)          # temperature drop proxy
        self.state.setdefault("immune_modulation", 0.5)     # NK cell activity proxy
        self.state.setdefault("seasonal_affect_bias", 0.0)  # SAD risk bias
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        tick = self.state.get("tick_count", 0)

        # --- Circadian phase ---
        # Phase advances with time; use tick count as circadian clock proxy
        phase = (tick % self.CIRCADIAN_PERIOD_TICKS) / self.CIRCADIAN_PERIOD_TICKS
        # phase 0.0 = noon, ~0.25 = evening, ~0.5 = midnight, ~0.75 = dawn

        # --- Light exposure ---
        # Primary: ArousalRegulator provides day/night signal
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        homeostat = prior.get("Homeostat", {})
        dominant_drive = homeostat.get("dominant_drive", "rest")

        # Simulate ambient light: high arousal during day, low at night
        # Drive context modulates light proxy (curiosity → outdoors → more light)
        light_base = 0.5 + (arousal - 0.5) * 0.6
        if dominant_drive == "curiosity":
            light_base = min(1.0, light_base + 0.15)
        elif dominant_drive == "rest":
            light_base = max(0.0, light_base - 0.1)

        # Light varies smoothly through circadian phase
        # Peak light at noon (phase=0), minimum at midnight (phase=0.5)
        phase_light_component = 0.5 * (1.0 + math.cos(2 * math.pi * phase))
        light_exposure = light_base * 0.6 + phase_light_component * 0.4
        light_exposure = max(0.0, min(1.0, light_exposure))

        # --- Seasonal photoperiod ---
        # Day length (photoperiod) varies with seasonal context
        # Encode as slowly-changing seasonal signal driven by tick modulo
        # to simulate seasonal cycle (full cycle = 1 year in ticks)
        year_ticks = self.CIRCADIAN_PERIOD_TICKS * 365  # ticks per year
        year_phase = (tick % year_ticks) / year_ticks  # 0-1 through year
        # Seasonal day length: longest at summer solstice (~day 172), shortest at winter
        seasonal_day_length = 0.5 + 0.35 * math.cos(2 * math.pi * (year_phase - 0.47))
        seasonal_day_length = max(0.15, min(0.85, seasonal_day_length))

        # Melatonin duration: longer on short days (winter), shorter on long days
        # (linear relationship, winter = 10-14h melatonin, summer = 6-8h)
        melatonin_duration = 1.0 - (seasonal_day_length - 0.15) / 0.70
        melatonin_duration = max(0.2, min(0.9, melatonin_duration))

        # --- Melatonin synthesis ---
        current_mel = self.state["melatonin_level"]

        # DLMO: melatonin onset ~2h before sleep (modeled as phase 0.7-0.85)
        dlmo_phase = 0.7 + (1 - seasonal_day_length) * 0.1
        is_night = phase > dlmo_phase or phase < (dlmo_phase - 0.5 + 1.0) % 1.0

        # If light exposure is low AND it's "night" by circadian phase
        if light_exposure < 0.4 and is_night:
            # Darkness: melatonin rises
            melatonin_rise = self.MELATONIN_RISE_RATE * melatonin_duration
            new_mel = min(1.0, current_mel + melatonin_rise)
        elif light_exposure > 0.65 and not is_night:
            # Daylight: melatonin suppressed
            new_mel = max(0.05, current_mel - self.MELATONIN_FALL_RATE)
        else:
            # Transition/twilight: slow rise
            new_mel = current_mel + 0.005 * (1 - current_mel)

        # Night duration tracking
        night_ticks = self.state["night_duration_ticks"]
        if is_night and light_exposure < 0.4:
            night_ticks += 1
        else:
            night_ticks = max(0, night_ticks - 1)

        # --- Thermal gate ---
        # Melatonin drives core temperature drop at sleep onset
        # Temperature drop = proportional to melatonin level (peaks at midnight)
        thermal_gate = new_mel * 0.9 * (0.5 + 0.5 * math.sin(2 * math.pi * phase))

        # --- Immune modulation ---
        # NK cell activity peaks during melatonin surge (mid-sleep)
        # Immune modulation = low during day, high during melatonin peak
        immune_mod = 0.3 + new_mel * 0.6 * math.sin(2 * math.pi * (phase - 0.1))

        # --- Seasonal affective bias ---
        # Long melatonin duration (winter) → potential SAD risk
        # SAD threshold: melatonin duration > 0.7 for sustained period
        current_sad_bias = self.state["seasonal_affect_bias"]
        if melatonin_duration > 0.7:
            sad_delta = (melatonin_duration - 0.7) * 0.01
            seasonal_affect_bias = min(1.0, current_sad_bias + sad_delta)
        else:
            # Recovery in summer
            seasonal_affect_bias = max(0.0, current_sad_bias - 0.005)

        # --- Circadian signal output ---
        # Phase + melatonin = full circadian signal
        circadian_signal = (phase + new_mel) / 2.0

        # --- Persist ---
        self.state["melatonin_level"] = new_mel
        self.state["circadian_phase"] = phase
        self.state["light_exposure"] = light_exposure
        self.state["night_duration_ticks"] = night_ticks
        self.state["seasonal_day_length"] = seasonal_day_length
        self.state["melatonin_duration"] = melatonin_duration
        self.state["dlmo_phase"] = dlmo_phase
        self.state["thermal_gate"] = thermal_gate
        self.state["immune_modulation"] = immune_mod
        self.state["seasonal_affect_bias"] = seasonal_affect_bias
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "melatonin_level": round(new_mel, 4),
            "circadian_signal": round(circadian_signal, 4),
            "seasonal_modulation": {
                "day_length": round(seasonal_day_length, 4),
                "melatonin_duration": round(melatonin_duration, 4),
                "seasonal_affect_bias": round(seasonal_affect_bias, 4),
                "is_winter_mode": melatonin_duration > 0.65,
            },
            "light_exposure_proxy": round(light_exposure, 4),
            "circadian_phase_info": {
                "phase_of_day": round(phase, 4),
                "is_night": is_night,
                "near_dlmo": abs(phase - dlmo_phase) < 0.05,
                "near_midnight": abs(phase - 0.5) < 0.05,
            },
            "physiological_effects": {
                "thermal_gate": round(thermal_gate, 4),
                "immune_modulation": round(immune_mod, 4),
                "sleep_propensity": round(new_mel * 0.8, 4),
            },
        }
