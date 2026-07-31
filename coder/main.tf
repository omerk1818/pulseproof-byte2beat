terraform {
  required_providers {
    coder = {
      source  = "coder/coder"
      version = ">= 2.18.0"
    }
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "coder" {}
provider "docker" {}

data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "repo_url" {
  name         = "repo_url"
  display_name = "PulseProof GitHub repository"
  description  = "Public GitHub repository cloned into the workspace."
  type         = "string"
  mutable      = true
  default      = "https://github.com/omerk1818/pulseproof-byte2beat"
}

resource "coder_agent" "main" {
  arch = data.coder_provisioner.me.arch
  os   = "linux"
  dir  = "/home/coder/pulseproof"
}

resource "coder_script" "pulseproof_setup" {
  agent_id           = coder_agent.main.id
  display_name       = "Install and start PulseProof"
  run_on_start       = true
  start_blocks_login = true
  timeout            = 1200

  script = <<-EOT
    #!/bin/bash
    set -Eeuo pipefail

    REPO_DIR="/home/coder/pulseproof"
    INSTALL_LOG="/tmp/pulseproof-install.log"
    APP_LOG="/tmp/pulseproof.log"
    PID_FILE="/tmp/pulseproof.pid"

    exec > >(tee -a "$INSTALL_LOG") 2>&1
    trap 'rc=$?; echo "PulseProof setup failed with exit code $rc"; test -f "$APP_LOG" && tail -n 200 "$APP_LOG" || true; exit $rc' ERR

    echo "[1/5] Preparing repository"
    if [ -d "$REPO_DIR/.git" ]; then
      git -C "$REPO_DIR" fetch --depth 1 origin
      git -C "$REPO_DIR" reset --hard origin/main
    else
      rm -rf "$REPO_DIR"
      git clone --depth 1 "${data.coder_parameter.repo_url.value}" "$REPO_DIR"
    fi

    cd "$REPO_DIR"

    echo "[2/5] Preparing Python environment"
    if [ ! -x .venv/bin/python ]; then
      python3 -m venv .venv
    fi
    source .venv/bin/activate

    if [ ! -f .venv/.pulseproof_dependencies_ready ]; then
      python -m pip install --upgrade pip
      python -m pip install -r requirements.txt
      touch .venv/.pulseproof_dependencies_ready
    else
      echo "Dependencies already installed; reusing persistent environment."
    fi

    echo "[3/5] Verifying model bundle"
    python - <<'PY'
from pulseproof_runtime import load_bundle, build_features, predict
bundle = load_bundle("model/native")
frame = build_features(55, 2, 175, 82, 135, 85, 1, 1, 0, 0, 1)
result = predict(bundle, frame)
print(f"Model smoke test OK; risk={result['risk']:.6f}")
PY

    echo "[4/5] Starting Streamlit"
    if curl -fsS http://localhost:8501/_stcore/health >/dev/null 2>&1; then
      echo "PulseProof is already healthy."
      exit 0
    fi

    rm -f "$PID_FILE" "$APP_LOG"
    nohup .venv/bin/python -m streamlit run app.py \
      --server.address :: \
      --server.port 8501 \
      --server.headless true \
      --server.fileWatcherType none \
      >"$APP_LOG" 2>&1 </dev/null &
    APP_PID=$!
    echo "$APP_PID" > "$PID_FILE"
    echo "Started Streamlit with PID $APP_PID"

    echo "[5/5] Waiting for health check"
    for attempt in $(seq 1 120); do
      if curl -fsS http://localhost:8501/_stcore/health >/dev/null 2>&1; then
        echo "PulseProof is healthy."
        exit 0
      fi

      if ! kill -0 "$APP_PID" 2>/dev/null; then
        echo "Streamlit exited before becoming healthy."
        cat "$APP_LOG" || true
        exit 1
      fi

      sleep 2
    done

    echo "PulseProof did not become healthy before timeout."
    cat "$APP_LOG" || true
    exit 1
  EOT
}

resource "docker_image" "workspace" {
  name = "pulseproof-coder-${data.coder_workspace.me.id}:latest"

  build {
    context = "./build"
  }

  triggers = {
    dir_sha1 = sha1(join("", [
      for file in fileset(path.module, "build/*") : filesha1(file)
    ]))
  }
}

resource "docker_volume" "home" {
  name = "coder-${data.coder_workspace.me.id}-home"

  lifecycle {
    ignore_changes = all
  }
}

resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count

  image    = docker_image.workspace.image_id
  name     = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname = data.coder_workspace.me.name

  entrypoint = [
    "sh",
    "-c",
    replace(
      coder_agent.main.init_script,
      "/localhost|127\\.0\\.0\\.1/",
      "host.docker.internal"
    )
  ]

  env = [
    "CODER_AGENT_TOKEN=${coder_agent.main.token}"
  ]

  host {
    host = "host.docker.internal"
    ip   = "host-gateway"
  }

  volumes {
    container_path = "/home/coder"
    volume_name    = docker_volume.home.name
    read_only      = false
  }
}

resource "coder_app" "pulseproof" {
  agent_id     = coder_agent.main.id
  slug         = "pulseproof"
  display_name = "PulseProof"
  url          = "http://localhost:8501"
  subdomain    = false
  share        = "owner"

  healthcheck {
    url       = "http://localhost:8501/_stcore/health"
    interval  = 5
    threshold = 120
  }
}
