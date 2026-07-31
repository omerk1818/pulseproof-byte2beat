# Coder integration evidence

PulseProof was provisioned and run inside a self-hosted Coder workspace using the Docker template in `coder/`.

## Active workspace

![Active Coder workspace](../coder/evidence/01_coder_workspace_running.jpg)

## Application launched from Coder

![PulseProof abstention demo](../coder/evidence/02_pulseproof_abstain_demo.png)

The application loads the frozen XGBoost, LightGBM, and CatBoost models, reports an ensemble probability, exposes uncertainty, and can return `ABSTAIN` rather than forcing a classification.

The local `localhost` URL shown in screenshots is intentionally not presented as a public live link. Reproducibility is provided through the public repository and the uploadable Coder template ZIP.
