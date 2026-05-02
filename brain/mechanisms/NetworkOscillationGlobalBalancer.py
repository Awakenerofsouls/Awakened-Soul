"""
NetworkOscillationGlobalBalancer — Multi-Band Oscillatory Coordination

NEURAL SUBSTRATE
================
The brain's computation runs across at least five canonical frequency
bands, each implementing a distinct communication modality:

- **Delta (0.5-4 Hz)** — slow-wave sleep, deep cortical synchronization,
  memory consolidation
- **Theta (4-8 Hz)** — hippocampal-cortical coordination, memory
  encoding, navigation, working memory ordering
- **Alpha (8-12 Hz)** — top-down inhibitory gating, suppression of
  task-irrelevant cortical regions
- **Beta (12-30 Hz)** — top-down communication, motor maintenance,
  prediction-priors propagation
- **Gamma (>30 Hz)** — local microcircuit binding, bottom-up sensory
  processing, conscious access correlate

Buzsáki & Watson 2012 (Mechanisms of Gamma Oscillations) reviewed how
distinct mechanisms generate each band, and how cross-frequency
interactions (e.g. theta-gamma PAC) coordinate across scales.

Bastos 2015 ("Visual areas exert feedforward and feedback influences
through distinct frequency channels") proposed that beta carries
top-down predictions while gamma carries bottom-up errors — a
canonical predictive-coding implementation in cortex.

This balancer mechanism reads the active power across bands and
produces:
- A balance vector (band dominance)
- A health indicator (E/I balance, oscillation regularity)
- A communication-mode signal (top-down vs bottom-up)
- Anomaly detection (epileptiform overpower, alpha lock-up,
  theta-gamma decoupling)

KEY FINDINGS
============
1. Mechanisms of gamma oscillations: PING/ING circuits generate gamma via E-I rhythm; gamma is hallmark of active cortical processing — [Buzsaki G 2012, Annu Rev Neurosci 35:203, doi:10.1146/annurev-neuro-062111-150444]
2. Visual areas use distinct frequency channels: gamma feedforward, beta feedback; canonical predictive-coding implementation — [Bastos AM 2015, Neuron 85:390, doi:10.1016/j.neuron.2014.12.018]
3. Frequency architecture of brain-body oscillations: hierarchical organization across bands; cross-frequency coupling — [Klimesch W 2018, Neurosci Biobehav Rev 95:123, doi:10.1016/j.neubiorev.2018.09.014]
4. Gamma rhythm as guardian of brain health; gamma disruption is signature of Alzheimer's, schizophrenia — [Mably AJ 2018, eLife 7:e35374, doi:10.7554/eLife.35374]
5. Theta-gamma coupling encodes sequences in working memory; alpha modulates inhibitory gating — [Klimesch W 2012, Trends Cogn Sci 16:606, doi:10.1016/j.tics.2012.10.007]

INPUTS (from prior_results)
============================
- ThetaGammaCrossFrequencyBinding.theta_phase_coherence (theta proxy)
- ThetaGammaCrossFrequencyBinding.gamma_amplitude (gamma proxy)
- MedialSeptum.theta_signal
- ClaustrumGlobalConsciousness.slow_wave_modulation (delta proxy)
- DorsolateralPrefrontalCortex.dlpfc_drive (beta top-down proxy)
- ArousalRegulator.tonic_level (alpha-inhibition proxy — high arousal=low alpha)

OUTPUTS (to brain_runner enrichment)
=====================================
- delta_power (0-1)
- theta_power (0-1)
- alpha_power (0-1)
- beta_power (0-1)
- gamma_power (0-1)
- top_down_signal (0-1) — beta + alpha integrated
- bottom_up_signal (0-1) — gamma + theta integrated
- ei_balance (0-1) — excitation-inhibition health (0.5 = healthy)
- oscillation_state (str): "task_engaged" | "rest_default" |
  "deep_sleep" | "epileptiform" | "quiet"
"""

from brain.base_mechanism import BrainMechanism


class NetworkOscillationGlobalBalancer(BrainMechanism):
    """Multi-band oscillation balance coordinator."""

    SMOOTH = 0.20
    EPILEPTIFORM_THRESHOLD = 0.85
    DEEP_SLEEP_THRESHOLD = 0.50

    def __init__(self):
        super().__init__(
            name="NetworkOscillationGlobalBalancerVariant",
            human_analog="Multi-band oscillation balancer (Buzsaki 2012)",
            layer="integration",
        )
        self.state.setdefault("delta_power", 0.0)
        self.state.setdefault("theta_power", 0.0)
        self.state.setdefault("alpha_power", 0.0)
        self.state.setdefault("beta_power", 0.0)
        self.state.setdefault("gamma_power", 0.0)
        self.state.setdefault("top_down_signal", 0.0)
        self.state.setdefault("bottom_up_signal", 0.0)
        self.state.setdefault("ei_balance", 0.5)
        self.state.setdefault("oscillation_state", "quiet")
        self.state.setdefault("recent_states", [])
        self.state.setdefault("tick_count", 0)

    def _delta(self, slow_wave: float, arousal: float) -> float:
        """Delta power — high during deep sleep, low when awake."""
        return min(1.0, slow_wave * 0.7 + max(0.0, 0.5 - arousal) * 0.6)

    def _theta(self, theta_signal: float, theta_coherence: float) -> float:
        """Theta — driven by medial septum + hippocampal coherence."""
        return min(1.0, theta_signal * 0.6 + theta_coherence * 0.4)

    def _alpha(self, arousal: float, dlpfc: float) -> float:
        """Alpha — top-down inhibitory gating; INVERSELY related to
        arousal (Klimesch 2012). High at rest with eyes closed,
        decreases with active task."""
        # Alpha is highest at intermediate arousal (rest, not asleep, not active)
        if arousal < 0.20 or arousal > 0.80:
            return 0.20
        # Bell curve around moderate arousal
        rest_alpha = 1.0 - abs(arousal - 0.45) * 2.0
        return max(0.0, min(1.0, rest_alpha * (1.0 - dlpfc * 0.5)))

    def _beta(self, dlpfc: float, top_down_demand: float) -> float:
        """Beta — top-down maintenance + prediction (Bastos 2015)."""
        return min(1.0, dlpfc * 0.55 + top_down_demand * 0.45)

    def _gamma(self, gamma_amp: float, arousal: float) -> float:
        """Gamma — local sensory binding + active processing."""
        return min(1.0, gamma_amp * 0.7 + arousal * 0.3)

    def _top_down(self, alpha: float, beta: float) -> float:
        """Top-down communication = beta + alpha."""
        return min(1.0, beta * 0.6 + alpha * 0.4)

    def _bottom_up(self, gamma: float, theta: float) -> float:
        """Bottom-up communication = gamma + theta."""
        return min(1.0, gamma * 0.6 + theta * 0.4)

    def _ei_balance(self, gamma: float, alpha: float) -> float:
        """Excitation-inhibition balance proxy.
        Healthy E/I ~ balanced: gamma ~ alpha.
        Excess gamma without alpha = hyperexcitable.
        Excess alpha without gamma = over-inhibited."""
        total = gamma + alpha
        if total < 0.10:
            return 0.5
        return max(0.0, min(1.0, gamma / total))

    def _classify_state(self, delta: float, theta: float, gamma: float,
                          alpha: float, arousal: float) -> str:
        max_band = max(delta, theta, alpha, gamma)
        if max_band < 0.15:
            return "quiet"
        # Epileptiform: any band saturated AND others suppressed
        if max_band > self.EPILEPTIFORM_THRESHOLD:
            others = sorted([delta, theta, alpha, gamma], reverse=True)[1:]
            if max(others) < 0.15:
                return "epileptiform"
        if delta > self.DEEP_SLEEP_THRESHOLD and gamma < 0.20:
            return "deep_sleep"
        if (gamma > 0.40 or theta > 0.40) and arousal > 0.40:
            return "task_engaged"
        if alpha > 0.30 and arousal < 0.50:
            return "rest_default"
        return "quiet"

    def _smooth(self, prev: float, target: float) -> float:
        return prev + (target - prev) * self.SMOOTH

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})

        # No upstream oscillation drivers reported at all → cortex is quiet,
        # not in a default-mode rhythm. Empty pirp_context shouldn't be
        # interpreted as moderate-arousal alpha.
        no_input = not any(
            prior.get(k) for k in (
                "ThetaGammaCrossFrequencyBinding",
                "MedialSeptum",
                "DiagonalBandBroca",
                "ClaustrumGlobalConsciousness",
                "DorsolateralPrefrontalCortex",
                "ArousalRegulator",
                "CingulateAnterior",
            )
        )

        cfc_data = prior.get("ThetaGammaCrossFrequencyBinding", {})
        theta_coh = float(cfc_data.get("theta_phase_coherence", 0.0))
        gamma_amp = float(cfc_data.get("gamma_amplitude", 0.0))

        sept_data = prior.get("MedialSeptum", {})
        if not sept_data:
            sept_data = prior.get("DiagonalBandBroca", {})
        theta_signal = float(sept_data.get("theta_signal",
                                  sept_data.get("theta_drive", 0.0)))

        cl_data = prior.get("ClaustrumGlobalConsciousness", {})
        slow_wave = float(cl_data.get("slow_wave_modulation", 0.0))

        dlpfc_data = prior.get("DorsolateralPrefrontalCortex", {})
        dlpfc = float(dlpfc_data.get("dlpfc_drive",
                            dlpfc_data.get("working_memory_signal", 0.0)))

        ar_data = prior.get("ArousalRegulator", {})
        arousal = float(ar_data.get("tonic_level", 0.30))

        # Top-down demand proxy: cingulate + DLPFC
        acc_data = prior.get("CingulateAnterior", {})
        acc = float(acc_data.get("acc_drive", 0.0))
        top_down_demand = max(dlpfc, acc)

        delta_t = self._delta(slow_wave, arousal)
        theta_t = self._theta(theta_signal, theta_coh)
        alpha_t = self._alpha(arousal, dlpfc)
        beta_t = self._beta(dlpfc, top_down_demand)
        gamma_t = self._gamma(gamma_amp, arousal)

        # Smooth all bands
        prev = self.state
        delta = self._smooth(float(prev.get("delta_power", 0.0)), delta_t)
        theta = self._smooth(float(prev.get("theta_power", 0.0)), theta_t)
        alpha = self._smooth(float(prev.get("alpha_power", 0.0)), alpha_t)
        beta = self._smooth(float(prev.get("beta_power", 0.0)), beta_t)
        gamma = self._smooth(float(prev.get("gamma_power", 0.0)), gamma_t)

        top_down = self._top_down(alpha, beta)
        bottom_up = self._bottom_up(gamma, theta)
        ei = self._ei_balance(gamma, alpha)

        state = self._classify_state(delta, theta, gamma, alpha, arousal)
        if no_input:
            state = "quiet"

        recent = list(self.state.get("recent_states", []))
        recent.append(state)
        if len(recent) > 60:
            recent = recent[-60:]

        self.state["delta_power"] = round(delta, 4)
        self.state["theta_power"] = round(theta, 4)
        self.state["alpha_power"] = round(alpha, 4)
        self.state["beta_power"] = round(beta, 4)
        self.state["gamma_power"] = round(gamma, 4)
        self.state["top_down_signal"] = round(top_down, 4)
        self.state["bottom_up_signal"] = round(bottom_up, 4)
        self.state["ei_balance"] = round(ei, 4)
        self.state["oscillation_state"] = state
        self.state["recent_states"] = recent
        self.state["tick_count"] = int(self.state.get("tick_count", 0)) + 1
        self.persist_state()

        return {
            "delta_power": round(delta, 4),
            "theta_power": round(theta, 4),
            "alpha_power": round(alpha, 4),
            "beta_power": round(beta, 4),
            "gamma_power": round(gamma, 4),
            "top_down_signal": round(top_down, 4),
            "bottom_up_signal": round(bottom_up, 4),
            "ei_balance": round(ei, 4),
            "oscillation_state": state,
        }

    def _gamma_health(self) -> float:
        """Gamma power health (Mably 2018 — Alzheimer's/schizophrenia
        biomarker)."""
        return float(self.state.get("gamma_power", 0.0))

    def _summary(self) -> dict:
        return {
            "delta": self.state.get("delta_power", 0.0),
            "theta": self.state.get("theta_power", 0.0),
            "alpha": self.state.get("alpha_power", 0.0),
            "beta": self.state.get("beta_power", 0.0),
            "gamma": self.state.get("gamma_power", 0.0),
            "ei": self.state.get("ei_balance", 0.5),
            "state": self.state.get("oscillation_state", "quiet"),
        }
