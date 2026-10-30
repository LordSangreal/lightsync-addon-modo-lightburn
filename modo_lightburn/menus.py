"""
Menus na mesma ordem do LightBurn:
Arquivo, Editar, Ferramentas, Organizar, Ferramentas Laser, Janela, Ajuda.

Os submenus originais são reaproveitados (não copiados), então itens que o
LightSync atualiza sozinho, como "Abrir recente" e "Macros", continuam
funcionando.
"""

import logging

from gi.repository import Gio

logger = logging.getLogger(__name__)

# Ordem dos menus no LightSync (Rayforge)
_ORIGINAL = ["file", "edit", "view", "object", "arrange", "tools", "machine",
             "help"]

_main_window = None


def _submenus(menu: Gio.Menu) -> list[Gio.MenuModel | None]:
    return [menu.get_item_link(i, "submenu") for i in range(menu.get_n_items())]


def apply(main_window):
    global _main_window
    original = main_window.menu_model
    links = _submenus(original)
    if len(links) < len(_ORIGINAL) or any(
        link is None for link in links[: len(_ORIGINAL)]
    ):
        logger.warning("Modo LightBurn: menus diferentes do esperado")
        return
    m = dict(zip(_ORIGINAL, links))

    tools = Gio.Menu()
    tools.append_section(None, m["object"])
    tools.append_section(None, m["tools"])

    menu = Gio.Menu()
    menu.append_submenu("_Arquivo", m["file"])
    menu.append_submenu("_Editar", m["edit"])
    menu.append_submenu("_Ferramentas", tools)
    menu.append_submenu("_Organizar", m["arrange"])
    menu.append_submenu("Ferramentas _Laser", m["machine"])
    menu.append_submenu("_Janela", m["view"])
    # Menus que outros complementos criarem ficam antes da Ajuda
    for i in range(len(_ORIGINAL), original.get_n_items()):
        menu.append_item(Gio.MenuItem.new_from_model(original, i))
    menu.append_submenu("Aj_uda", m["help"])

    main_window.menubar.set_menu_model(menu)
    _main_window = main_window


def undo():
    global _main_window
    if _main_window is not None:
        _main_window.menubar.set_menu_model(_main_window.menu_model)
        _main_window = None
