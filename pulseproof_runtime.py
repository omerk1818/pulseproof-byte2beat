from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import json
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from lightgbm import Booster
from catboost import CatBoostClassifier


def load_bundle(model_dir: str | Path) -> Dict[str, Any]:
    model_dir = Path(model_dir)
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    xgb = XGBClassifier()
    xgb.load_model(model_dir / "xgboost.json")
    lgb = Booster(model_file=str(model_dir / "lightgbm.txt"))
    cat = CatBoostClassifier()
    cat.load_model(str(model_dir / "catboost.cbm"))
    return {"metadata": metadata, "models": {"XGBoost": xgb, "LightGBM": lgb, "CatBoost": cat}}


def build_features(age_years: float, gender: int, height: float, weight: float,
                   ap_hi: float, ap_lo: float, cholesterol: int, gluc: int,
                   smoke: int, alco: int, active: int) -> pd.DataFrame:
    bmi = weight / (height / 100.0) ** 2
    pulse_pressure = ap_hi - ap_lo
    map_value = (ap_hi + 2 * ap_lo) / 3
    bp_ratio = ap_hi / ap_lo if ap_lo else np.nan
    chol_high = int(cholesterol > 1)
    gluc_high = int(gluc > 1)
    hypertension = int(ap_hi >= 140 or ap_lo >= 90)
    lifestyle = smoke + alco + (1 - active)
    combined = chol_high + gluc_high + hypertension + smoke + (1 - active)
    return pd.DataFrame([{
        "age_years": age_years, "gender": gender, "height": height,
        "weight": weight, "ap_hi": ap_hi, "ap_lo": ap_lo,
        "cholesterol": cholesterol, "gluc": gluc, "smoke": smoke,
        "alco": alco, "active": active, "bmi": bmi,
        "pulse_pressure": pulse_pressure, "map": map_value,
        "bp_ratio": bp_ratio, "chol_high": chol_high,
        "gluc_high": gluc_high, "hypertension_flag": hypertension,
        "age_sq": (age_years / 10.0) ** 2,
        "bmi_sq": (bmi / 10.0) ** 2,
        "age_sbp_interaction": age_years * ap_hi / 1000.0,
        "age_bmi_interaction": age_years * bmi / 1000.0,
        "metabolic_interaction": cholesterol * gluc,
        "lifestyle_risk_count": lifestyle,
        "combined_risk_count": combined,
    }])


def validate_profile(frame: pd.DataFrame) -> List[str]:
    r = frame.iloc[0]
    issues: List[str] = []
    if not 18 <= r.age_years <= 100: issues.append("Age must be between 18 and 100 years.")
    if not 130 <= r.height <= 210: issues.append("Height must be between 130 and 210 cm.")
    if not 35 <= r.weight <= 200: issues.append("Weight must be between 35 and 200 kg.")
    if not 70 <= r.ap_hi <= 250: issues.append("Systolic pressure is outside the supported range.")
    if not 40 <= r.ap_lo <= 150: issues.append("Diastolic pressure is outside the supported range.")
    if r.ap_hi <= r.ap_lo: issues.append("Systolic pressure must exceed diastolic pressure.")
    if not 12 <= r.bmi <= 70: issues.append("Calculated BMI is physiologically implausible.")
    return issues


def _impute(values: np.ndarray, statistics: list[float]) -> np.ndarray:
    x = np.asarray(values, dtype=float).copy()
    stats = np.asarray(statistics, dtype=float)
    rows, cols = np.where(np.isnan(x))
    x[rows, cols] = stats[cols]
    return x


def apply_calibration(spec: Dict[str, Any], p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    if spec.get("method") == "none": return p
    if spec.get("method") == "sigmoid":
        z = np.log(p / (1 - p))
        return 1 / (1 + np.exp(-(spec["coef"] * z + spec["intercept"])))
    return np.clip(np.interp(p, np.asarray(spec["x"]), np.asarray(spec["y"])), 1e-6, 1 - 1e-6)


def predict(bundle: Dict[str, Any], frame: pd.DataFrame) -> Dict[str, Any]:
    meta = bundle["metadata"]
    features = meta["features"]
    values = frame[features].to_numpy(dtype=float)
    stats = meta["imputer_statistics"]
    xgb_x = _impute(values, stats["XGBoost"])
    lgb_x = _impute(values, stats["LightGBM"])
    cat_x = _impute(values, stats["CatBoost"])
    probs = {
        "XGBoost": float(bundle["models"]["XGBoost"].predict_proba(xgb_x)[:, 1][0]),
        "LightGBM": float(bundle["models"]["LightGBM"].predict(lgb_x)[0]),
        "CatBoost": float(bundle["models"]["CatBoost"].predict_proba(cat_x)[:, 1][0]),
    }
    raw = sum(probs[name] * float(meta["weights"][name]) for name in probs)
    risk = float(apply_calibration(meta["calibration_spec"], np.array([raw]))[0])
    uncertainty = float(1 - abs(2 * risk - 1))
    return {
        "risk": risk,
        "uncertainty": uncertainty,
        "accepted": uncertainty <= float(meta["uncertainty_cutoff"]),
        "positive": risk >= float(meta["decision_threshold"]),
        "threshold": float(meta["decision_threshold"]),
        "model_probabilities": probs,
        "weights": meta["weights"],
    }
