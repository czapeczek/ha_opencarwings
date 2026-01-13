#!/usr/bin/env bash
# Build and run tests in Docker
set -euo pipefail
TAG="ha_opencarwings-tests:latest"

docker build -t "$TAG" .
# Run the default CMD (pytest tests -v)
docker run --rm "$TAG"

# You can also override the command, e.g.:
# docker run --rm $TAG pytest tests/test_ev_sensor_states.py -q
