# PulseProof: When Cardiovascular AI Should Refuse to Answer

## Subtitle

Patient-disjoint HPO, selective prediction, stress tests, and a frozen cross-dataset audit show when heart-risk AI stops being trustworthy.

## Executive summary

Cardiovascular machine-learning projects often end with a high internal validation score. PulseProof begins where that workflow usually stops:

> **How do we know when a cardiovascular AI prediction should not be trusted?**

We developed a reliability-first pipeline on the Byte2Beat resources. The design includes physiological input checks, patient-disjoint development/calibration/test partitions, a broad hyperparameter-optimized model benchmark, frozen ensemble selection, probability calibration assessment, selective prediction, reliability stress tests, subgroup auditing, and a source-only cross-dataset transportability experiment.

The central result is not merely an internal ROC-AUC of **0.8069**. It is the discovery that:

1. carefully tuned models cluster within a narrow internal performance range;
2. uncertainty-aware abstention improves performance on the patients for whom the system reports a result;
3. calibration can deteriorate sharply under population shift even when ROC-AUC changes little; and
4. model rankings reverse on a second provided dataset, with simpler linear models transporting better than the source-selected boosted model.

PulseProof is a research and education prototype. It is not a medical device and must not be used for diagnosis, treatment, prognosis, screening, or emergency triage.

---

## 1. Research question

**Can a cardiovascular model remain useful while explicitly exposing invalid inputs, uncertainty, calibration failure, subgroup variation, and dataset shift?**

We deliberately avoided optimizing only one headline metric. Instead, the analysis asks five connected questions:

- Is the evaluation identity-safe?
- Do hyperparameter gains persist across identical patient folds?
- Are predicted probabilities calibrated?
- Can the system abstain on uncertain patients?
- Does performance transport to a second dataset without retraining or post-hoc model selection?

---

## 2. Data integrity and patient-disjoint evaluation

The primary analysis combines `cardio_base.csv` and `cardiac_failure_processed.csv` by `id`.

Before modeling, the notebook verifies that overlapping columns agree exactly:

- `cardio`: 70,000 compared, 0 mismatches;
- `gluc`: 70,000 compared, 0 mismatches;
- `alco`: 70,000 compared, 0 mismatches;
- `active`: 70,000 compared, 0 mismatches.

The physiological quality gate checks age, height, weight, systolic pressure, diastolic pressure, pressure ordering, and calculated BMI.

- Rows before checks: **70,000**
- Rows retained: **68,560**
- Rows rejected from training: **2.06%**

We used a frozen **70% development / 10% calibration / 20% locked-test** protocol.

- Development patients: **47,992**
- Calibration patients: **6,856**
- Locked-test patients: **13,712**
- Patient overlap across partitions: **0**

Each patient has one row in the current table. Therefore, a grouped and a conventional row-level split would happen to produce the same identity-separation property here. We still implemented the evaluation explicitly by patient ID so that leakage remains impossible if repeated measurements are introduced later.

**Recommended figure:** `02_patient_level_split.png`

---

## 3. Model zoo and hyperparameter optimization

We evaluated 11 model families under identical patient folds:

1. Dummy prevalence
2. Logistic regression
3. Gaussian Naive Bayes
4. Shrinkage LDA
5. Random Forest
6. Extra Trees
7. Histogram Gradient Boosting
8. Multilayer Perceptron
9. XGBoost
10. LightGBM
11. CatBoost

The competition run completed **137 successful HPO configurations**. Parameter selection used only development patients and a composite objective combining discrimination and probability quality. The locked test was not used for model-family selection, hyperparameter tuning, blend selection, calibration selection, threshold selection, or abstention-policy selection.

### What optimization changed

Hyperparameter optimization produced its largest ROC-AUC improvement for Extra Trees:

- baseline: **0.7898**
- tuned: **0.7993**
- gain: **+0.0095**

LightGBM improved by **+0.0023**, Random Forest by **+0.0035**, and XGBoost by approximately **+0.0010**. CatBoost and logistic regression changed very little.

This is an important negative result: after sensible feature engineering, strong boosting models were already near the dataset's practical ceiling. Reliability controls contributed more to the final system than unlimited tuning.

**Recommended figure:** `03_hpo_baseline_vs_tuned.png`

---

## 4. Tuned out-of-fold model comparison

The final tuned models were re-evaluated with five patient-grouped out-of-fold splits.

| Model | OOF ROC-AUC | 95% CI | PR-AUC | Brier | ECE |
|---|---:|---:|---:|---:|---:|
| XGBoost | **0.8003** | 0.7963–0.8041 | 0.7798 | 0.1808 | 0.0053 |
| LightGBM | 0.7999 | 0.7958–0.8037 | 0.7798 | 0.1809 | 0.0045 |
| CatBoost | 0.7997 | 0.7957–0.8035 | 0.7791 | 0.1811 | 0.0058 |
| HistGradientBoosting | 0.7994 | 0.7953–0.8032 | **0.7800** | 0.1812 | 0.0045 |
| Extra Trees | 0.7987 | 0.7947–0.8025 | 0.7772 | 0.1815 | 0.0078 |
| Random Forest | 0.7983 | 0.7942–0.8022 | 0.7776 | 0.1816 | 0.0081 |
| Logistic regression | 0.7940 | 0.7898–0.7980 | 0.7715 | 0.1845 | 0.0236 |

The confidence intervals overlap heavily. We therefore avoid claiming that a difference of a few ten-thousandths establishes a universally superior algorithm.

**Recommended figure:** `05_tuned_model_zoo_auc_ci.png`

---

## 5. Frozen ensemble and calibration

The six strongest tuned families were considered for blending:

- XGBoost
- LightGBM
- CatBoost
- HistGradientBoosting
- Extra Trees
- Random Forest

The calibration set selected an equal-weight average of the top three:

- XGBoost: **1/3**
- LightGBM: **1/3**
- CatBoost: **1/3**

It also selected **no post-hoc calibration**. Sigmoid and isotonic calibration did not improve the joint calibration-set criteria. This is another useful negative result: calibration should be tested, not applied automatically.

The decision threshold was frozen at **0.5175** using calibration patients only.

---

## 6. Locked-test performance

After every modeling decision was frozen, the locked test was opened once.

| Metric | Result |
|---|---:|
| ROC-AUC | **0.8069** |
| ROC-AUC 95% CI | **0.7997–0.8143** |
| PR-AUC | **0.7930** |
| PR-AUC 95% CI | **0.7821–0.8037** |
| Brier score | **0.1780** |
| Expected calibration error | **0.0105** |
| Accuracy | **73.85%** |
| Balanced accuracy | **73.78%** |
| F1 | **0.7177** |
| Locked-test patients | **13,712** |

The locked score is consistent with the development OOF estimates and their confidence intervals, which reduces concern that model selection exploited a lucky split.

**Recommended figure:** `09_locked_test_calibration.png`

---

## 7. Selective prediction: allowing the model to abstain

Five uncertainty measures were compared on calibration patients:

- probability margin;
- entropy;
- model disagreement;
- entropy plus disagreement;
- entropy plus disagreement plus out-of-distribution score.

The simplest measure—**distance from the decision boundary**—performed best for mistake detection and risk–coverage behavior. Complexity did not improve uncertainty ranking.

The abstention operating point was frozen at approximately 80% coverage.

| Evaluation | Coverage | ROC-AUC | PR-AUC | Accuracy | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| All locked-test patients | 100.0% | 0.8069 | 0.7930 | 73.85% | 0.1780 | 0.0105 |
| Reported patients | **80.0%** | **0.8321** | **0.8143** | **78.50%** | **0.1610** | **0.0084** |

PulseProof does not claim that abstention makes the model clinically safe. It demonstrates a transparent trade-off: the system can report fewer predictions in exchange for stronger performance among the patients it does report.

**Recommended figure:** `12_locked_test_risk_coverage.png`

---

## 8. Reliability stress tests

The frozen model was evaluated under foreseeable data failures.

| Scenario | ROC-AUC | Brier | ECE | Accuracy |
|---|---:|---:|---:|---:|
| Clean locked test | **0.8069** | **0.1780** | **0.0105** | **73.85%** |
| 10% missing-at-random | 0.8012 | 0.1817 | 0.0232 | 73.02% |
| Blood-pressure measurement noise | 0.7770 | 0.1926 | 0.0220 | 71.02% |
| Population age +10 years | 0.7979 | 0.1967 | **0.1044** | 69.11% |
| Lifestyle fields unavailable | 0.8051 | 0.1788 | 0.0110 | 73.69% |

The age-shift scenario is particularly revealing. ROC-AUC remains close to 0.80, yet calibration error rises almost tenfold. A model can preserve ranking performance while producing unreliable probabilities.

**Recommended figure:** `13_reliability_stress_tests.png`

---

## 9. Subgroup audit

Performance was audited across recorded sex, age, and blood-pressure groups.

Recorded-sex ROC-AUC was:

- Female: **0.8096**
- Male: **0.8018**

Age-group ROC-AUC declined with age:

- Under 50: **0.8284**
- 50–59: **0.7789**
- 60–69: **0.7213**

The blood-pressure strata exposed a thresholding limitation. In the 140–159 and 160+ groups, prevalence was very high and the frozen global threshold classified nearly every patient positive, producing sensitivity of 1.0 but specificity of 0.0. We report this rather than hiding it: a global threshold is not automatically appropriate for every clinical subgroup.

The subgroup results are descriptive. They do not establish fairness or clinical effectiveness.

---

## 10. What drives the model?

Permutation importance identified systolic blood pressure as the dominant signal.

Top features:

1. systolic blood pressure;
2. age × systolic-pressure interaction;
3. cholesterol category;
4. physical activity;
5. age × BMI interaction.

Feature importance describes model behavior and must not be interpreted as a causal medical explanation.

---

## 11. Frozen cross-dataset transportability test

The second provided heart dataset was not used for training, source-model selection, hyperparameter optimization, calibration, threshold selection, or ensemble selection.

Because the two datasets do not share identical variables or endpoint definitions, we trained a separate portable source model using overlapping concepts only:

- age;
- recorded sex;
- systolic blood pressure;
- cholesterol category;
- glucose category.

Source-only selection chose **Portable CatBoost**.

| Dataset | ROC-AUC | 95% CI | PR-AUC | Brier | ECE |
|---|---:|---:|---:|---:|---:|
| Source locked test | **0.7991** | 0.7922–0.8067 | 0.7847 | 0.1816 | 0.0089 |
| Second provided dataset | **0.5487** | 0.5121–0.5850 | 0.5879 | 0.2850 | 0.1800 |

This is a **transportability stress test**, not external clinical validation.

### The complexity–portability paradox

The source-development ranking did not predict external ranking:

- Portable CatBoost was selected from source data but reached external AUC **0.5487**.
- Portable LDA reached external AUC **0.5966**.
- Portable logistic regression reached external AUC **0.5932**.

The simpler models transported better even though they were weaker on the source development data.

A domain classifier separated source and external records with AUC **0.9881**, confirming extreme dataset shift. The largest standardized mean differences were:

- recorded male proportion: **1.0008**
- high cholesterol: **0.8975**
- systolic blood pressure: **0.3479**

The correct conclusion is not “the source model failed a conventional holdout.” The correct conclusion is:

> **Internal model ranking is not a reliable proxy for cross-dataset transportability under severe population, schema, and endpoint shift.**

**Recommended figure:** `17_transportability_and_model_instability.png`

---

## 12. ECG readiness audit

The ECG file contains:

- **528 rows**
- **123,995 columns**

No defensible patient identifier, target field, or linkage key was found. Therefore, ECG was not joined to the supervised tabular dataset.

This is an intentional scientific decision. A visually impressive multimodal model built without defensible patient-level linkage would introduce label leakage or unsupported assumptions. We report ECG readiness and an example trace, but do not claim a multimodal predictor that the data cannot support.

---

## 13. Interactive demo and Coder integration

The frozen XGBoost, LightGBM, and CatBoost ensemble is exposed through a Streamlit research application. The interface applies the same physiological input gate used by the analysis, displays the three component-model probabilities, reports the frozen decision threshold, quantifies uncertainty, and can return **ABSTAIN** instead of forcing a classification.

The application was provisioned and launched inside a self-hosted **Coder** workspace using the reproducible Terraform/Docker template included in the public repository under `coder/`. The template clones the repository, installs the pinned runtime dependencies, runs a model smoke test, starts Streamlit, and waits for the application health endpoint before declaring the workspace ready.

The Media Gallery includes:

- the active `pulseproof-demo` Coder workspace in **Running** state;
- PulseProof opened through the Coder application button;
- an uncertainty example producing **ABSTAIN**; and
- an invalid-input example blocked by the physiological validity gate.

The public repository includes both the readable template source and an uploadable `coder/PulseProof_Coder_Template.zip`. Raw competition data are not included.

Public repository:
https://github.com/omerk1818/pulseproof-byte2beat

Coder template and deployment files:
https://github.com/omerk1818/pulseproof-byte2beat/tree/main/coder
---

## 14. What did not work

Several expected “improvements” did not deliver:

- Extensive HPO produced only small gains for already-strong boosting models.
- A more complex optimized blend did not beat a simple equal average of the top three.
- Post-hoc calibration did not improve the selected joint criteria.
- Ensemble disagreement was weaker for mistake detection than simple probability margin.
- The source-best portable nonlinear model was not the best model on the second dataset.
- ECG could not be defensibly linked to the tabular labels.

These are not omitted experiments. They are part of the result.

---

## 15. Limitations

- Each patient currently contributes one row, so grouped splitting prevents future leakage but is numerically equivalent to identity-unique row splitting in this release.
- The datasets are observational.
- The primary label is not a prospectively validated clinical endpoint.
- The second dataset differs in population, schema, and outcome definition.
- The external experiment is a transportability stress test, not proof of clinical generalization.
- The recorded binary sex field is limited.
- The global threshold behaves poorly in some high-prevalence blood-pressure strata.
- Abstention improves selected-patient metrics but does not establish clinical safety.
- Decision-curve analysis is exploratory because no real deployment utility or treatment policy was supplied.
- No result should guide care for an individual patient.

---

## 16. Conclusion

PulseProof does not present another cardiovascular classifier and stop at ROC-AUC.

It demonstrates a more complete evaluation pattern:

1. verify data integrity;
2. split by patient identity;
3. separate development, calibration, and locked test patients;
4. compare broad model families under identical folds;
5. tune without touching the test set;
6. test calibration rather than assuming it;
7. permit the model to abstain;
8. stress-test realistic data failures;
9. audit subgroup behavior;
10. freeze source decisions before testing transportability;
11. report negative results and unsupported data linkages honestly.

The strongest lesson from this project is simple:

> **A cardiovascular AI system should not only know how to predict. It should know when its evidence no longer supports the prediction.**
