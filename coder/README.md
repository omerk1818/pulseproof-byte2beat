# PulseProof Coder Template V4

This version fixes both startup failures seen in earlier templates:

1. It contains no `pkill -f` call, so the Coder setup shell cannot terminate itself.
2. Streamlit binds to `::` so the Coder agent's IPv6 application proxy can reach port 8501.

The startup script also:
- reuses the persistent virtual environment,
- runs a real model smoke test before starting Streamlit,
- writes install logs to `/tmp/pulseproof-install.log`,
- writes app logs to `/tmp/pulseproof.log`,
- exits immediately with the Streamlit log if the app process dies.
