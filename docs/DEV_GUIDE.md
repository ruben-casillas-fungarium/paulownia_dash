## Developer Guide

This document provides an overview of how to extend the Paulownia dashboard.

### Adding parameters

1. Open `core/params.py` and define a new `BaseModel` for your parameters.  Provide default values and sensible ranges.
2. Add the new model as a field of `Scenario` so that it is loaded and stored alongside other parameters.

### Adding computations

1. Create a new module under `core/` (e.g. `sim_newstage.py`) and implement pure functions that accept parameter objects and return `pandas.DataFrame` objects.  Document your outputs.
2. Update `core/aggregate.join_all` to merge your new dataframe into the main dataset and calculate any derived KPIs.
3. Write unit tests under `tests/` to verify your logic.

### Adding UI

1. Create a new file in `pages/` following the naming convention `X_<emoji>_PageName.py` and implement a `page()` function.  Use `streamlit` widgets to expose your parameters.
2. Use `@st.cache_data` when performing expensive computations keyed on the scenario hash.  Store results in `st.session_state` so other pages can access them.

### Theming

Colours and fonts are defined in `assets/theme.json`.  You can adjust these values and reference them in Plotly figures.