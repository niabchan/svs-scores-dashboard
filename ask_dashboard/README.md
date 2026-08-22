# Ask Dashboard compatibility package

This package is a compatibility layer around the historical root-level `ask_dashboard.py` module.

Python imports the package before the same-named module. The package therefore loads the existing module privately, re-exports its stable API, and layers newer routing, calculation, rendering, and localization behaviour around it.

The package currently contains focused modules for:

- contribution and multilingual question routing;
- intent-contract validation;
- newer calculation/execution paths;
- deterministic localized answer rendering;
- ranking rendering helpers;
- legacy-module loading.

This structure allowed the project to add tested behaviour without a high-risk rewrite of the original single-file implementation late in development.

For v1, this compatibility layer is intentional and is **not** a release blocker. A future direct refactor should be attempted only when it has a concrete maintenance benefit and dedicated regression coverage for the existing public API, routing contracts, calculations, localized rendering, and analytics behaviour.
