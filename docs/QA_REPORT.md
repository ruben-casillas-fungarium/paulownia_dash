## QA Report

This document summarises quality assurance checks for the current version of the Paulownia dashboard.

* All unit tests in `tests/` pass with the current implementation.
* Smoke tests confirm that each Streamlit page can be imported and executed without errors when default scenario data is present.
* Download buttons were manually tested to ensure scenario JSON and results CSV can be saved from the browser.
* KPI cards show correct units and values when running the default scenario on the Results page.
* Stub pages contain placeholder text indicating future development areas.