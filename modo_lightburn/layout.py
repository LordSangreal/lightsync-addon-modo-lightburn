"""
Arruma a janela principal no jeito do LightBurn:

- ferramentas numa barra vertical à esquerda;
- painel "Cortes / Camadas" fixo à direita, com Laser, Mover, Console e as
  outras abas logo abaixo (no LightSync elas ficam no painel de baixo);
- barra de cores embaixo da área de trabalho: clicar numa cor manda a
  seleção para a camada daquela cor.

Tudo é desfeito em undo(), deixando a janela como era.
"""

import logging

from gi.repository import Gdk, GLib, Gtk

from rayforge.context import get_context
from rayforge.core.group import Group
from rayforge.core.layer import Layer
from rayforge.core.workpiece import WorkPiece
from rayforge.ui_gtk.icons import get_icon

logger = logging.getLogger(__name__)

# Cores da barra de baixo. As primeiras são as que o LightSync já usa nas
# camadas novas, assim as camadas existentes aparecem na barra.
COLORS = [
    "#00ccff", "#ff6600", "#33cc33", "#ffcc00", "#cc3366",
    "#66cccc", "#ff9999", "#9966ff", "#00cc99", "#000000",
    "#0000ff", "#ff0000", "#008000", "#996633", "#ff00ff",
    "#808080", "#00ffff", "#808000", "#000080", "#800080",
]

# Largura inicial do painel da direita (dá para arrastar a divisa)
DOCK_WIDTH = 440
# Altura inicial das abas Laser / Mover / Console
DOCK_PANEL_HEIGHT = 620

# Ordem das abas do painel da direita (nomes internos do LightSync)
_DOCK_ITEMS = ["laser", "controls", "layers", "console", "gcode", "assets"]

_CSS_BASE = """
.lb-tools {
    background-color: @headerbar_bg_color;
    border-right: 1px solid @borders;
    padding: 4px 3px;
}
.lb-tools button { min-width: 30px; min-height: 30px; padding: 2px; }
.lb-dock {
    background-color: @sidebar_bg_color;
    border-left: 1px solid @borders;
}
.lb-dock-title {
    font-weight: bold;
    padding: 6px 10px;
    background-color: @headerbar_bg_color;
    border-bottom: 1px solid @borders;
}
.lb-colors {
    background-color: @headerbar_bg_color;
    border-top: 1px solid @borders;
    padding: 3px 6px;
}
.lb-colors button {
    min-width: 26px;
    min-height: 20px;
    padding: 0;
    margin: 0 1px;
    border-radius: 2px;
    font-size: 9px;
    font-weight: bold;
    box-shadow: none;
}
.lb-colors button.lb-used { box-shadow: inset 0 -3px 0 alpha(white, 0.8); }
.lb-colors button.lb-active { outline: 2px solid @accent_color; outline-offset: 1px; }
"""


def _text_color(hex_color: str) -> str:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "black" if (r * 299 + g * 587 + b * 114) / 1000 > 140 else "white"


def _css() -> str:
    swatches = "".join(
        f".lb-colors button.lb-c{i} {{ background: {c}; color: {_text_color(c)}; }}\n"
        for i, c in enumerate(COLORS)
    )
    return _CSS_BASE + swatches


class _FitHeight(Gtk.Widget):
    """
    Pede a largura que o conteúdo precisa para a altura que ele tem agora.

    O painel de Mover se arruma em coluna quando tem altura sobrando e em
    linha quando não tem; o Gtk.Paned só pergunta a largura sem dizer a
    altura, e aí a resposta é sempre a da linha (larga demais).
    """

    def __init__(self, child):
        super().__init__()
        self._child = child
        self._height = -1
        child.set_parent(self)
        self.set_vexpand(True)

    def release(self):
        child = self._child
        child.unparent()
        self._child = None
        return child

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    def do_measure(self, orientation, for_size):
        if self._child is None:
            return (0, 0, -1, -1)
        if orientation == Gtk.Orientation.HORIZONTAL:
            natural_height = self._child.measure(Gtk.Orientation.VERTICAL, -1)[1]
            for_size = self._height if self._height >= natural_height else -1
        m, n, _, _ = self._child.measure(orientation, for_size)
        return (m, n, -1, -1)

    def do_size_allocate(self, width, height, baseline):
        if self._child is None:
            return
        if height != self._height:
            self._height = height
            GLib.idle_add(self._requeue)
        self._child.allocate(width, height, baseline, None)

    def _requeue(self):
        self.queue_resize()
        return GLib.SOURCE_REMOVE


class _Layout:
    def __init__(self, win):
        self.win = win
        self.provider = None
        self.tools = None
        self.tools_box = None
        self.paned = None
        self.paned_handler = 0
        self.paned_timeout = 0
        self.dock = None
        self.dock_handler = 0
        self.panel_holder = None
        self.colors_bar = None
        self.swatches: list[Gtk.Button] = []
        self.saved_dock_layout = None
        self.doc = None
        self.refresh_id = 0

    # ----- montar -----

    def apply(self):
        win = self.win
        self.provider = Gtk.CssProvider()
        self.provider.load_from_string(_css())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            self.provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
        self._build_tools()
        self._build_dock()
        self._build_colors()

        # O painel da direita agora fica ao lado da área de trabalho, então os
        # botões de visibilidade não precisam mais desviar dele.
        win._get_vis_overlay_margin_end = lambda: 6
        win._apply_right_panel_visibility()

    def _build_tools(self):
        win = self.win
        main_ui_box = win.main_stack.get_child_by_name("main")
        tools = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tools.add_css_class("lb-tools")

        def add(icon, tip, action=None, on_click=None):
            button = Gtk.Button(child=get_icon(icon))
            button.add_css_class("flat")
            button.set_tooltip_text(tip)
            if action:
                button.set_action_name(action)
            if on_click:
                button.connect("clicked", lambda *_: on_click())
            tools.append(button)

        def sep():
            tools.append(Gtk.Separator(margin_top=3, margin_bottom=3))

        panel = win.bottom_panel
        add("sketch-add-symbolic", "Desenhar (retângulo, círculo, linha, texto…)",
            "win.new_sketch")
        add("download-symbolic", "Importar arquivo (Ctrl+I)", "win.import")
        sep()
        add("move-symbolic", "Posicionar o laser: clique na área de trabalho",
            on_click=lambda: panel.click_to_move_btn.emit("clicked"))
        add("crosshairs-symbolic", "Definir a origem: clique na área de trabalho",
            on_click=lambda: panel.click_to_zero_btn.emit("clicked"))
        sep()
        add("flip-horizontal-symbolic", "Espelhar na horizontal (Ctrl+Shift+H)",
            "win.flip-horizontal")
        add("flip-vertical-symbolic", "Espelhar na vertical (Ctrl+Shift+V)",
            "win.flip-vertical")
        add("align-horizontal-center-symbolic", "Centralizar na horizontal",
            "win.align-h-center")
        add("align-vertical-center-symbolic", "Centralizar na vertical",
            "win.align-v-center")
        add("distribute-horizontal-symbolic", "Distribuir na horizontal",
            "win.spread-h")
        add("sketch-array-symbolic", "Matriz (copiar em grade)", "win.array-grid")
        sep()
        add("tabs-equidistant-symbolic", "Adicionar pontes (Ctrl+Tab)",
            "win.add-tabs-equidistant")
        add("clean-symbolic", "Apagar duplicados (Alt+D)",
            "win.delete-duplicates")
        add("test-symbolic", "Teste de material", "win.material_test")

        canvas = win._canvas_overlay
        main_ui_box.remove(canvas)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_vexpand(True)
        box.append(tools)
        box.append(canvas)
        main_ui_box.append(box)
        self.tools = tools
        self.tools_box = box

    def _build_dock(self):
        win = self.win
        right = win._right_pane

        # "Cortes / Camadas" (no LightSync: as etapas de cada camada)
        win._canvas_overlay.remove_overlay(right)
        right.remove_css_class("right-panel-overlay")
        right.set_halign(Gtk.Align.FILL)
        right.set_valign(Gtk.Align.FILL)
        right.set_propagate_natural_height(False)
        cuts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        title = Gtk.Label(label="Cortes / Camadas", xalign=0)
        title.add_css_class("lb-dock-title")
        cuts.append(title)
        cuts.append(right)

        # Abas Laser, Mover, Console... todas juntas, uma de cada vez
        panel = win.bottom_panel
        self.saved_dock_layout = panel.dock_layout.get_layout()
        items = [n for n in _DOCK_ITEMS if panel.dock_layout.get_item(n)]
        items += [n for n in panel.dock_layout.get_item_names() if n not in items]
        panel.dock_layout.apply_layout(
            {"areas": [{"items": items, "active": "controls"}]}
        )
        win.vertical_paned.set_end_child(None)
        if not panel.get_visible():
            action = win.action_manager.actions.get("toggle_bottom_panel")
            if action:
                action.change_state(GLib.Variant.new_boolean(True))

        dock = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        dock.add_css_class("lb-dock")
        dock.set_start_child(cuts)
        self.panel_holder = _FitHeight(panel)
        dock.set_end_child(self.panel_holder)
        dock.set_resize_end_child(False)
        dock.set_shrink_start_child(False)
        dock.set_shrink_end_child(False)

        view = win.view_stack
        win._canvas_overlay.set_child(None)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_start_child(view)
        paned.set_end_child(dock)
        paned.set_resize_end_child(False)
        paned.set_shrink_start_child(False)
        paned.set_shrink_end_child(False)
        win._canvas_overlay.set_child(paned)
        self.paned = paned
        self.paned_handler = paned.connect(
            "notify::max-position", self._on_paned_allocation
        )
        # Enquanto a janela abre os tamanhos mudam algumas vezes; depois
        # disso a divisa fica onde a pessoa deixar.
        self.paned_timeout = GLib.timeout_add_seconds(
            5, self._stop_initial_sizing
        )
        self.dock = dock
        self.dock_handler = dock.connect(
            "notify::max-position", self._on_dock_allocation
        )

    def _on_paned_allocation(self, paned, _pspec):
        # O Gtk divide o espaço pelo tamanho "natural" de cada lado, e o
        # painel de Mover pede bastante; começa com uma largura parecida
        # com a do LightBurn.
        width = paned.get_width()
        if width > DOCK_WIDTH * 2:
            paned.set_position(width - DOCK_WIDTH)

    def _stop_initial_sizing(self):
        self.paned_timeout = 0
        if self.paned_handler:
            self.paned.disconnect(self.paned_handler)
            self.paned_handler = 0
        if self.dock_handler:
            self.dock.disconnect(self.dock_handler)
            self.dock_handler = 0
        return GLib.SOURCE_REMOVE

    def _on_dock_allocation(self, dock, _pspec):
        # Cortes em cima; embaixo, altura para o Mover ficar em coluna
        height = dock.get_height()
        if height < 400:
            return
        dock.set_position(max(220, height - DOCK_PANEL_HEIGHT))

    def _build_colors(self):
        win = self.win
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.add_css_class("lb-colors")
        for i, color in enumerate(COLORS):
            button = Gtk.Button(label=f"{i:02d}")
            button.add_css_class(f"lb-c{i}")
            button.set_tooltip_text(
                "Mandar a seleção para a camada desta cor "
                "(sem seleção: usar esta camada)"
            )
            button.connect("clicked", self._on_color_clicked, i)
            bar.append(button)
            self.swatches.append(button)
        vbox = win._status_overlay.get_parent()
        vbox.insert_child_after(bar, win._status_overlay)
        self.colors_bar = bar

        win.doc_editor.document_changed.connect(self._on_document_changed)
        self._watch_doc()
        self._refresh()

    # ----- barra de cores -----

    def _on_color_clicked(self, button, index):
        win = self.win
        editor = win.doc_editor
        color = COLORS[index]
        items = [
            item for item in win.surface.get_selected_top_level_items()
            if isinstance(item, (WorkPiece, Group))
        ]
        layer = next(
            (l for l in editor.doc.layers if l.color.lower() == color), None
        )
        if layer is None:
            layer = Layer(name=f"C{index:02d}")
            layer.set_color(color)
            material = get_context().material_mgr.get_default_material()
            if material:
                layer.set_stock_material_uid(material.uid)
            editor.layer.add_layer_and_set_active(layer)
        if items:
            editor.layer.move_items_to_layer(items, layer)
            win.surface.select_items(items)
        else:
            editor.layer.set_active_layer(layer)
        self._refresh()

    def _on_document_changed(self, sender, **kwargs):
        self._watch_doc()
        self._schedule_refresh()

    def _on_doc_event(self, sender, **kwargs):
        self._schedule_refresh()

    def _watch_doc(self):
        if self.doc is not None:
            self._unwatch_doc()
        self.doc = self.win.doc_editor.doc
        for signal in (self.doc.updated, self.doc.descendant_updated,
                       self.doc.descendant_added, self.doc.descendant_removed,
                       self.doc.active_layer_changed):
            signal.connect(self._on_doc_event)

    def _unwatch_doc(self):
        for signal in (self.doc.updated, self.doc.descendant_updated,
                       self.doc.descendant_added, self.doc.descendant_removed,
                       self.doc.active_layer_changed):
            signal.disconnect(self._on_doc_event)
        self.doc = None

    def _schedule_refresh(self):
        if not self.refresh_id:
            self.refresh_id = GLib.idle_add(self._refresh)

    def _refresh(self):
        self.refresh_id = 0
        if not self.swatches:
            return GLib.SOURCE_REMOVE
        doc = self.win.doc_editor.doc
        used = {l.color.lower() for l in doc.layers}
        active = doc.active_layer.color.lower() if doc.active_layer else None
        for button, color in zip(self.swatches, COLORS):
            if color in used:
                button.add_css_class("lb-used")
            else:
                button.remove_css_class("lb-used")
            if color == active:
                button.add_css_class("lb-active")
            else:
                button.remove_css_class("lb-active")
        return GLib.SOURCE_REMOVE

    # ----- desfazer -----

    def undo(self):
        win = self.win
        if self.refresh_id:
            GLib.source_remove(self.refresh_id)
            self.refresh_id = 0
        if self.colors_bar is not None:
            win.doc_editor.document_changed.disconnect(self._on_document_changed)
            if self.doc is not None:
                self._unwatch_doc()
            self.colors_bar.get_parent().remove(self.colors_bar)
            self.colors_bar = None
            self.swatches.clear()

        if self.paned is not None:
            if self.paned_timeout:
                GLib.source_remove(self.paned_timeout)
            self._stop_initial_sizing()
            view = win.view_stack
            panel = win.bottom_panel
            right = win._right_pane
            win._canvas_overlay.set_child(None)
            self.paned.set_start_child(None)
            self.dock.set_end_child(None)
            self.panel_holder.release()
            self.panel_holder = None
            right.get_parent().remove(right)
            right.add_css_class("right-panel-overlay")
            right.set_halign(Gtk.Align.END)
            right.set_valign(Gtk.Align.START)
            right.set_propagate_natural_height(True)
            win._canvas_overlay.set_child(view)
            win._canvas_overlay.add_overlay(right)
            win.vertical_paned.set_end_child(panel)
            if self.saved_dock_layout:
                panel.dock_layout.apply_layout(self.saved_dock_layout)
            self.paned = None
            self.dock = None

        if self.tools_box is not None:
            main_ui_box = win.main_stack.get_child_by_name("main")
            canvas = win._canvas_overlay
            self.tools_box.remove(canvas)
            main_ui_box.remove(self.tools_box)
            main_ui_box.append(canvas)
            self.tools_box = None
            self.tools = None

        if "_get_vis_overlay_margin_end" in vars(win):
            del win._get_vis_overlay_margin_end
            win._apply_right_panel_visibility()

        if self.provider is not None:
            Gtk.StyleContext.remove_provider_for_display(
                Gdk.Display.get_default(), self.provider
            )
            self.provider = None


_layout: _Layout | None = None


def apply(main_window):
    global _layout
    _layout = _Layout(main_window)
    try:
        _layout.apply()
    except Exception:
        logger.exception("Modo LightBurn: não deu para montar o layout")
        _layout.undo()
        _layout = None


def undo():
    global _layout
    if _layout is not None:
        _layout.undo()
        _layout = None
