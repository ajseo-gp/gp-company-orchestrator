"""GP Company Experiment Orchestrator (Hermes) — V0.1.

An EXPERIMENT layer over the read-only gp-company-os SSOT. This package never
edits, writes, or claims changes to the OS. PROMOTE yields an OS-change
*candidate* only.
"""

__version__ = "0.1.0"

# Exact OS ref this experiment layer is pinned to (read-only, external).
OS_REF = "60bcdb2ec8ee88287e3664bf0b1b31a287fa246d"
OS_REPO = "ajseo-gp/gp-company-os"
