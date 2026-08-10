# Merger — Análisis de opciones (diferido)

Estado: pendiente. Se decidió no implementar esta feature todavía porque el
diseño se estaba complicando (cross-panel drag tiene fricción con el patrón
HTML5 D&D nativo y el PR oficial de NiceGUI para `ui.sortable` aún no está
mergeado).

## Objetivo

Mover grupos HDF5 entre dos archivos (source → destination), con preview
antes de aplicar (igual que el Editor).

## Opciones evaluadas

### Opción A: SortableJS (lo que recomienda la discussion #932)

- **Cómo**: `ui.add_body_html(SortableJS CDN)`, classes `.sortable-source` y
  `.sortable-dest`, emit eventos vía `ui.on("item-dropped")`.
- **Pros**: drag real cross-panel, touch support, animations out-of-the-box.
- **Contras**:
  - NiceGUI no lo expone oficialmente aún (PR #4656 en revisión).
  - Requiere conocer SortableJS.
  - Bundle externo de ~20KB.

```python
ui.add_body_html('''
<script type="module">
import 'https://cdnjs.cloudflare.com/ajax/libs/Sortable/1.15.0/Sortable.min.js';
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sortable-source, .sortable-dest').forEach((el) => {
        Sortable.create(el, {
            group: 'shared',
            animation: 150,
            onEnd: (evt) => emitEvent('item-moved', {
                from: evt.from.id, to: evt.to.id, item: evt.item.dataset.path
            });
        });
    });
});
</script>
''')
```

### Opción B: HTML5 D&D nativo (patrón del ejemplo Trello)

- **Cómo**: subclass `ui.card` con `on('dragstart')`, subclass `ui.column` con
  `on('drop')`. Estado global `dragged` / `target`.
- **Pros**: no necesita librería externa, funciona ya en NiceGUI.
- **Contras**:
  - **Falko (maintainer) admite problemas con dos columnas separadas**:
    "Sadly this somehow does not work for me when I have two columns".
  - No funciona en touch devices (límite de HTML5 D&D).
  - Mucho código custom para cross-panel.

### Opción C: Botón "Add to queue" por card (preview-pattern del Editor)

- **Cómo**: cada card del source tiene un botón que agrega a
  `pending_merges` (lista en `app.storage.user`). Panel lateral muestra los
  pendientes. Apply itera la lista y llama `merge_files()`.
- **Pros**:
  - Reutiliza exactamente el patrón del Editor (preview + apply + restore).
  - Sin librerías externas, sin JavaScript custom.
  - Funciona en touch, funciona siempre.
  - Validación de conflictos al momento de hacer click (más control).
- **Contras**: no es drag visual, es click. Menos "vistoso".

## Recomendación cuando se retome

**Opción C** como MVP. **Opción A** si querés drag visual después de que se
mergee `ui.sortable` en NiceGUI. **Evitar Opción B** porque el maintainer
mismo reporta fricción.

## Estructura final del layout (Opción C)

```
┌─ Merger ──────────────────────────────────────────────────────────────┐
│  Source: [/path/to/exp1.h5] [📁 Browse]                                │
│  Dest:   [/path/to/exp2.h5] [📁 Browse]                                │
│                                                                          │
│  ┌─ Source groups (cards) ─────────────┐  ┌─ Pending merges ────────┐ │
│  │ ┌─batch2_..._00 [Add to queue] ──┐ │  │ • batch2_..._00 → dest   │ │
│  │ ┌─batch2_..._01 [Add to queue] ──┐ │  │ • batch2_..._01 → dest   │ │
│  └────────────────────────────────────┘  └─────────────────────────┘ │
│                                                                          │
│  ☐ Reemplazar si existe                                                │
│                                                                          │
│  [Restore] [Apply]                                                     │
└────────────────────────────────────────────────────────────────────── ┘
```

## Estado de funciones del core necesarias

- `merge_files()` ya existe en `core/operations.py:72`.
- Falta `apply_merges()` que itere una lista de merges y los aplique todos
  antes de cerrar el handle de destino:

```python
# Pendiente en core/operations.py
def apply_merges(
    merges: list[dict],
    overwrite: bool = False,
) -> None:
    """Apply a batch of merges. Group by dest_file to avoid reopening."""
    by_dest = {}
    for m in merges:
        by_dest.setdefault(m["dest_file"], []).append(m)
    for dest_path, dest_merges in by_dest.items():
        with h5py.File(dest_path, "r+") as dest:
            for m in dest_merges:
                with h5py.File(m["source_file"], "r") as src:
                    merge_files(src, m["source_group"], dest, m["dest_parent"])
```

## Referencias

- Discussion NiceGUI #932: https://github.com/zauberzeug/nicegui/discussions/932
- Ejemplo Trello cards: https://github.com/zauberzeug/nicegui/tree/main/examples/trello_cards
- PR NiceGUI #4656 (sortable): https://github.com/zauberzeug/nicegui/pull/4656
