FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git procps sudo build-essential && rm -rf /var/lib/apt/lists/*
ARG USER=coder
RUN useradd --create-home --shell /bin/bash "$USER" && echo "$USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/$USER && chmod 0440 /etc/sudoers.d/$USER
USER $USER
WORKDIR /home/$USER
