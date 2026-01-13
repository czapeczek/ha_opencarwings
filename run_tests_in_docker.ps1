# Build and run tests in Docker (PowerShell)
param(
    [string]$Tag = 'ha_opencarwings-tests:latest'
)

docker build -t $Tag .
# Run the default CMD (pytest tests -v)
docker run --rm $Tag

# To run a single test file:
# docker run --rm $Tag pytest tests/test_ev_sensor_states.py -q
