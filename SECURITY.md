# Security policy

## Reporting a vulnerability

Please do not report security issues in public GitHub issues.

Use GitHub's [private vulnerability reporting](https://github.com/tracksim-app/tracksim-python/security/advisories/new)
to tell us about a vulnerability in this library. We aim to reply within a few working days.

Issues with the TrackSim service itself should be reported to TrackSim directly.

## Supported versions

Security fixes are released for the latest minor version only.

## Handling credentials

- Never commit API keys or webhook secrets. Load them from environment variables or a
  secrets manager.
- If a key leaks, regenerate it on the [integrations page](https://tracksim.app/integrations);
  this invalidates the old key.
- Map links (`MapLink.full_url` and `MapLink.flag`) grant access to your route planner
  for 24 hours. Treat them as secrets.
