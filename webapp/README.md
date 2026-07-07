# datOnym Webapp

Static browser-only test app for DatOnym prompt anonymization.

The app keeps all mappings in browser memory. No prompt text or original values
are sent to a server.

## Local preview

```powershell
py -m http.server 8081 -d webapp
```

Then open http://127.0.0.1:8081.

