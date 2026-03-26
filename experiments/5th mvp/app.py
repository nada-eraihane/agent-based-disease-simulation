import solara
from .ui.state import current_page
from .ui.home import HomePage
from .ui.settings import SettingsPage
from .ui.simulation import SimulationPage


@solara.component
def Page():
    page = current_page.value

    if page == "home":
        HomePage()
    elif page == "settings":
        SettingsPage()
    elif page == "simulation":
        SimulationPage()
    else:
        HomePage()
