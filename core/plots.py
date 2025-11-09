# MIT License
"""Plotly figure builders for the Paulownia dashboard.

This module centralises creation of Plotly figures used by the Streamlit
frontend.  Keeping the plotting code separate from the page logic
facilitates consistent styling and makes it easier to adapt the
visualisations across the application.
"""

from __future__ import annotations
import pandas as pd
import plotly.graph_objects as go

def fig_cashflow(df: pd.DataFrame) -> go.Figure:
    """Create an annual cashflow bar chart.

    Parameters
    ----------
    df:
        Dataframe with at least columns 'year' and 'cashflow'.

    Returns
    -------
    plotly.graph_objects.Figure
        A simple bar chart of cashflows per year.
    """
    fig = go.Figure()
    fig.add_bar(x=df["year"], y=df["cashflow"], name="Cashflow")
    fig.update_layout(
        title="Annual Cashflow",
        xaxis_title="Year",
        yaxis_title="Cashflow (EUR)",
        template="plotly_white",
    )
    return fig


def fig_co2(df: pd.DataFrame) -> go.Figure:
    """Create a line chart of CO₂ fixed per year and cumulative.

    Parameters
    ----------
    df:
        Dataframe with at least columns 'year', 'co2_t' and 'cum_co2_t'.

    Returns
    -------
    plotly.graph_objects.Figure
        A chart with two traces: annual and cumulative CO₂.
    """
    fig = go.Figure()
    fig.add_scatter(x=df["year"], y=df["co2_t"], mode="lines+markers", name="Annual CO₂ (t)")
    fig.add_scatter(x=df["year"], y=df["cum_co2_t"], mode="lines", name="Cumulative CO₂ (t)")
    fig.update_layout(
        title="CO₂ Fixation",
        xaxis_title="Year",
        yaxis_title="Tonnes CO₂",
        template="plotly_white",
    )
    return fig

def fig_waterfall_business(df: pd.DataFrame)->go.Figure:
    r=df.iloc[0]
    measure=['relative']*6+['total']
    labels=['Rev plates','Rev extract','- Plates cost','- Transport','- Additives','- Inoculum','Net']
    values=[r.get('rev_plates',0),r.get('rev_extract',0),-r.get('cost_plates',0),-r.get('transport_cost_eur',0),-r.get('additives_cost_eur',0),-r.get('inoculum_cost_eur',0),r.get('cashflow_business',0)]
    fig=go.Figure(go.Waterfall(measure=measure,x=labels,y=values,connector={'line':{'width':1}}))
    fig.update_layout(template='plotly_white',title='Business Waterfall (EUR/yr)')
    return fig

def fig_allocation_donut(labels, values)->go.Figure:
    fig=go.Figure(go.Pie(labels=labels, values=values, hole=0.55))
    fig.update_layout(template='plotly_white', title='Profit Allocation')
    return fig

def fig_eps_vs_myco_margin(eps_margin: float, myco_margin: float)->go.Figure:
    fig=go.Figure()
    fig.add_bar(x=['EPS'], y=[eps_margin], name='EPS €/plate')
    fig.add_bar(x=['Myco'], y=[myco_margin], name='Myco €/plate')
    fig.update_layout(template='plotly_white', barmode='group', title='€/plate Margin: EPS vs Myco', yaxis_title='EUR per plate')
    return fig

def fig_investor_cum_line(df: pd.DataFrame)->go.Figure:
    cum=df['investor_cashflow_y'].cumsum()
    fig=go.Figure(); fig.add_scatter(x=df['year'], y=cum, mode='lines+markers', name='Investor cumulative (€)')
    fig.update_layout(template='plotly_white', title='Investor Cumulative Cashflows', xaxis_title='Year', yaxis_title='EUR')
    return fig
