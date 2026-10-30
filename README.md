# Modo LightBurn para o LightSync

Complemento que deixa o LightSync familiar para quem vem do LightBurn: a tela
fica arrumada do mesmo jeito e as teclas de atalho são as mesmas. Funções que o LightSync já tem passam a
responder às mesmas teclas do LightBurn; atalhos que no LightBurn fazem outra
coisa são retirados para não confundir.

Este complemento não usa código, ícones, imagens nem textos do LightBurn. As
combinações de teclas seguem a lista pública de atalhos do LightBurn
(https://docs.lightburnsoftware.com/Hotkeys.html). LightBurn é marca da
LightBurn Software; o LightSync não tem relação com a empresa.

## Tela

- **Menus** na ordem do LightBurn: Arquivo, Editar, Ferramentas, Organizar,
  Ferramentas Laser, Janela, Ajuda.
- **Ferramentas à esquerda**, numa barra vertical: desenhar, importar,
  posicionar o laser, definir a origem, espelhar, centralizar, distribuir,
  matriz, pontes, apagar duplicados e teste de material.
- **Painel Cortes / Camadas à direita**, fixo, com as etapas da camada ativa.
  Logo abaixo ficam as abas Laser, Mover, Camadas, Console, G-code e
  Biblioteca (no LightSync normal elas ficam no painel de baixo). A divisa
  entre a área de trabalho e o painel pode ser arrastada.
- **Barra de cores embaixo**: clique numa cor para mandar o que está
  selecionado para a camada daquela cor. Se a camada ainda não existe, ela é
  criada (C00, C01…). Sem nada selecionado, a cor só vira a camada ativa. A
  cor da camada ativa fica contornada e as cores que já têm camada ficam com
  um risco embaixo. Ctrl+Z desfaz.

## Tema

Usa o tema escuro, parecido com o do LightBurn, a menos que você tenha escolhido
um tema claro ou escuro em Configurações. Ao desligar o complemento, volta ao tema do sistema.

Ao desligar o complemento, a tela também volta a ser como era.

## Atalhos desta versão

| Teclas | Função |
| --- | --- |
| Alt+X | Exportar |
| Alt+D | Apagar duplicados |
| Alt+J | Juntar caminhos |
| Alt+B | Separar (quebrar) |
| Ctrl+Tab | Adicionar pontes (tabs) |
| Ctrl+Shift+H / Ctrl+Shift+V | Espelhar na horizontal / vertical |
| Alt+← → ↑ ↓ | Alinhar à esquerda, direita, topo, base |
| Alt+PgUp / Alt+PgDn | Alinhar centros |
| Alt+L | Levar o laser até o ponto |
| Pause | Pausar o trabalho |
| Ctrl+Break | Parar o trabalho |

Ctrl+E (Exportar no Rayforge, Elipse no LightBurn) fica sem função neste modo.

## Licença

MIT
