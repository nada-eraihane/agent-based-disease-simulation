# simulation page
#
# shows the simulation running, with a sidebar for live controls and stats
#
import solara
import time
import threading
from .state import (
    current_page, sim_params, model_instance,
    sim_running, sim_paused, sim_tick, sim_results,
)
from ..agents import HospitalAgent, AGENT_SHAPES, STATUS_COLOURS, Status


def _agent_shape_svg(shape: str, cx: float, cy: float, r: float, fill: str) -> str:
    if shape == "circle":
        return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="#0F172A" stroke-width="1"/>'
    elif shape == "diamond":
        pts = f"{cx},{cy-r} {cx+r},{cy} {cx},{cy+r} {cx-r},{cy}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="#0F172A" stroke-width="1"/>'
    elif shape == "square":
        return f'<rect x="{cx-r}" y="{cy-r}" width="{r*2}" height="{r*2}" fill="{fill}" stroke="#0F172A" stroke-width="1" rx="1"/>'
    elif shape == "triangle_up":
        pts = f"{cx},{cy-r} {cx+r},{cy+r*0.7} {cx-r},{cy+r*0.7}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="#0F172A" stroke-width="1"/>'
    elif shape == "triangle_down":
        pts = f"{cx-r},{cy-r*0.7} {cx+r},{cy-r*0.7} {cx},{cy+r}"
        return f'<polygon points="{pts}" fill="{fill}" stroke="#0F172A" stroke-width="1"/>'
    elif shape == "hexagon":
        import math
        pts = " ".join(
            f"{cx + r * math.cos(math.radians(60*i - 30))},"
            f"{cy + r * math.sin(math.radians(60*i - 30))}"
            for i in range(6)
        )
        return f'<polygon points="{pts}" fill="{fill}" stroke="#0F172A" stroke-width="1"/>'
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'


def _render_floor_plan_svg(model, width=720, height=500) -> str:
    if model is None:
        return f'<svg width="{width}" height="{height}"><text x="{width//2}" y="{height//2}" fill="#94A3B8" text-anchor="middle">No simulation loaded</text></svg>'

    fp = model.floor_plan
    sx = width / fp.width
    sy = height / fp.height
    scale = min(sx, sy) * 0.92
    ox = (width - fp.width * scale) / 2
    oy = (height - fp.height * scale) / 2

    def tx(x): return ox + x * scale
    def ty(y): return oy + y * scale

    parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" '
             f'style="background:#0F172A; border-radius:12px;">']

    parts.append(f'<rect x="{tx(0)}" y="{ty(0)}" width="{fp.width*scale}" height="{fp.height*scale}" '
                 f'fill="#1a2332" rx="4"/>')

    for room in fp.rooms:
        pts = " ".join(f"{tx(p[0])},{ty(p[1])}" for p in room.polygon)
        parts.append(f'<polygon points="{pts}" fill="#1E293B" stroke="#334155" stroke-width="1.5"/>')
        cx = sum(p[0] for p in room.polygon) / len(room.polygon)
        cy = sum(p[1] for p in room.polygon) / len(room.polygon)
        parts.append(f'<text x="{tx(cx)}" y="{ty(cy)}" fill="#64748B" font-size="9" '
                     f'text-anchor="middle" dominant-baseline="middle" font-family="monospace">{room.name}</text>')

    for w_start, w_end in fp.walls:
        parts.append(f'<line x1="{tx(w_start[0])}" y1="{ty(w_start[1])}" '
                     f'x2="{tx(w_end[0])}" y2="{ty(w_end[1])}" '
                     f'stroke="#475569" stroke-width="2.5" stroke-linecap="round"/>')

    for door in fp.doors:
        dx, dy = door.position
        parts.append(f'<circle cx="{tx(dx)}" cy="{ty(dy)}" r="10" fill="red" opacity="0.2"/>')

    living = model._living_agents()
    for agent in living:
        if agent.pos is None:
            continue
        ax, ay = agent.pos
        fill = STATUS_COLOURS.get(agent.status, "#888")
        shape = AGENT_SHAPES.get(agent.agent_type, "circle")
        r = 5
        svg_shape = _agent_shape_svg(shape, tx(ax), ty(ay), r, fill)
        parts.append(svg_shape)

    parts.append('</svg>')
    return "\n".join(parts)


def _render_sir_chart_svg(sir_history, width=260, height=130) -> str:
    # if not sir_history:
    #     return f'<svg width="{width}" height="{height}"><text x="{width//2}" y="{height//2}" fill="#64748B" text-anchor="middle" font-size="11">Waiting for data...</text></svg>'

    max_tick = max(h["tick"] for h in sir_history) or 1
    max_count = max(max(h["S"], h["I"], h["R"]) for h in sir_history) or 1
    pad = 28
    cw = width - pad * 2
    ch = height - pad * 2

    def px(tick): return pad + (tick / max_tick) * cw
    def py(count): return pad + ch - (count / max_count) * ch

    parts = [f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    parts.append(f'<rect width="{width}" height="{height}" fill="#0F172A" rx="8"/>')
    parts.append(f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{pad+ch}" stroke="#334155" stroke-width="1"/>')
    parts.append(f'<line x1="{pad}" y1="{pad+ch}" x2="{pad+cw}" y2="{pad+ch}" stroke="#334155" stroke-width="1"/>')

    for series, colour in [("S", "#22C55E"), ("I", "#EF4444"), ("R", "#9CA3AF")]:
        points = " ".join(f"{px(h['tick'])},{py(h[series])}" for h in sir_history)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{colour}" stroke-width="1.5" opacity="0.8"/>')

    parts.append(f'<circle cx="{pad+5}" cy="10" r="3" fill="#22C55E"/><text x="{pad+12}" y="13" fill="#94A3B8" font-size="8">S</text>')
    parts.append(f'<circle cx="{pad+28}" cy="10" r="3" fill="#EF4444"/><text x="{pad+35}" y="13" fill="#94A3B8" font-size="8">I</text>')
    parts.append(f'<circle cx="{pad+51}" cy="10" r="3" fill="#9CA3AF"/><text x="{pad+58}" y="13" fill="#94A3B8" font-size="8">R</text>')

    parts.append('</svg>')
    return "\n".join(parts)


def _legend_html() -> str:
    return """
    <div style="background:#0F172A; border-radius:8px; padding:10px; border:1px solid #334155; margin-top:12px;">
        <div style="font-size:11px; font-weight:600; color:#F8FAFC; margin-bottom:8px;">Map Key</div>
        <div style="font-size:10px; color:#94A3B8; margin-bottom:6px; font-weight:600;">Agent Shapes:</div>
        <div style="display:flex; flex-wrap:wrap; gap:6px 12px; margin-bottom:10px;">
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><circle cx="7" cy="7" r="5" fill="#9CA3AF" stroke="#0F172A" stroke-width="1"/></svg>Patient
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><polygon points="7,2 12,7 7,12 2,7" fill="#9CA3AF" stroke="#0F172A" stroke-width="1"/></svg>Doctor
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><rect x="2" y="2" width="10" height="10" fill="#9CA3AF" stroke="#0F172A" stroke-width="1" rx="1"/></svg>Nurse
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><polygon points="7,2 12,11 2,11" fill="#9CA3AF" stroke="#0F172A" stroke-width="1"/></svg>Visitor
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><polygon points="2,5 12,5 7,13" fill="#9CA3AF" stroke="#0F172A" stroke-width="1"/></svg>Cleaner
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <svg width="14" height="14"><polygon points="7,2 11,4.5 11,9.5 7,12 3,9.5 3,4.5" fill="#9CA3AF" stroke="#0F172A" stroke-width="1"/></svg>Volunteer
            </span>
        </div>
        <div style="font-size:10px; color:#94A3B8; margin-bottom:6px; font-weight:600;">Status Colours:</div>
        <div style="display:flex; gap:12px;">
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <span style="width:10px; height:10px; border-radius:50%; background:#22C55E; display:inline-block;"></span>Susceptible
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <span style="width:10px; height:10px; border-radius:50%; background:#EF4444; display:inline-block;"></span>Infected
            </span>
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <span style="width:10px; height:10px; border-radius:50%; background:#9CA3AF; display:inline-block;"></span>Recovered
            </span>
        </div>
        <div style="margin-top:8px;">
            <span style="display:flex; align-items:center; gap:4px; font-size:10px; color:#CBD5E1;">
                <span style="width:6px; height:6px; border-radius:50%; background:#F97316; display:inline-block;"></span>Door
            </span>
        </div>
    </div>
    """


@solara.component
def SimulationPage():
    model = model_instance.value
    tick = sim_tick.value
    running = sim_running.value
    paused = sim_paused.value

    live_speed, set_live_speed = solara.use_state(sim_params.value.get("sim_speed", 10))

    def run_loop():
        m = model_instance.value
        if m is None:
            return
        while m.running and sim_running.value:
            if sim_paused.value:
                time.sleep(0.1)
                continue
            m.step()
            sim_tick.set(m.tick_count)
            spd = max(1, live_speed)
            time.sleep(1.0 / spd)
        sim_running.set(False)
        if m:
            sim_results.set(m.get_results())

    thread_started, set_thread_started = solara.use_state(False)
    if running and not thread_started and model is not None:
        set_thread_started(True)
        t = threading.Thread(target=run_loop, daemon=True)
        t.start()

    with solara.Column(style={"min-height": "100vh", "background": "#e2eeff", "padding": "20px"}):
        with solara.Row(
            style={"background": "#17048c", "padding": "12px 24px",
                   "border-radius": "12px", "align-items": "center", "gap": "16px"}
        ):
            solara.HTML(tag="span",
                unsafe_innerHTML=f'<span style="font-size:20px; font-weight:700; color:#F8FAFC;">Simulation — Tick {tick}</span>')
            solara.HTML(tag="span",
                unsafe_innerHTML=f'<span style="font-size:14px; color:{"#d3e65c" if running and not paused else "#cb6ce6"};">{"● Running" if running and not paused else "● Paused" if paused else "● Stopped"}</span>')

        with solara.Row(style={"flex": "1", "gap": "16px", "margin-top": "16px", "background": "transparent"}):
            # Left sidebar
            with solara.Column(
                style={"width": "300px", "min-width": "300px", "background": "#b1d2ff",
                       "padding": "16px", "border-radius": "12px",
                       "overflow-y": "auto",}
            ):
                solara.HTML(tag="div",
                    unsafe_innerHTML='<div style="font-weight:600; color:#17048c; margin-bottom:8px; font-size:14px;">Parameters</div>')
                if model:
                    p = model.p
                    recap = (
                        f"Patients: {p['num_patients']} | Doctors: {p['num_doctors']} | Nurses: {p['num_nurses']}<br/>"
                        f"Visitors: {p['num_visitors']} | Cleaners: {p['num_cleaners']}<br/>"
                        f"Floor Plan: {model.floor_plan.name}"
                    )
                    solara.HTML(tag="div",
                        unsafe_innerHTML=f'<div style="color:#17048c; font-size:11px; line-height:1.6; margin-bottom:12px; padding:8px; background:#e2eeff; border-radius:8px;">{recap}</div>')

                solara.HTML(tag="div",
                    unsafe_innerHTML='<div style="font-weight:600; color:#17048c; margin-bottom:8px; font-size:14px;">Live Controls</div>')

                solara.SliderInt(label="Speed (ticks/s)", value=live_speed, min=1, max=60, on_value=set_live_speed)

                with solara.Row(style={"gap": "8px", "margin": "12px 0", "background": "transparent"}):
                    if not paused:
                        solara.Button(label="⏸ Pause", on_click=lambda: sim_paused.set(True), color= "#cb6ce6", style={"text-transform": "none", "flex": "1", "color": "#17048c"})
                    else:
                        solara.Button(label="▶ Resume", on_click=lambda: sim_paused.set(False), color="#d3e65c", style={"text-transform": "none", "flex": "1", "color": "#17048c"})

                    def _step_once():
                        m = model_instance.value
                        if m and m.running:
                            sim_paused.set(True)
                            m.step()
                            sim_tick.set(m.tick_count)

                    solara.Button(label="⏭ Step", on_click=_step_once, color= "#cb6ce6", style={"text-transform": "none", "flex": "1", "color": "#17048c"})

                def _stop():
                    sim_running.set(False)
                    sim_paused.set(False)
                    m = model_instance.value
                    if m:
                        m.running = False
                        sim_results.set(m.get_results())

                solara.Button(label="⏹ Stop", on_click=_stop, color="#d3e65c",
                    style={"text-transform": "none", "width": "100%", "margin-bottom": "12px", "color": "#17048c"})

                solara.HTML(tag="div",
                    unsafe_innerHTML='<div style="font-weight:600; color:#17048c; margin-bottom:8px; font-size:14px;">SIR Curve</div>')
                sir_data = model.sir_history if model else []
                chart_svg = _render_sir_chart_svg(sir_data, width=280, height=130)
                solara.HTML(tag="div", unsafe_innerHTML=chart_svg)

                solara.HTML(tag="div", unsafe_innerHTML=_legend_html())

            # Main visualisation area
            with solara.Column(
                style={"flex": "1", "padding": "16px", "display": "flex",
                       "align-items": "center", "justify-content": "center",
                       "background": "#b1d2ff", "border-radius": "12px"}
            ):
                svg = _render_floor_plan_svg(model, width=720, height=500)
                solara.HTML(tag="div", unsafe_innerHTML=svg)
