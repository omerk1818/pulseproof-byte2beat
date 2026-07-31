terraform {
  required_providers {
    coder = { source = "coder/coder", version = ">= 2.18.0" }
    docker = { source = "kreuzwerker/docker", version = "~> 3.0" }
  }
}
provider "coder" {}
provider "docker" {}
data "coder_provisioner" "me" {}
data "coder_workspace" "me" {}
data "coder_workspace_owner" "me" {}

data "coder_parameter" "repo_url" {
  name = "repo_url"
  display_name = "PulseProof GitHub repository"
  type = "string"
  mutable = true
  default = "https://github.com/omerk1818/pulseproof-byte2beat"
}

resource "coder_agent" "main" {
  arch = data.coder_provisioner.me.arch
  os = "linux"
  dir = "/home/coder/pulseproof"
  startup_script_timeout = 1200
  startup_script = <<-EOT
    #!/bin/bash
    set -euo pipefail
    REPO_DIR="/home/coder/pulseproof"
    if [ -d "$REPO_DIR/.git" ]; then git -C "$REPO_DIR" pull --ff-only; else rm -rf "$REPO_DIR"; git clone --depth 1 "${data.coder_parameter.repo_url.value}" "$REPO_DIR"; fi
    cd "$REPO_DIR"
    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pkill -f "streamlit run app.py" || true
    nohup .venv/bin/streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true >/tmp/pulseproof.log 2>&1 &
    for attempt in $(seq 1 120); do
      curl -fsS http://localhost:8501/_stcore/health >/dev/null && exit 0
      sleep 5
    done
    cat /tmp/pulseproof.log || true
    exit 1
  EOT
}

resource "docker_image" "workspace" {
  name = "pulseproof-coder-${data.coder_workspace.me.id}:latest"
  build { context = "./build" }
  triggers = { dir_sha1 = sha1(join("", [for file in fileset(path.module, "build/*") : filesha1(file)])) }
}
resource "docker_volume" "home" { name = "coder-${data.coder_workspace.me.id}-home" lifecycle { ignore_changes = all } }
resource "docker_container" "workspace" {
  count = data.coder_workspace.me.start_count
  image = docker_image.workspace.name
  name = "coder-${data.coder_workspace_owner.me.name}-${lower(data.coder_workspace.me.name)}"
  hostname = data.coder_workspace.me.name
  entrypoint = ["sh", "-c", replace(coder_agent.main.init_script, "/localhost|127\\.0\\.0\\.1/", "host.docker.internal")]
  env = ["CODER_AGENT_TOKEN=${coder_agent.main.token}"]
  host { host = "host.docker.internal" ip = "host-gateway" }
  volumes { container_path = "/home/coder" volume_name = docker_volume.home.name read_only = false }
}
resource "coder_app" "pulseproof" {
  agent_id = coder_agent.main.id
  slug = "pulseproof"
  display_name = "PulseProof"
  url = "http://localhost:8501"
  subdomain = false
  share = "public"
  healthcheck { url = "http://localhost:8501/_stcore/health" interval = 5 threshold = 120 }
}
