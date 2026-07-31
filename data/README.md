# Data access

Raw competition CSV files are intentionally **not included** in this repository.

To reproduce the notebook, attach the official Byte2Beat resource containing:

- `Cardiac Failure/cardio_base.csv`
- `Cardiac Failure/cardiac_failure_processed.csv`
- `Heart Attack/heart_processed.csv`
- `ECG Timeseries/ecg_timeseries.csv`

The notebook recursively discovers these files under `/kaggle/input` and supports the original separators used by the resources.
