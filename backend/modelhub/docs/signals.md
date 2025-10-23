# Signals

The `modelhub` app does not define any custom Django signals as of this version. All core logic for models, API keys, routing, and metrics is handled directly in models, views, and services.

If you plan to add signals (e.g., for auditing, notifications, or automation), document them here with:
- The signal name
- What triggers it
- What handlers listen to it
- Side effects or workflows

---

_No custom signals are currently implemented in this app._
