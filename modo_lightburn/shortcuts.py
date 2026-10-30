"""
Atalhos de teclado no padrão de quem vem do LightBurn.

Cada entrada liga uma combinação de teclas a uma ação que já existe no
LightSync/Rayforge. As combinações seguem a lista pública de atalhos do
LightBurn (docs.lightburnsoftware.com/Hotkeys.html); só entram aqui funções
que o LightSync já tem.
"""

# tecla (formato GTK) -> ação da janela
LIGHTBURN_SHORTCUTS: dict[str, str] = {
    # Arquivo
    "<Alt>x": "win.export",
    # Editar
    "<Alt>d": "win.delete-duplicates",
    "<Alt>j": "win.join-paths",
    # Ferramentas de vetor
    "<Alt>b": "win.break-apart",
    "<Control>Tab": "win.add-tabs-equidistant",
    # Organizar
    "<Control><Shift>h": "win.flip-horizontal",
    "<Control><Shift>v": "win.flip-vertical",
    "<Alt>Left": "win.align-left",
    "<Alt>Right": "win.align-right",
    "<Alt>Up": "win.align-top",
    "<Alt>Down": "win.align-bottom",
    "<Alt>Page_Up": "win.align-h-center",
    "<Alt>Page_Down": "win.align-v-center",
    # Máquina
    "<Alt>l": "win.move-head-here",
    "Pause": "win.machine-hold",
    "<Control>Break": "win.machine-cancel",
}

# Atalhos do Rayforge que, no LightBurn, fazem outra coisa. São retirados
# para não surpreender quem está migrando (ex.: Ctrl+E é Elipse no LightBurn).
REMOVED_SHORTCUTS: set[str] = {
    "<Control>e",
}
