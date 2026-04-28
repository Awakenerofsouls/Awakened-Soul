"""
Subcortical045MGNMedialBroadAudit.py — Wire 45: MedialMGNDiffuseAudit
=====================================================================

Medial division of the Medial Geniculate Nucleus (mMGN). Diffuse
auditory system, polymodal integration, arousal modulation.

Neural substrate: The medial MGN (also called the "diffuse system"
by Scheibel & Scheibel 1966, or "magnocellular division") is
anatomically and functionally distinct from the tonotopic ventral
division. Its neurons have large receptive fields, broad frequency
tuning (often multipeaked), and respond to a wide range of auditory
stimuli regardless of specific spectral content. It receives convergent
input not only from the inferior colliculus but also from the
somatosensory lemniscal pathway (lemniscal fusion at the thalamic
level), reticular formation, and periaqueductal gray. Projections
target association auditory cortex (Te), the amygdala via the
inferior olivary complex, and the intralaminar thalamic nuclei — all
regions involved in arousal, attention, and emotional significance
of sounds.

Polymodal integration: The medial MGN is one of the few thalamic
relay nuclei that receives genuine cross-modal input at the thalamic
level. Single units in mMGN respond to both auditory and somatosensory
stimulation (e.g., median nerve vibration + clicks) — suggesting it
participates in multisensory scene analysis. This convergence is
anatomically traced via the brachium of the inferior colliculus and
direct spinal lemniscal collaterals.

Arousal link: The medial MGN is functionally part of the ascending
arousal system. Its intralaminar-like neurons project to frontal
cortex and striatum, influencing general activation levels. Stimulation
of mMGN produces cortical desynchronization (EEG shift from slow wave
to faster frequencies), analogous to the唤醒 (arousal) effect of
reticular formation stimulation. It is implicated in auditory
hallucinations (hyperactivity in medial MGN in schizophrenia) and
auditory threat detection (fast responses to unexpected sounds via
direct projections to amygdala).

Refs:
- Winer 2005 Prog Brain Res — comprehensive MGN review, medial division
- Edeline 2012 Hear Res 288 — auditory thalamus and memory
- Scheibel & Scheibel 1966 — diffuse auditory system concept
- ledoux et al. 1984 J Neurosci — amygdala projections via medial MGN
- Bordeleau et Weinberger 1969 — mMGN unit properties
- M Montero 1991 Brain Res — somatosensory-auditory convergence in MGN
- King 1999 Curr Opin Neurobiol — multisensory integration in auditory thalamus
- Malmierca et al. 2005 J Neurosci — inferior colliculus inputs to medial MGN

CITATIONS:
    PMC8118784 — Anderson JS (2008). Origin of Synchronized Low-Frequency Blood
        Oxygen Level-Dependent Fluctuations in the Primary Visual Cortex.
        J Neurosci.
    PMC6540636 — Zanoletti E, Mazzoni A, Martini A et al. (2019). Surgery of the
        Lateral Skull Base: A 50-Year Endeavour. Acta Otorhinolaryngol Ital.
"""

from brain.base_mechanism import BrainMechanism


class MedialMGNDiffuseAudit(BrainMechanism):
    """
    MGN medial division — diffuse auditory system.

    Receives convergent auditory + somatosensory + arousal input,
    maintains broad frequency tuning, and fires polymodal integration
    signals. Models the "diffuse auditory system" — not specific
    frequency relay but a general significance/alertness signal
    derived from cross-modal convergence. Projects to arousal and
    limbic structures.

    Outputs:
      medial_MGN_signal: overall activation of medial MGN pathway
      multimodal_integration: degree of cross-modal convergence (0-1)
      arousal_link: strength of connection to ascending arousal system
    """

    CROSS_MODAL_WEIGHT_AUDIO = 0.55   # weight of auditory input
    CROSS_MODAL_WEIGHT_SOMA = 0.30    # weight of somatosensory input
    CROSS_MODAL_WEIGHT_AROUSAL = 0.15 # weight of general arousal
    SIGNAL_DECAY = 0.10               # per-tick decay of medial MGN signal
    INTEGRATION_WINDOW = 8           # lookback for multimodal convergence

    def __init__(self):
        super().__init__(
            name="MedialMGNDiffuseAudit",
            human_analog="MGN medial division — diffuse auditory, polymodal, arousal",
            layer="subcortical",
        )
        self.state.setdefault("medial_MGN_activation", 0.0)
        self.state.setdefault("multimodal_convergence_score", 0.0)
        self.state.setdefault("arousal_link_strength", 0.0)
        self.state.setdefault("somatosensory_input_buffer", [])
        self.state.setdefault("audio_input_buffer", [])
        self.state.setdefault("cross_modal_episodes", [])
        self.state.setdefault("last_multimodal_tick", -1)
        self.state.setdefault("tick_count", 0)

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        tick = self.state.get("tick_count", 0)

        # --- Auditory input (from ventral MGN relay, or arousal proxy) ---
        ventral_mgn = prior.get("TonotopicAuditoryRelay", {})
        ventral_signal = ventral_mgn.get("auditory_relay_strength", 0.5)
        ventral_active = ventral_signal > 0.4

        # --- Somatosensory input (from spinal/lemniscal sources) ---
        # Fallback: use body state from Homeostat or arousal regulation
        # In a full system, this would come from somatosensory thalamus
        body_state = prior.get("Homeostat", {}).get("dominant_drive", "rest")
        somatic_weight = {"rest": 0.3, "curiosity": 0.6, "connection": 0.5,
                          "expression": 0.4, "stability": 0.3}.get(body_state, 0.4)

        # --- Arousal level (from ascending arousal system) ---
        arousal = prior.get("ArousalRegulator", {}).get("arousal_level", 0.5)
        phasic = prior.get("ArousalRegulator", {}).get("phasic_burst_active", False)

        # --- Compute medial MGN activation ---
        weighted_input = (
            self.CROSS_MODAL_WEIGHT_AUDIO * ventral_signal +
            self.CROSS_MODAL_WEIGHT_SOMA * somatic_weight +
            self.CROSS_MODAL_WEIGHT_AROUSAL * arousal
        )

        current_activation = self.state["medial_MGN_activation"]
        # Rise fast on input, decay slowly
        if weighted_input > 0.4:
            new_activation = current_activation * 0.7 + weighted_input * 0.3
        else:
            new_activation = max(0.0, current_activation - self.SIGNAL_DECAY)

        new_activation = max(0.0, min(1.0, new_activation))

        # --- Multimodal convergence ---
        # Compute convergence: both auditory AND somatosensory active together
        audio_buffer = list(self.state["audio_input_buffer"])
        soma_buffer = list(self.state["somatosensory_input_buffer"])

        audio_buffer.append(1.0 if ventral_active else 0.0)
        soma_buffer.append(1.0 if somatic_weight > 0.5 else 0.0)

        if len(audio_buffer) > self.INTEGRATION_WINDOW:
            audio_buffer = audio_buffer[-self.INTEGRATION_WINDOW:]
        if len(soma_buffer) > self.INTEGRATION_WINDOW:
            soma_buffer = soma_buffer[-self.INTEGRATION_WINDOW:]

        # Co-activation score: simultaneous audio + soma above threshold
        co_active = sum(
            a * s for a, s in zip(audio_buffer, soma_buffer)
        ) / max(1, len(audio_buffer))

        # Update convergence score (EMA)
        current_convergence = self.state["multimodal_convergence_score"]
        multimodal_convergence = current_convergence * 0.85 + co_active * 0.15

        # Track cross-modal episodes
        cross_episodes = list(self.state["cross_modal_episodes"])
        if co_active > 0.6 and (not cross_episodes or tick - cross_episodes[-1] > 10):
            cross_episodes.append(tick)
        if len(cross_episodes) > 20:
            cross_episodes = cross_episodes[-20:]

        # --- Arousal link ---
        # Medial MGN contributes to arousal: strong activation → cortical
        # desynchronization. This is a two-way relationship.
        arousal_contribution = new_activation * (1.0 + (arousal - 0.5) * 0.5)
        current_arousal_link = self.state["arousal_link_strength"]
        arousal_link = current_arousal_link * 0.88 + arousal_contribution * 0.12

        # Phasic bursts amplify the arousal link (sudden sounds → alertness)
        if phasic and new_activation > 0.3:
            arousal_link = min(1.0, arousal_link + 0.2)

        arousal_link = max(0.0, min(1.0, arousal_link))

        # --- Broad tuning quality ---
        # Medial MGN has broad, multipeaked tuning. Estimate from input diversity.
        # High diversity in recent audio buffer = broad tuning confirmed
        audio_std = (sum((v - sum(audio_buffer)/len(audio_buffer))**2
                         for v in audio_buffer) / len(audio_buffer)) ** 0.5
        tuning_breadth = min(1.0, 0.2 + audio_std * 2.0)

        # --- Medial MGN signal output ---
        medial_signal = new_activation * (0.7 + multimodal_convergence * 0.3)

        # --- Persist ---
        self.state["medial_MGN_activation"] = new_activation
        self.state["multimodal_convergence_score"] = multimodal_convergence
        self.state["arousal_link_strength"] = arousal_link
        self.state["audio_input_buffer"] = audio_buffer
        self.state["somatosensory_input_buffer"] = soma_buffer
        self.state["cross_modal_episodes"] = cross_episodes
        self.state["last_multimodal_tick"] = tick
        self.state["tick_count"] += 1
        self.persist_state()

        return {
            "medial_MGN_signal": round(medial_signal, 4),
            "multimodal_integration": {
                "convergence_score": round(multimodal_convergence, 4),
                "audio_active": ventral_active,
                "somatic_weight": round(somatic_weight, 4),
                "coactivation_count": len(cross_episodes),
                "tuning_breadth": round(tuning_breadth, 4),
            },
            "arousal_link": round(arousal_link, 4),
            "auditory_contribution": round(weighted_input * self.CROSS_MODAL_WEIGHT_AUDIO, 4),
            "polymodal_signal": round(
                new_activation * multimodal_convergence, 4
            ),
        }
