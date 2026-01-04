This will be an OpenCARWINGS integration for HomeAssisstant.

## Authentication (JWT)

This integration supports authentication using the OpenCARWINGS JWT endpoints. During setup, provide your OpenCARWINGS account username and password — the integration will obtain an access and refresh token from `https://opencarwings.viaaq.eu/api/token/obtain/` and use the `Authorization: Bearer <access>` header for API calls. Refreshes are handled automatically when the API returns 401 (expired token).

## Available cars

On setup the integration fetches the list of cars associated with your OpenCARWINGS account from `/api/car/` and stores it in Home Assistant under `hass.data['ha_opencarwings'][<entry_id>]['cars']`.

A sensor `OpenCARWINGS Cars` is added which shows the number of cars as its state and exposes attributes:

- `cars`: full list of car objects returned by the API
- `car_vins`: list of VINs for quick reference

New entities per car:

- **Battery sensor**: `Car Battery` - reports battery level (if available).
- **Location sensor**: `Car Location` - reports last known location (lat,lon) as a string.
- **A/C switch**: `Car A/C` (switch) - simple control to send A/C on/off commands to the car.

Commands sent by the A/C switch use the OpenCARWINGS `/api/command/{vin}/` endpoint.
