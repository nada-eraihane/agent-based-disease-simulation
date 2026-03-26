# simulation Settings
#
# has sliders for agent numbers, infection param, sim speed...
#
import solara
from .state import (
    current_page, sim_params,
    model_instance, sim_running, sim_paused, sim_tick, sim_results,
)
from ..floorplan import load_predefined
from ..model import HospitalModel


def _update_param(key, value):
    """Update a single simulation parameter."""
    p = sim_params.value.copy()
    p[key] = value
    sim_params.set(p)


@solara.component
def SettingsPage():
    error_msg, set_error_msg = solara.use_state("")

    p = sim_params.value
    solara.Style("""
        .v-input .v-label {
            color: #17048c !important;
        }
        .v-input .v-messages {
            color: #17048c !important;
        }
        .v-input input {
            color: #17048c !important;
        }
    """)

    with solara.Column(style={"min-height": "100vh", "background": "#e2eeff", "padding": "20px"}):
        # Top bar
        with solara.Row(
            style={
                "background": "#17048c",
                "padding": "16px 32px",
                "align-items": "center",
                "border-radius": "12px",
            }
        ):
            solara.Button(
                label="← Home",
                on_click=lambda: current_page.set("home"),
                style={
                    "text-transform": "bold",
                    "color": "#17048c",
                    "background": "#d3e65c",
                },
            )
            solara.HTML(
                tag="span",
                unsafe_innerHTML='<span style="font-size:20px; font-weight:700; color:#F8FAFC;">Simulation Settings</span>',
            )

        # Two-column layout
        with solara.Row(style={
            "gap": "24px",
            "flex-wrap": "wrap",
            "background": "transparent",
        }):
            # Left column — parameter sliders
            with solara.Column(
                style={
                    "flex": "1",
                    "min-width": "350px",
                    "background": "#b1d2ff",
                    "border-radius": "12px",
                    "padding": "24px",
                    "color": "#ffffff",
                }
            ):
                solara.HTML(
                    tag="h3",
                    unsafe_innerHTML='<span style="color:#17048c; font-weight:600;">Agent Counts</span>',
                )

                solara.SliderInt(
                    label="Patients",
                    value=p["num_patients"],
                    min=1, max=100,
                    on_value=lambda v: _update_param("num_patients", v),
                )
                solara.SliderInt(
                    label="Doctors",
                    value=p["num_doctors"],
                    min=1, max=50,
                    on_value=lambda v: _update_param("num_doctors", v),
                )
                solara.SliderInt(
                    label="Nurses",
                    value=p["num_nurses"],
                    min=1, max=70,
                    on_value=lambda v: _update_param("num_nurses", v),
                )
                solara.SliderInt(
                    label="Visitors",
                    value=p["num_visitors"],
                    min=0, max=60,
                    on_value=lambda v: _update_param("num_visitors", v),
                )
                solara.SliderInt(
                    label="Cleaners",
                    value=p["num_cleaners"],
                    min=0, max=30,
                    on_value=lambda v: _update_param("num_cleaners", v),
                )
                solara.SliderInt(
                    label="Volunteers",
                    value=p["num_volunteers"],
                    min=0, max=20,
                    on_value=lambda v: _update_param("num_volunteers", v),
                )
                solara.SliderInt(
                    label="Initially Infected",
                    value=p["initially_infected"],
                    min=1, max=100,
                    on_value=lambda v: _update_param("initially_infected", v),
                )

                solara.HTML(
                    tag="h3",
                    unsafe_innerHTML='<span style="color:#17048c; font-weight:600; margin-top:16px;">Disease Parameters</span>',
                )

                solara.SliderFloat(
                    label="Infection Rate",
                    value=p["infection_rate"],
                    min=0.01, max=1.0, step=0.01,
                    on_value=lambda v: _update_param("infection_rate", v),
                )
                solara.SliderFloat(
                    label="Infection Radius",
                    value=p["infection_radius"],
                    min=5.0, max=50.0, step=1.0,
                    on_value=lambda v: _update_param("infection_radius", v),
                )
                solara.SliderFloat(
                    label="Recovery Rate",
                    value=p["recovery_rate"],
                    min=0.005, max=0.2, step=0.005,
                    on_value=lambda v: _update_param("recovery_rate", v),
                )
                #hardcoded sliders and boxes
                solara.Checkbox(
                    label="SEIR Mode (Incubation Period)",
                    value=p.get("use_seir", False),
                    on_value=lambda v: None,
                )
                if p.get("use_seir", False):
                    solara.SliderInt(
                        label="Incubation Duration (ticks)",
                        value=p.get("incubation_duration", 30),
                        min=5, max=100,
                        on_value=lambda v: None,
                    )

                solara.SliderFloat(
                    label="Contamination Decay Rate",
                    value=p.get("contamination_decay_rate", 0.01),
                    min=0.001, max=0.1, step=0.001,
                    on_value=lambda v: None,
                )
                solara.SliderFloat(
                    label="Surface Infection Prob.",
                    value=p.get("contamination_infection_prob", 0.05),
                    min=0.01, max=0.3, step=0.01,
                    on_value=lambda v: _update_param("contamination_infection_prob", v),
                )

                solara.HTML(
                    tag="h3",
                    unsafe_innerHTML='<span style="color:#17048c; font-weight:600; margin-top:16px;">Simulation Control</span>',
                )

                solara.SliderInt(
                    label="Simulation Speed (ticks/s)",
                    value=p["sim_speed"],
                    min=1, max=60,
                    on_value=lambda v: _update_param("sim_speed", v),
                )
                solara.SliderInt(
                    label="Max Steps",
                    value=p["max_steps"],
                    min=100, max=5000, step=100,
                    on_value=lambda v: _update_param("max_steps", v),
                )
                solara.SliderInt(
                    label="Random Seed",
                    value=p["random_seed"],
                    min=0, max=9999,
                    on_value=lambda v: _update_param("random_seed", v),
                )

            # Right column — interventions + floor plan
            with solara.Column(
                style={
                    "flex": "1",
                    "min-width": "350px",
                    "gap": "20px",
                    "background": "transparent",
                }
            ):
                
                with solara.Column(
                    style={
                        "background": "#b1d2ff",
                        "border-radius": "12px",
                        "padding": "24px",
                    }
                ):
                    solara.HTML(
                        tag="h3",
                        unsafe_innerHTML='<span style="color:#17048c; font-weight:600;">Intervention Parameters</span>',
                    )
                    solara.SliderFloat(
                        label="Hand Hygiene Effectiveness",
                        value=p.get("hand_hygiene_effectiveness", 0.6),
                        min=0.0, max=1.0, step=0.05,
                        on_value=lambda v: None,
                    )
                    solara.SliderFloat(
                        label="Cleaner Efficiency",
                        value=p.get("cleaner_efficiency", 0.5),
                        min=0.1, max=1.0, step=0.05,
                        on_value=lambda v:  None,
                    )
                    solara.SliderFloat(
                        label="Visitor Spawn Rate",
                        value=p.get("visitor_spawn_rate", 0.02),
                        min=0.0, max=0.1, step=0.005,
                        on_value=lambda v:  None,
                    )

                #select floor plan card
                with solara.Column(
                    style={
                        "background": "#b1d2ff",
                        "border-radius": "16px",
                        "padding": "24px",
                    }
                ):
                    solara.HTML(
                        tag="h3",
                        unsafe_innerHTML='<span style="color:#17048c; font-weight:600;">Floor Plan</span>',
                    )

                    #hardcoded layout simple 
                    solara.HTML(
                        tag="div",
                        unsafe_innerHTML='<div style="color:#17048c; font-size:14px; padding:8px 0;">Layout: <b>Simple Hospital</b></div>',
                    )

                   
                    solara.HTML(
                        tag="div",
                        unsafe_innerHTML='<div style="color:#17048c; font-size:14px; margin:8px 0;">Or upload a custom floor plan JSON:</div>',
                    )

                    #file drop
                    solara.HTML(
                        tag="div",
                        unsafe_innerHTML="""
                        <div style="
                            border: 2px dashed #17048c; border-radius:12px; padding:24px;
                            text-align:center; color:#17048c; font-size:13px; opacity:0.5;
                        ">
                            📁 Drop floor plan JSON here<br/>
                            
                        </div>
                        """,
                    )

                    solara.Button(
                        label="Design Your Own Floor Plan",
                        on_click=lambda: "floorplaneditor.html",  
                        style={
                            "margin-top": "12px",
                            "text-transform": "none",
                            "width": "100%",
                            "background": "#d3e65c",
                            "color": "#17048c",
                            "opacity": "0.5",
                        },
                    )
               
                # Run button
                def run_simulation():
                    p = sim_params.value.copy()
                    fp = load_predefined("simple")
                    model = HospitalModel(p, fp)
                    model_instance.set(model)
                    sim_tick.set(0)
                    sim_running.set(True)
                    sim_paused.set(False)
                    sim_results.set(None)
                    current_page.set("simulation")

                solara.Button(
                    label="▶  Run Simulation",
                    on_click=run_simulation,
                    color="#cb6ce6",
                    style={
                        "width": "100%",
                        "height": "56px",
                        "font-size": "18px",
                        "font-weight": "700",
                        "border-radius": "14px",
                        "text-transform": "none",
                    },
                )
