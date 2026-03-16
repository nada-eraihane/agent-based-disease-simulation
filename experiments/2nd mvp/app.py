"""
app.py
======
Two-page Solara simulation app.
Run with:  solara run app.py

PAGE 1 — Floor Plan Setup
    Upload a floor_plan.json exported from floor_plan_editor.html,
    or use the bundled default hospital layout.
    Shows a matplotlib preview of the loaded floor plan.
    "Continue →" moves to page 2.

PAGE 2 — Simulation
    SolaraViz provides Step / Run / Pause / Reset controls and sliders.
    FloorPlanView renders the floor plan + agent positions each tick.
    SIRChart plots Susceptible / Infected / Recovered over time.
    "← Back" returns to page 1 to load a different floor plan.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

import solara
from mesa.visualization import SolaraViz

from model import HospitalModel
from floor_plan_loader import load as fp_load, load_from_string
from agents import State


# ── Module-level state ────────────────────────────────────────────────────────

# Which page is shown. Changing this triggers a re-render of App().
current_page = solara.reactive("setup")   # "setup" | "simulation"

# The processed floor plan dict passed to SimModel on creation.
# Set by the setup page when the user confirms a floor plan.
_floor_plan = solara.reactive(None)

# Path to the default floor plan shipped with the project
_DEFAULT_FP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "floor_plan.json")


# ── Colour tables ─────────────────────────────────────────────────────────────

ROOM_STYLE = {
    "ward":      ("#dbeafe", "#2563eb"),
    "icu":       ("#fee2e2", "#dc2626"),
    "reception": ("#dcfce7", "#16a34a"),
    "corridor":  ("#fef9c3", "#a16207"),
    "staff":     ("#f3e8ff", "#9333ea"),
    "waiting":   ("#e0f2fe", "#0284c7"),
}

AGENT_COLOUR = {
    ("staff",   State.SUSCEPTIBLE): "#1d4ed8",
    ("staff",   State.INFECTED):    "#ef4444",
    ("staff",   State.RECOVERED):   "#16a34a",
    ("patient", State.SUSCEPTIBLE): "#d97706",
    ("patient", State.INFECTED):    "#ef4444",
    ("patient", State.RECOVERED):   "#16a34a",
    ("visitor", State.SUSCEPTIBLE): "#9333ea",
    ("visitor", State.INFECTED):    "#ef4444",
    ("visitor", State.RECOVERED):   "#16a34a",
}

AGENT_MARKER = {"staff": "s", "patient": "o", "visitor": "^"}


# ── Shared drawing helper ─────────────────────────────────────────────────────

def _draw_floor_plan(ax, fp: dict, model=None):
    """
    Draw the floor plan onto a matplotlib Axes.

    Drawing order:
        1. Dark background  — walls / outside space
        2. Room rectangles  — coloured by type
        3. Room name labels
        4. Explicit wall lines
        5. Agent dots       — only if model is provided

    ax.invert_yaxis() matches the editor's coordinate system (y=0 at top).
    """
    ax.set_facecolor("#374151")

    for room in fp["rooms"]:
        fill, stroke = ROOM_STYLE.get(room["type"], ("#f9fafb", "#6b7280"))
        ax.add_patch(mpatches.Rectangle(
            (room["x"], room["y"]), room["w"], room["h"],
            linewidth=1.5, edgecolor=stroke, facecolor=fill, zorder=1,
        ))
        ax.text(
            room["x"] + room["w"] / 2,
            room["y"] + room["h"] / 2,
            room["name"],
            ha="center", va="center", fontsize=6,
            color=stroke, fontweight="bold", zorder=2, clip_on=True,
        )

    for wall in fp["walls"]:
        ax.plot(
            [wall["x1"], wall["x2"]], [wall["y1"], wall["y2"]],
            color="#111827", linewidth=3, solid_capstyle="round", zorder=3,
        )

    if model is not None:
        for agent in model.agents:
            cx, cy = agent.pos
            ax.scatter(
                cx + 0.5, cy + 0.5,
                c=AGENT_COLOUR.get((agent.agent_type, agent.state), "#9ca3af"),
                s=38 if agent.state == State.INFECTED else 22,
                marker=AGENT_MARKER.get(agent.agent_type, "o"),
                zorder=5, linewidths=0.5, edgecolors="white",
            )

    ax.set_xlim(0, fp["width"])
    ax.set_ylim(0, fp["height"])
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")
    ax.get_figure().patch.set_facecolor("#161b22")


# ── Visualisation components ──────────────────────────────────────────────────

def FloorPlanPreview(fp: dict):
    """Renders the floor plan WITHOUT agents — used on the setup page."""
    w, h = fp["width"], fp["height"]
    fig_w = min(9.0, w * 0.18)
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * h / w))
    _draw_floor_plan(ax, fp, model=None)
    fig.tight_layout(pad=0.3)
    solara.FigureMatplotlib(fig)
    plt.close(fig)


def FloorPlanView(model):
    """Renders floor plan + agents. Called by SolaraViz every step."""
    fp = model.floor_plan
    w, h = fp["width"], fp["height"]
    fig_w = min(9.0, w * 0.18)
    fig, ax = plt.subplots(figsize=(fig_w, fig_w * h / w))
    _draw_floor_plan(ax, fp, model=model)
    fig.tight_layout(pad=0.3)
    solara.FigureMatplotlib(fig)
    plt.close(fig)


def SIRChart(model):
    """Line chart of S/I/R counts over simulation steps."""
    df = model.datacollector.get_model_vars_dataframe()
    fig, ax = plt.subplots(figsize=(4, 2.5))
    if not df.empty:
        ax.plot(df.index, df["Susceptible"], color="#1d4ed8", label="S", linewidth=1.5)
        ax.plot(df.index, df["Infected"],    color="#ef4444", label="I", linewidth=1.5)
        ax.plot(df.index, df["Recovered"],   color="#16a34a", label="R", linewidth=1.5)
    ax.set_xlabel("Step", fontsize=7)
    ax.set_ylabel("Agents", fontsize=7)
    ax.tick_params(labelsize=6)
    ax.legend(fontsize=6, loc="upper right")
    ax.set_title("S / I / R over time", fontsize=8)
    fig.tight_layout()
    solara.FigureMatplotlib(fig)
    plt.close(fig)


# ── SimModel ──────────────────────────────────────────────────────────────────

class SimModel(HospitalModel):
    """
    Subclass of HospitalModel that reads _floor_plan.value at creation.
    SolaraViz re-creates this when the user resets or changes a slider,
    so it always picks up the latest confirmed floor plan.
    """
    def __init__(
        self,
        n_staff=10, n_patients=15, n_visitors=10,
        infected_staff=1, infected_patients=2, infected_visitors=0,
        transmission_prob=0.3, recovery_steps=50,
    ):
        super().__init__(
            floor_plan        = _floor_plan.value,
            n_staff           = n_staff,
            n_patients        = n_patients,
            n_visitors        = n_visitors,
            infected_staff    = infected_staff,
            infected_patients = infected_patients,
            infected_visitors = infected_visitors,
            transmission_prob = transmission_prob,
            recovery_steps    = recovery_steps,
        )


model_params = {
    "n_staff":           {"type": "SliderInt",   "label": "Staff",             "value": 10,  "min": 0,   "max": 50,  "step": 1},
    "n_patients":        {"type": "SliderInt",   "label": "Patients",          "value": 15,  "min": 0,   "max": 50,  "step": 1},
    "n_visitors":        {"type": "SliderInt",   "label": "Visitors",          "value": 10,  "min": 0,   "max": 50,  "step": 1},
    "infected_staff":    {"type": "SliderInt",   "label": "Infected staff",    "value": 1,   "min": 0,   "max": 20,  "step": 1},
    "infected_patients": {"type": "SliderInt",   "label": "Infected patients", "value": 2,   "min": 0,   "max": 20,  "step": 1},
    "infected_visitors": {"type": "SliderInt",   "label": "Infected visitors", "value": 0,   "min": 0,   "max": 20,  "step": 1},
    "transmission_prob": {"type": "SliderFloat", "label": "Transmission prob", "value": 0.3, "min": 0.0, "max": 1.0, "step": 0.05},
    "recovery_steps":    {"type": "SliderInt",   "label": "Recovery steps",    "value": 50,  "min": 5,   "max": 200, "step": 5},
}


# ── Page 1: Setup ─────────────────────────────────────────────────────────────

@solara.component
def SetupPage():
    fp_data,  set_fp  = solara.use_state(None)
    error,    set_err = solara.use_state("")

    def use_default():
        try:
            set_fp(fp_load(_DEFAULT_FP))
            set_err("")
        except Exception as exc:
            set_err(f"Could not load default: {exc}")

    def on_file(file_info):
        try:
            content = file_info["data"].decode("utf-8")
            set_fp(load_from_string(content))
            set_err("")
        except Exception as exc:
            set_err(f"Could not parse JSON: {exc}")

    def proceed():
        _floor_plan.set(fp_data)
        current_page.set("simulation")

    with solara.Column(style="padding:28px; min-height:100vh;"):

        solara.HTML(tag="h1", unsafe_innerHTML="⊞ &nbsp; Hospital Simulation",
            style="color:#2f81f7;font-family:monospace;font-size:22px;margin:0 0 4px;")
        solara.HTML(tag="p",
            unsafe_innerHTML="<b>Step 1 of 2</b> &nbsp;·&nbsp; "
                             "<span style='color:#7d8590;'>Design your floor plan in the editor, export the JSON, then upload it here.</span>",
            style="font-size:12px;margin:0 0 28px;")

        with solara.Row(style="gap:24px;align-items:flex-start;flex-wrap:wrap;"):

            # Left panel
            with solara.Column(style="flex:0 0 310px;gap:18px;"):

                with solara.Card("How to use the Floor Plan Editor"):
                    solara.HTML(tag="div", unsafe_innerHTML="""
                        <ol style="font-size:11px;line-height:2.2;padding-left:18px;margin:0;color:#7d8590;">
                          <li>Open <code style='color:#e6edf3;'>floor_plan_editor.html</code> in any browser</li>
                          <li>Draw rooms, corridors, walls and place objects</li>
                          <li>Click <b style='color:#e6edf3;'>Export JSON</b> to download <code style='color:#e6edf3;'>floor_plan.json</code></li>
                          <li>Upload it below, or use the built-in default layout</li>
                        </ol>
                        <div style="margin-top:12px;padding:8px;background:#0d1117;border-radius:6px;border:1px solid #30363d;">
                          <div style="font-size:10px;color:#7d8590;margin-bottom:5px;font-weight:bold;text-transform:uppercase;letter-spacing:.08em;">Walls &amp; Doors</div>
                          <div style="font-size:10px;color:#7d8590;line-height:1.8;">
                            Wall lines drawn in the editor remove cells from walkable space — agents cannot cross them.<br>
                            Door objects placed on a wall re-open that cell, creating a passage agents can walk through.
                          </div>
                        </div>
                    """)

                with solara.Card("Load Floor Plan"):
                    solara.FileDrop(
                        label="Drop floor_plan.json here, or click to browse",
                        on_file=on_file,
                        lazy=False,
                    )
                    solara.HTML(tag="div",
                        unsafe_innerHTML="<div style='text-align:center;color:#7d8590;font-size:11px;margin:10px 0 8px;'>— or —</div>")
                    solara.Button("Use Default Hospital Layout",
                        on_click=use_default, color="primary", style="width:100%;")
                    if error:
                        solara.HTML(tag="p",
                            unsafe_innerHTML=f"<span style='color:#ef4444;font-size:11px;'>⚠ {error}</span>")

                if fp_data is not None:
                    with solara.Card("Floor Plan Stats"):
                        solara.HTML(tag="div", unsafe_innerHTML=f"""
                            <table style="font-size:11px;width:100%;border-collapse:collapse;">
                              <tr style="border-bottom:1px solid #30363d;">
                                <td style="color:#7d8590;padding:4px 0;">Grid size</td>
                                <td style="color:#e6edf3;text-align:right;">{fp_data['width']} × {fp_data['height']}</td>
                              </tr>
                              <tr style="border-bottom:1px solid #30363d;">
                                <td style="color:#7d8590;padding:4px 0;">Rooms</td>
                                <td style="color:#e6edf3;text-align:right;">{len(fp_data['rooms'])}</td>
                              </tr>
                              <tr style="border-bottom:1px solid #30363d;">
                                <td style="color:#7d8590;padding:4px 0;">Walkable cells</td>
                                <td style="color:#e6edf3;text-align:right;">{len(fp_data['walkable'])}</td>
                              </tr>
                              <tr style="border-bottom:1px solid #30363d;">
                                <td style="color:#7d8590;padding:4px 0;">Explicit walls</td>
                                <td style="color:#e6edf3;text-align:right;">{len(fp_data['walls'])}</td>
                              </tr>
                              <tr>
                                <td style="color:#7d8590;padding:4px 0;">Objects</td>
                                <td style="color:#e6edf3;text-align:right;">{len(fp_data['objects'])}</td>
                              </tr>
                            </table>
                        """)

                    solara.Button("Continue to Simulation →",
                        on_click=proceed, color="success",
                        style="width:100%;font-size:13px;margin-top:4px;")

            # Right panel — preview
            with solara.Column(style="flex:1;min-width:320px;"):
                with solara.Card("Floor Plan Preview"):
                    if fp_data is not None:
                        FloorPlanPreview(fp_data)
                    else:
                        solara.HTML(tag="div", unsafe_innerHTML="""
                            <div style="height:300px;display:flex;flex-direction:column;
                                        align-items:center;justify-content:center;color:#374151;">
                              <div style="font-size:52px;margin-bottom:14px;">🏥</div>
                              <div style="font-size:13px;">No floor plan loaded yet</div>
                              <div style="font-size:11px;margin-top:6px;color:#6b7280;">
                                Upload a JSON or use the default layout
                              </div>
                            </div>
                        """)


# ── Page 2: Simulation ────────────────────────────────────────────────────────

@solara.component
def SimulationPage():
    with solara.Row(style="background:#161b22;border-bottom:1px solid #30363d;padding:8px 16px;align-items:center;"):
        solara.Button("← Back to Floor Plan",
            on_click=lambda: current_page.set("setup"),
            text=True, style="color:#7d8590;font-size:12px;")
        solara.HTML(tag="span",
            unsafe_innerHTML="⊞ &nbsp; Hospital Disease Spread Simulation",
            style="color:#2f81f7;font-size:13px;font-weight:bold;font-family:monospace;margin-left:16px;")

    SolaraViz(
        model        = SimModel(),
        components   = [FloorPlanView, SIRChart],
        model_params = model_params,
        name         = "Hospital Disease Spread Simulation",
    )


# ── Root component ────────────────────────────────────────────────────────────

@solara.component
def App():
    if current_page.value == "setup":
        SetupPage()
    else:
        SimulationPage()


page = App()