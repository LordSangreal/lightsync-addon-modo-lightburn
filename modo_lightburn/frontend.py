"""
Liga o "Modo LightBurn" na janela principal do LightSync.

Arruma a tela no jeito do LightBurn (menus, ferramentas à esquerda, painel
Cortes / Camadas à direita, barra de cores embaixo), troca atalhos de teclado
pelos do padrão LightBurn, usa o tema escuro (se a pessoa não escolheu um tema
nas configurações) e desfaz tudo quando o complemento é desligado.
"""

import logging

from gi.repository import Adw, Gtk

from rayforge.context import get_context
from rayforge.core.hooks import hookimpl

from . import layout, menus
from .shortcuts import LIGHTBURN_SHORTCUTS, REMOVED_SHORTCUTS

logger = logging.getLogger(__name__)

# O que este complemento mudou, para poder desfazer no on_unload
_controller: Gtk.ShortcutController | None = None
_added: list[Gtk.Shortcut] = []
_removed: list[Gtk.Shortcut] = []
_forced_dark = False


def _normalize(trigger: str) -> str:
    parsed = Gtk.ShortcutTrigger.parse_string(trigger)
    return parsed.to_string() if parsed else trigger


def _shortcuts(controller: Gtk.ShortcutController) -> list[Gtk.Shortcut]:
    return [controller.get_item(i) for i in range(controller.get_n_items())]


def _apply_dark_theme():
    """Tema escuro como o do LightBurn, sem passar por cima da escolha da pessoa."""
    global _forced_dark
    if get_context().config.theme not in ("light", "dark"):
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        _forced_dark = True


@hookimpl
def main_window_ready(main_window):
    global _controller
    _apply_dark_theme()
    menus.apply(main_window)
    layout.apply(main_window)
    controller = getattr(main_window.action_manager, "_shortcut_controller", None)
    if controller is None:
        logger.warning("Modo LightBurn: controle de atalhos não encontrado")
        return
    _controller = controller

    # Teclas que vamos usar: tira quem estiver nelas antes (ex.: Ctrl+Shift+H
    # no Rayforge é "distribuir"; no LightBurn é "espelhar na horizontal").
    taken = {_normalize(k) for k in LIGHTBURN_SHORTCUTS} | {
        _normalize(k) for k in REMOVED_SHORTCUTS
    }
    for shortcut in _shortcuts(controller):
        trigger = shortcut.get_trigger()
        if trigger and trigger.to_string() in taken:
            controller.remove_shortcut(shortcut)
            _removed.append(shortcut)

    for keys, action in LIGHTBURN_SHORTCUTS.items():
        trigger = Gtk.ShortcutTrigger.parse_string(keys)
        if trigger is None:
            logger.warning(f"Modo LightBurn: atalho inválido {keys}")
            continue
        shortcut = Gtk.Shortcut.new(trigger, Gtk.NamedAction.new(action))
        controller.add_shortcut(shortcut)
        _added.append(shortcut)

    logger.info(
        f"Modo LightBurn ativo: {len(_added)} atalhos, {len(_removed)} substituídos"
    )


@hookimpl
def on_unload():
    global _forced_dark
    if _forced_dark:
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
        _forced_dark = False
    layout.undo()
    menus.undo()
    if _controller is None:
        return
    for shortcut in _added:
        _controller.remove_shortcut(shortcut)
    for shortcut in _removed:
        _controller.add_shortcut(shortcut)
    _added.clear()
    _removed.clear()
