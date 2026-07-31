from pathlib import Path
import json
import pandas as pd
import streamlit as st

from pulseproof_runtime import build_features, load_bundle, predict, validate_profile

ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "model" / "native"
METRICS_PATH = ROOT / "results" / "final_metrics.json"

st.set_page_config(page_title="PulseProof", page_icon="🫀", layout="wide")

@st.cache_resource
def get_bundle():
    return load_bundle(MODEL_PATH)

@st.cache_data
def get_metrics():
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))

bundle = get_bundle()
metrics = get_metrics()

st.title("🫀 PulseProof")
st.subheader("When Cardiovascular AI Should Refuse to Answer")
st.caption("Research and education prototype only — not a medical device or clinical decision tool.")

with st.sidebar:
    st.header("Profile inputs")
    age = st.slider("Age", 18, 100, 55)
    gender_label = st.selectbox("Recorded sex", ["Female", "Male"])
    gender = 1 if gender_label == "Female" else 2
    height = st.number_input("Height (cm)", 100.0, 230.0, 170.0)
    weight = st.number_input("Weight (kg)", 25.0, 250.0, 75.0)
    ap_hi = st.number_input("Systolic blood pressure", 40.0, 300.0, 130.0)
    ap_lo = st.number_input("Diastolic blood pressure", 20.0, 200.0, 80.0)
    cholesterol = st.selectbox("Cholesterol category", [1, 2, 3], format_func=lambda x: {1:"Normal",2:"Above normal",3:"Well above normal"}[x])
    gluc = st.selectbox("Glucose category", [1, 2, 3], format_func=lambda x: {1:"Normal",2:"Above normal",3:"Well above normal"}[x])
    smoke = int(st.checkbox("Smoker"))
    alco = int(st.checkbox("Regular alcohol indicator"))
    active = int(st.checkbox("Physically active", value=True))

frame = build_features(age, gender, height, weight, ap_hi, ap_lo, cholesterol, gluc, smoke, alco, active)
issues = validate_profile(frame)

main, evidence = st.tabs(["Interactive reliability demo", "Verified evidence"])
with main:
    if issues:
        st.error("Input-validity gate blocked inference.")
        for issue in issues: st.write(f"• {issue}")
    else:
        result = predict(bundle, frame)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Estimated probability", f"{result['risk']:.1%}")
        c2.metric("Decision threshold", f"{result['threshold']:.1%}")
        c3.metric("Uncertainty", f"{result['uncertainty']:.3f}")
        c4.metric("Status", "REPORT" if result["accepted"] else "ABSTAIN")
        if result["accepted"]:
            st.success("The profile passed the frozen uncertainty operating point.")
        else:
            st.warning("PulseProof refuses to provide a definitive classification for this uncertain profile.")
        st.dataframe(pd.DataFrame({
            "Model": list(result["model_probabilities"].keys()),
            "Probability": list(result["model_probabilities"].values()),
            "Frozen weight": list(result["weights"].values()),
        }), use_container_width=True)
        st.info("Probabilities are model outputs, not diagnoses. What-if changes are not causal treatment effects.")

with evidence:
    a,b,c,d = st.columns(4)
    a.metric("Locked-test ROC-AUC", f"{metrics['locked_test_auc']:.4f}")
    b.metric("Locked-test PR-AUC", f"{metrics['locked_test_pr_auc']:.4f}")
    c.metric("Selective coverage", f"{metrics['selective_coverage']:.1%}")
    d.metric("Reported-case accuracy", f"{metrics['selective_accuracy']:.1%}")
    st.image(str(ROOT / "assets" / "pulseproof_story.png"), use_container_width=True)
    st.markdown(
        f"**Transportability stress test:** source AUC `{metrics['source_portable_auc']:.4f}` → "
        f"second-dataset AUC `{metrics['external_auc']:.4f}`; domain-shift AUC `{metrics['domain_classifier_auc']:.4f}`."
    )
