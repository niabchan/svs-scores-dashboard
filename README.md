# SVS Scores Dashboard

Interactive Streamlit dashboard for reviewing Evony SVS score data by period, alliance, player, and contribution pattern.

## Ask Dashboard analytics safety

Analytics and developer tools should be enabled deliberately per deployment.

For a production deployment that is not yet intended to collect analytics, set:

```toml
ASK_DASHBOARD_DEBUG_LOG = "false"
ASK_DASHBOARD_ANALYTICS_MODE = "off"
```

`ASK_DASHBOARD_ANALYTICS_ADMIN_PASSWORD` protects developer tools only in versions that gate the entire developer section. Do not rely on the password alone when running an older analytics build; disable `ASK_DASHBOARD_DEBUG_LOG` until the access-control fix is deployed.
