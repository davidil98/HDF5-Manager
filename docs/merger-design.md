# Merger - Diseño y estado

Estado: implementacion inicial.

## Objetivo

Copiar grupos HDF5 desde un archivo source hacia un archivo destination con
preview visual estilo Trello. Los archivos de entrada no se modifican durante
la seleccion ni durante el preview. El resultado se escribe por defecto en
`<destination>-merged.<ext>`.

La primera version permite arrastrar grupos de nivel raiz. Cada tarjeta
incluye sus datasets y subgrupos; los datasets no son arrastrables.

## UX

- La columna izquierda muestra las tarjetas del source.
- La columna derecha muestra el destination y sus grupos como tarjetas.
- Un click en una tarjeta de grupo destination preselecciona el grupo que
  recibira la copia y lo marca visualmente; el destino seleccionado tambien se
  muestra en un label.
- Un click en una tarjeta de grupo source la preselecciona y muestra su ruta;
  cada tarjeta conserva un boton `Add` para confirmar la copia.
- Un click en `Add` crea un registro en `pending_merges`.
- El destination se reconstruye virtualmente despues de cada `Add`.
- Source permanece visible porque el merge es una copia, no un move.
- `Restore` elimina todos los movimientos pendientes.
- Cada movimiento puede eliminarse individualmente desde el panel pending o
  desde el boton de la tarjeta marcada como `pending`.
- `Apply` reemplaza el output solo despues de confirmar si ya existe.

## Estado

El merger usa claves separadas en `app.storage.user`:

- `h5_path` como source global, compartido con Viewer y Editor
- `merger_dest_path`
- `merger_dest_parent`
- `merger_selected_source`
- `merger_output_path`
- `pending_merges`

Los movimientos guardan rutas HDF5 y rutas de archivos, no IDs del DOM:

```python
{
    "source_file": "/data/source.h5",
    "source_path": "/group_a",
    "dest_file": "/data/destination.h5",
    "dest_parent": "/target",
}
```

`core.merge.apply_virtual_merges()` es una funcion pura. Copia el arbol del
source, rebasa las rutas al destination y marca las copias con `pending=True`.
No abre ni modifica archivos.

## Interaccion estable

La primera implementacion intento usar SortableJS con un controller para cada
zona de drop. Cada movimiento refrescaba todo el tablero y recreaba controllers
Vue despues de inicializar el cliente. En native mode esto producia latencia,
desincronizaciones y reinicios.

El Merger usa ahora tarjetas estaticas, seleccion por click y botones `Add`. No
necesita SortableJS, import maps ni JavaScript custom. Esto permite que
cualquier subgroup sea seleccionable sin crear zonas de drop anidadas. Los
datasets son filas normales y no se copian individualmente.

## Core y seguridad

`core.operations.apply_merges()`:

1. Valida todos los source groups y destination parents.
2. Rechaza conflictos de nombre antes de crear el output.
3. Copia destination a un archivo temporal.
4. Aplica todos los merges sobre el temporal.
5. Reemplaza el output atomically al terminar.

El source nunca puede ser el output. Source y destination deben ser archivos
distintos. Los conflictos de nombres HDF5 se rechazan en esta version; el
overwrite del archivo de salida es una decision independiente.

## Limitaciones conocidas

- No hay drag and drop en esta version; la operacion se inicia seleccionando el
  destino, seleccionando el source y pulsando `Add`.
- Los grupos importados en preview no son zonas de drop.
- No se permite copiar datasets individualmente.
- No hay reorder persistente: el arbol del proyecto ordena nombres
  alfabeticamente y el orden de las tarjetas no tiene significado HDF5.
- La prueba automatizada del drag visual requiere una prueba de navegador o
  native mode; el core si tiene cobertura de conflictos y aplicacion atomica.

## Siguiente iteracion

- Medir el tiempo de lectura y preview con archivos grandes.
- Añadir una estrategia explicita para conflictos de nombres si se necesita
  reemplazar grupos existentes.

## Referencias

- Discussion NiceGUI #932: https://github.com/zauberzeug/nicegui/discussions/932
- PR NiceGUI #5855: https://github.com/zauberzeug/nicegui/pull/5855
- Trello cards example: https://github.com/zauberzeug/nicegui/tree/main/examples/trello_cards
