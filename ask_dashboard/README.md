# Contribution routing extension

This package is a compatibility layer around the historical root-level `ask_dashboard.py` module.

Python imports the package before the same-named module. The package therefore loads the existing module privately, re-exports its stable API, and overrides only contribution-question routing, calculation, execution, and rendering. This keeps the change isolated while the single-file implementation remains available for a later direct refactor.
