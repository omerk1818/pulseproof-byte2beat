# Model Card: PulseProof

## Purpose
PulseProof is a research and education prototype for reliability-aware cardiovascular machine learning. It demonstrates patient-disjoint evaluation, hyperparameter optimization, calibration checks, selective prediction, stress testing, subgroup auditing, and cross-dataset transportability analysis.

## Intended use
- Educational demonstration
- Reproducible ML reliability research
- Exploration of uncertainty and dataset shift

## Prohibited use
PulseProof is **not** a medical device. Do not use it for diagnosis, treatment, prognosis, screening, triage, or individual healthcare decisions.

## Final system
The frozen internal model is an equal-weight ensemble of tuned XGBoost, LightGBM, and CatBoost models. The decision threshold and abstention operating point were selected only on a separate calibration partition.

## Verified locked-test results
- ROC-AUC: 0.8069 (95% CI 0.7997–0.8143)
- PR-AUC: 0.7930
- Brier score: 0.1780
- ECE: 0.0105
- Patient overlap across development/calibration/test: 0

At approximately 80% selective coverage, reported-patient accuracy was 78.5% and ROC-AUC was 0.8321.

## Major limitation
The source-selected portable model fell from AUC 0.7991 on the source locked test to 0.5487 on the second provided dataset. This is a transportability stress test, not external clinical validation. A domain classifier AUC of 0.9881 indicates severe dataset shift.

## ECG decision
The ECG file was explored, but no defensible patient-to-label linkage was available. It was therefore not used in the final supervised model.
