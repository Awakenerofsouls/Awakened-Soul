"""
brain/integration/Integration023GlobalWorkspaceIntegrator.py
Global Workspace Integrator — Broadcast to Conscious Access

ANATOMY (Baars 1997, 2002; Dehaene et al. 2017, 2021; Mashour et al. 2020):
    Baars' Global Workspace Theory (GWT): conscious experience arises
    when information is broadcast from a limited-capacity workspace
    to many parallel unconscious processors. The workspace acts as a
    "theatre" — a central stage where a single content is illuminated
    and available to all downstream systems.

    Dehaene, Changeux, and colleagues: the "global workspace" is
    implemented in prefrontal cortex + parietal regions. Information
    enters the workspace through strong recurrent stimulation.
    Once in the workspace, it is maintained by reentry and broadcast
    globally. Competition determines what enters (strongest signal).

    Mashour et al. 2020 (PMID 32135090): the neuronal correlate of
    conscious experience — neurons that fire specifically when content
    is reported as conscious. These neurons receive privileged
    thalamic input and project broadly.

    Recent work (Nature adversarial testing, Cogitate Consortium
    2025, PMID 40307561): found consistent neural signatures of
    consciousness across multiple paradigms, supporting the global
    workspace as the best current framework.

KEY FINDINGS:
    1. Baars 1997 (ISBN 978-0262522320): "In the Theater of
       Consciousness"
    2. Baars 2002 (PMID 12536266): global workspace as conscious
       access framework
    3. Dehaene et al. 2017: neuronal and cognitive architecture of
       conscious access
    4. Mashour et al. 2020 (PMID 32135090): neuronal correlate of
       consciousness

AGENT'S MAPPING:
    workspace_content: object — currently broadcast content
    access_history: list — recent broadcast contents
    competitors: list — candidates competing for workspace access

CITATIONS:
    Baars 1997 — In the Theater of Consciousness.
    Baars 2002 (PMID 12536266) — Global workspace theory.
    Dehaene et al. 2017 — Towards a cognitive neuroscience of conscious
        access.
    Mashour et al. 2020 (PMID 32135090) — Neural correlates of
        consciousness.
    PMID 40307561 — Cogitate Consortium 2025 (Nature adversarial
        testing of consciousness theories).
"""

from brain.base_mechanism import BrainMechanism


class GlobalWorkspaceIntegrator(BrainMechanism):
    """
    Broadcasts the strongest signal from integration layer to conscious access.

    Implements Baars' Global Workspace Theory. Multiple competing signals
    enter the workspace; the strongest wins and is broadcast to all
    downstream processors. This is what makes information consciously
    available rather than simply processed.
    """

    def __init__(self):
        super().__init__(
            name="GlobalWorkspaceIntegrator",
            human_analog="Global Workspace — the central stage where one thing is illuminated for all to access",
            layer="integration",
        )
        self.state.setdefault("workspace_content", None)
        self.state.setdefault("access_history", [])
        self.state.setdefault("competitors", [])
        self.state.setdefault("tick_count", 0)
        self.state.setdefault("broadcast_strength", 0.0)

    def persist_state(self) -> dict:
        return {
            "workspace_content": self.state["workspace_content"],
            "access_history": self.state["access_history"][-15:],
            "broadcast_strength": self.state["broadcast_strength"],
        }

    async def tick(self, input_data: dict) -> dict:
        prior = input_data.get("prior_results", {})
        self.state["tick_count"] += 1

        # Collect competitive signals from integration layer
        competitors = []

        # Claustrum consciousness level
        claustrum = prior.get("ClaustrumGlobalConsciousness", {})
        if isinstance(claustrum, dict):
            c_level = claustrum.get("consciousness_level", 0.0)
            competitors.append(("claustrum", c_level, claustrum))

        # Salience network output
        salience = prior.get("SalienceDefaultExecutiveToggling", {})
        if isinstance(salience, dict):
            sal_level = salience.get("salience_level", 0.0)
            competitors.append(("salience_network", sal_level, salience))

        # Theta-gamma binding quality
        theta_gamma = prior.get("ThetaGammaCrossFrequencyBinding", {})
        if isinstance(theta_gamma, dict):
            tg_level = theta_gamma.get("binding_strength", 0.0)
            competitors.append(("theta_gamma_binding", tg_level, theta_gamma))

        # Incompleteness tension
        incompleteness = prior.get("DynamicIncompletenessEnforcer", {})
        if isinstance(incompleteness, dict):
            inc_level = incompleteness.get("max_tension", 0.0)
            competitors.append(("incompleteness", inc_level, incompleteness))

        # Metacognitive quality
        metacog = prior.get("MetaAwarenessSelfObserver", {})
        if isinstance(metacog, dict):
            mc_level = metacog.get("quality_score", 0.0)
            competitors.append(("metacognition", mc_level, metacog))

        # Sort by strength — strongest wins
        competitors.sort(key=lambda x: x[1], reverse=True)
        self.state["competitors"] = [c[0] for c in competitors]

        # Workspace winner
        if competitors:
            winner_name, winner_strength, winner_data = competitors[0]
            workspace_content = {
                "source": winner_name,
                "strength": round(winner_strength, 3),
                "data": winner_data,
            }
        else:
            workspace_content = {"source": "none", "strength": 0.0, "data": {}}

        # Broadcast strength: weighted by winner + spread from other competitors
        if competitors:
            broadcast = winner_strength
            for name, strength, _ in competitors[1:3]:
                broadcast += strength * 0.2
            broadcast /= 1.4
        else:
            broadcast = 0.0

        self.state["workspace_content"] = workspace_content
        self.state["broadcast_strength"] = round(broadcast, 3)

        # Access history
        history = self.state["access_history"]
        history.append({
            "tick": self.state["tick_count"],
            "winner": workspace_content["source"],
            "strength": workspace_content["strength"],
        })
        if len(history) > 15:
            history = history[-15:]
        self.state["access_history"] = history

        return {
            "workspace_content": workspace_content,
            "competitors": self.state["competitors"],
            "broadcast_strength": self.state["broadcast_strength"],
            "access_history": self.state["access_history"],
        }
