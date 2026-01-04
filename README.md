This will be an OpenCARWINGS integration for HomeAssisstant.

## Authentication (JWT)

This integration supports authentication using the OpenCARWINGS JWT endpoints. During setup, provide your OpenCARWINGS account username and password — the integration will obtain an access and refresh token from `https://opencarwings.viaaq.eu/api/token/obtain/` and use the `Authorization: Bearer <access>` header for API calls. Refreshes are handled automatically when the API returns 401 (expired token).
