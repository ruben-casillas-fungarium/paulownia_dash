"""Streamlit entry point for the Paulownia dashboard.

This script sets up the session state, provides a scenario gallery for
loading presets, and displays a landing page.  The actual inputs and
outputs are implemented in separate files under the `pages/` directory.
"""

import json
import streamlit as st

from core.params import Scenario

st.set_page_config(page_title="Paulownia Dashboard", layout="wide")

def load_preset(name: str) -> Scenario:
    """Load a preset scenario from the assets/presets folder.

    If the file does not exist or is malformed, returns the default
    Scenario.
    """
    try:
        with open(f"assets/presets/{name}.json", "r") as f:
            data = json.load(f)
        return Scenario.model_validate_json(json.dumps(data))
    except Exception:
        return Scenario()


def main() -> None:
    # --- SESSION SETUP (UNCHANGED CORE LOGIC) -------------------------------
    if "scenario" not in st.session_state:
        st.session_state.scenario = Scenario()

    # --- SIDEBAR: BRANDING & PRESETS ---------------------------------------
    # Logos (placeholders – make sure these files exist in your repo)
    st.sidebar.image(
        "assets/images/FullLogoGroundedRoots.png",
        use_container_width=True,
        caption="Fungarium Global UG"
    )
    st.sidebar.image(
        "assets/images/PretzlPaulowniaLogo.png",
        use_container_width=True,
        caption="Pretzl Paulownia GmbH"
    )

    st.sidebar.markdown("### Quick facts")
    st.sidebar.markdown(
        """
        - **Target:** Replace EPS and petro-foams with mycelium biocomposites  
        - **Core feedstock:** Paulownia biomass + regional residues  
        - **Co-products:** MyzelBooster, theobromine, oleic acid  
        - **Phases:** Micro → A → B → C → D (scaling & replication)
        """
    )

    st.sidebar.header("Load Preset Scenario")
    presets = [
        "germany_wood_harvest",
        "equatorial_fast_growth",
        "soil_regen_5y_pullout",
    ]
    preset_choice = st.sidebar.selectbox("Preset", ["Default"] + presets)
    if preset_choice != "Default":
        st.session_state.scenario = load_preset(preset_choice)
        # st.experimental_rerun()  # optional: keep commented out

    st.sidebar.markdown(
        """
        **Next step:**  
        Go to **Scenario Inputs** (page menu) to configure or run your own
        Paulownia–mycelium scenario and compare it with these presets.
        """
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Regulatory & climate snapshot last updated: **2025-11-13**. "
        "Remember to review this section regularly as EU climate and packaging "
        "rules evolve."
    )

    # --- MAIN PAGE: HERO SECTION -------------------------------------------
    st.title("Paulownia Circular-Economy Dashboard")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("From fast-growing trees and fungi to regional climate & revenue impact")

        st.markdown(
            """
            This dashboard models the integrated **Paulownia + mycelium circular economy**  
            behind **PauwMyco** – from **agroforestry and biomass harvesting** to  
            **mycelium biocomposites**, **chemical co-products**, and **soil regeneration**.

            Use it to explore how different planting, harvesting and processing
            strategies can:

            - Decarbonize packaging, construction and acoustic materials  
            - Monetize Paulownia chemistry (MyzelBooster, theobromine, oleic acid)  
            - Create **regional jobs & EBIT** while aligning with EU climate and
              packaging regulation
            """
        )

        st.markdown(
            """
            Investors can combine this dashboard with our phase roadmap
            (Micro → A → B → C → D) to understand **revenue growth, CAPEX needs and risk**
            for each deployment step.
            """
        )

    with col2:
        # Hero visualization (placeholder path – point to the generated image)
        st.image(
            "assets/images/pauwmyco_dashboard_hero.png",
            caption="PauwMyco: Paulownia biomass → mycelium materials → regional impact",
            use_container_width=True,
        )

        # Key indicative metrics – values taken from PauwMyco documentation
        st.metric(label="Global EPS market (2024, approx.)", value="~€18 B")
        st.metric(label="Phase B annual revenue potential", value="€48–70 M")
        st.metric(label="Long-term plant network (Phase C/D)", value="€250 M+ / year")

        st.caption(
            "Figures illustrative based on PauwMyco's internal projections and "
            "market benchmarks; see investor materials for full financial detail."
        )

    # --- TABS: STORY & DOCUMENTATION ---------------------------------------
    tab1, tab2, tab3 = st.tabs(
        [
            "Circular Model & Revenue Stack",
            "Climate & Policy Context",
            "How to Use this Dashboard",
        ]
    )

    # ---- TAB 1: Circular model --------------------------------------------
    with tab1:
        st.subheader("1. The Paulownia–Mycelium Circular Value Loop")

        col_a, col_b = st.columns([3, 2])

        with col_a:
            st.markdown(
                """
                PauwMyco integrates **Paulownia agroforestry** with **mycelium
                biocomposites** and **bio-chemistry** into a single platform:

                1. **Paulownia cultivation & biomass**
                   - Fast-growing, deep-rooted tree with excellent CO₂ uptake and
                     soil-building potential  
                   - Sourced primarily from the **Pretzlhof Paulownia** network with
                     visibility on ~90% of relevant EU Paulownia feedstock  
                   - Blended with regional residues (e.g. Miscanthus) to de-risk supply

                2. **Mycelium biocomposites (MycoPlatte / MCB)**
                   - Mycelium binds Paulownia-rich substrate into rigid panels or
                     molded shapes  
                   - Thermal performance approaching EPS, with compostable,
                     bio-based end-of-life  
                   - Applications in **protective packaging, acoustic panels and,
                     later, building insulation**

                3. **Chemical co-products (MyzelBooster, theobromine, oleic acid)**
                   - Process water and biomass streams yield **MyzelBooster** (fungal
                     growth booster),  
                     plus higher-purity **theobromine** and **oleic acid** in later
                     phases  
                   - These co-products **subsidise material costs**, increasing
                     contribution margin per tonne

                4. **End-of-life & soil loop**
                   - Spent materials can be shredded, composted and returned to soil  
                   - Nutrient-rich amendments support **soil regeneration and regional
                     agro-ecosystems**

                The result is a **multi-revenue circular model** where one biomass
                input drives **boards, packaging, additives and chemicals** with
                minimal waste.
                """
            )

        with col_b:
            st.image(
                "assets/images/pauwmyco_circular_economy_flow.png",
                caption="Simplified Paulownia–mycelium circular economy flow.",
                use_container_width=True,
            )

            st.markdown(
                """
                **Why investors care**

                - Multiple revenue streams from one asset base  
                - Built-in hedging between materials and chemistry  
                - Strong narrative fit with ESG, green bonds and impact mandates
                """
            )

        st.markdown("---")
        st.subheader("2. Scaling roadmap: Micro → A → B → C → D")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Micro", "Proof-of-concept", "Lab & pilot")
        c2.metric("Phase A", "€13.7 M/y", "First industrial plant")
        c3.metric("Phase B", "€48–70 M/y", "EU & export hub")
        c4.metric("Phase C", "€250 M+/y", "3–5 plants, multi-country")
        c5.metric("Phase D", "€B+ scale", "Global EPS displacement")

        st.caption(
            "Indicative revenues and margins based on PauwMyco's internal "
            "business plan and risk-adjusted scaling strategy."
        )

        with st.expander("Technical notes for experts"):
            st.markdown(
                """
                - Substrate: >50% Paulownia, blended with regional lignocellulosic inputs  
                - Manufacturing: sterilisation → inoculation → growth in molds →
                  pressing → drying/finishing  
                - Performance targets:
                  - Thermal conductivity: ~0.040–0.055 W/(m·K) depending on density  
                  - Compressive strength: ≥ 250 kPa (10% deformation)  
                - Process control: sensor-rich, ML-assisted standardisation across regions
                """
            )

    # ---- TAB 2: Climate & policy context ----------------------------------
    with tab2:
        st.subheader("Why this circular model is structurally favoured in the EU")

        st.markdown("### 1. Climate targets & the need for better materials")

        st.markdown(
            """
            - The **European Green Deal** and the **European Climate Law** lock in
              **–55% net GHG emissions by 2030** and **climate neutrality by 2050**.  
            - Buildings account for ~**40% of EU energy use**; meeting 2030 goals
              requires **~60% reduction in building-related emissions**, pushing
              low-carbon insulation and materials.  
            - A circular, bio-based insulation and packaging material that re-enters
              soils fits directly into this policy direction.
            """
        )

        st.markdown("### 2. Packaging & Packaging Waste Regulation (PPWR 2025/40)")

        st.markdown(
            """
            - From **2026**, the new **PPWR** will require all packaging placed on
              the EU market to be **recyclable** under strict design-for-recycling rules.  
            - **Void space**, including space filled with foams like EPS, is capped
              (usually at **≤ 50%**), pressuring oversized, foam-heavy solutions.  
            - Combined with the **EU plastic levy** on non-recycled plastic packaging,
              this increases the effective cost of conventional EPS packaging.  
            - Several member states, such as France, are moving towards **bans or
              strong restrictions on styrenic packaging** by **2030**, further
              accelerating the shift away from EPS.
            """
        )

        st.markdown(
            """
            **Implication for Pretzl Paulownia:**  
            Bio-based, compostable, regionally sourced cushioning and boards become
            **not just nice-to-have but economically attractive** as compliance costs
            and EPR fees rise for fossil foams.
            """
        )

        st.markdown("### 3. Paulownia agroforestry & regulatory considerations")

        st.markdown(
            """
            - **Paulownia** species are attractive for climate-smart agroforestry:  
              they are **fast-growing**, can absorb **up to ~2× more CO₂** than many
              conventional tree species, and store carbon in wood and soil.  
            - In some EU regions, specific species (e.g. *Paulownia tomentosa*) are on
              **alert lists** for potential invasiveness, and certain member states do
              **not** classify Paulownia as a forest species for afforestation subsidies.  
            - EU regulation on **invasive alien species** requires careful species
              choice, site selection and management to ensure compliance.

            **Our stance in the dashboard narrative:**

            - Focus on **responsible, regulated Paulownia cultivation** with appropriate
              hybrids and management practices.  
            - Emphasise **multi-species agroforestry** and diversified feedstock
              (Paulownia + regional residues) to align with both climate and
              biodiversity goals.  
            - Treat Paulownia as part of a **wider regional biomass strategy**, not a
              monoculture silver bullet.
            """
        )

        with st.expander("How to keep this section up to date"):
            st.markdown(
                """
                - Review **PPWR** updates, national transposition and any new foam
                  restrictions at least **once per year**.  
                - Track the status of Paulownia species on:
                  - EU / EPPO invasive species lists  
                  - National forestry / agroforestry subsidy schemes  
                - Update the summary above and the sidebar date when major regulatory
                  changes occur.
                """
            )

    # ---- TAB 3: How to use the dashboard ----------------------------------
    with tab3:
        st.subheader("From story to numbers: using this dashboard")

        st.markdown(
            """
            This app is designed as an **investor-grade sandbox** for exploring the
            Paulownia–mycelium circular model.

            **1. Start with a preset**

            - Use the sidebar to load a preset, for example:  
              - `germany_wood_harvest` – temperate EU context with industrial
                packaging focus  
              - `equatorial_fast_growth` – high-growth biomass region scenario  
              - `soil_regen_5y_pullout` – soil regeneration and early harvest strategy
            - Each preset loads a tailored `Scenario` into session state, which you can
              inspect and refine on the **Scenario Inputs** page.
            """
        )

        st.markdown(
            """
            **2. Adjust scenario inputs**

            On the **Scenario Inputs** page you can (depending on your implementation):

            - Change **hectares of Paulownia** and rotation length  
            - Modify **growth rates, biomass yields and moisture content**  
            - Set **CAPEX/OPEX assumptions** for processing infrastructure  
            - Choose **end-markets mix** (packaging vs. boards vs. acoustics vs. chemistry)

            This allows you to model **Micro, A, B, C or D-like configurations** and
            stress-test unit economics.
            """
        )

        st.markdown(
            """
            **3. Explore the output pages**

            The other pages (under `pages/`) can present, for example:

            - **Climate impact** – CO₂ sequestered in biomass and stored in products,
              vs. fossil baseline  
            - **Material flows** – tonnes of biomass, m² of mycelium boards, liters of
              MyzelBooster, kg of theobromine / oleic acid  
            - **Financials** – revenue by product line, EBITDA, payback period per phase  
            - **Regional lens** – jobs created, local value added, sensitivity to policy
              changes

            Use these views to build an **investment thesis** and to compare:
            - High-margin, low-volume Micro & A pilots  
            - Versus volume-driven B/C configurations with strong co-product margins.
            """
        )

        st.markdown(
            """
            **4. Takeaways for investor conversations**

            - Translate dashboards into **phase-based milestones** (utilization, CAPEX,
              revenue, EBITDA) that match PauwMyco's business plan.  
            - Use the climate & policy tab as a **talk track** for why this model is
              structurally favoured by EU regulation.  
            - Export screenshots or numbers into pitch decks and data rooms as needed.
            """
        )

        st.info(
            "If you are an investor or partner and would like a tailored scenario "
            "configured with your own regional assumptions, please contact the "
            "Fungarium Global and or Pretzl Paulownia team. This dashboard is an exploratory tool, not a substitute "
            "for full technical and financial due diligence."
        )


if __name__ == "__main__":
    main()