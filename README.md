# Live Sewage Discharge

This project is to replace the old live sewage discharge updates for the app.

Since Southern Water changed from the old REST API to the now web based service, I need to obtain data and make it available every hour or 2.

This project uses Python Playwright to automate extracting the discharge data for the last 72 hours for displaying to folks living in the Folkestone to New Romney bay area.

Writes json to:
- https://steve.github.io/sewage-monitor/sewage.json
