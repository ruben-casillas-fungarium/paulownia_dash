## User Guide

### Getting started

1. Install the dependencies as described in the project README.
2. Launch the app with `streamlit run app.py`.
3. Use the **Scenario Inputs** page to configure your project parameters.  The parameters are grouped into project settings and pricing.  When you are ready, click *Run Simulation* to compute results.
4. Navigate to the **Results: Time Series** page to view KPIs and charts.  Download the results as CSV if needed.
5. Future pages (Biomass Flows, Water & CO₂, Economics, Sensitivity & Compare, Logistics, Extraction & Products, Substrate & Plates, Cradle‑to‑Gate Summary and End‑of‑Life pages) will provide more detailed views as development progresses.

### Importing and exporting scenarios

You can save your scenario configuration as JSON using the *Download Scenario* button on the Scenario Inputs page.  Later you can re‑upload this file to restore your settings.

### Extending the app

This version of the dashboard contains stub pages for many sections.  Developers can follow the guidelines in `docs/DEV_GUIDE.md` to add functionality.  End users should expect iterative updates to fill out these pages.