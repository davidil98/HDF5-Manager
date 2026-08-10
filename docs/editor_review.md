# Editor tab — code review notes

File: `src/hdf5_manager/web_gui/editor.py` (343 lines)
Date: 2026-08-10

---

## 1. The dual-checkbox bug (`apply_new` ↔ "Reemplazar si existe")

### What is actually happening

The two checkboxes are **the same boolean** with two different labels.

```python
# editor.py:96-98 — top checkbox
apply_new = ui.checkbox("Apply changes in a new file").bind_value(
    app.storage.user, "apply_to_new_file"
)

# editor.py:195 — bottom checkbox, bound to the OBJECT above (not a separate key)
ui.checkbox("Reemplazar si existe").bind_value(checkbox, "value")
```

`bind_value(checkbox, "value")` ties the second checkbox to the **Python object**
of the first one. NiceGUI resolves the binding by reference, so both check/uncheck
together. Two labels, one boolean.

### How `_apply_changes()` uses it (lines 295-308)

| `apply_to_new_file` | Behavior | `output`              | `overwrite`     |
|---------------------|----------|-----------------------|-----------------|
| `False` (default)   | Overwrite source in place | `source` (original) | `True` (forced) |
| `True`              | Write to user-selected `output_path` | `app.storage.user["output_path"]` | `reemplazar` flag |

### Why this is confusing

- The two labels mean different things in natural language: *"save to a new file?"*
  vs *"overwrite the destination if it exists?"*.
- The flow's actual semantics: if "new file" is checked, the destination usually
  **does not exist yet**, so a separate "overwrite if exists" toggle makes little sense.
- `core/operations.py:138-141` already raises `FileExistsError` when the output
  exists and `overwrite=False`, which justifies the safety flag — but only if it
  were a real, independent control.

**Diagnosis confirmed:** one of the two checkboxes should disappear, or they
should become two independent flags with conditional visibility.

---

## 2. Rename: full path vs. last segment — is it safe?

### Short answer

Internally: **`path` = full HDF5 path**, **`new_name` = leaf only**. The code joins
them correctly. **It is safe** and will not corrupt paths.

### How the pending change is built (line 232)

```python
pending.append({"action": "rename", "path": node, "new_name": new_name})
```

- `node` ← `app.storage.user["selected_node"]` → **absolute path**
  (e.g. `/data/signals/raw`)
- `new_name` ← the `ui.input` text → **only the new name**
  (e.g. `raw_renamed`)

### Safety validations (lines 217-230)

1. `new_name` cannot be empty.
2. `"/"` cannot appear in `new_name` — prevents path injection via the input.
3. `node` cannot be `"/"` — the root group is not renameable.

### How the virtual tree rewrites the id (lines 50-64)

```python
parent = "/".join(path.split("/")[:-1])          # "/data/signals"
node["id"] = f"{parent}/{new_name}" if parent else f"/{new_name}"
# → "/data/signals/raw_renamed"
```

Separating `parent` + `new_name` prevents any `/` injection through user input.

### Children rebase (lines 67-75)

```python
if node["id"].startswith(old_parent + "/"):
    node["id"] = new_parent + node["id"][len(old_parent):]
```

**Important detail — done correctly:** the `old_parent + "/"` check avoids the
classic string-prefix bug where `"/group1"` would also match `"/group10"`.

### How it lands on disk (`core/operations.py:12-26`)

```python
parent_path, _old_name = os.path.split(path)   # ("/data/signals", "raw")
h5file[parent_path].move(path, new_name)        # h5py moves within the parent
```

h5py's `move()` handles descendants internally. **No risk of corrupting existing
paths** because `move()` operates on the full absolute path.

### Summary

| Aspect                    | Status        |
|---------------------------|---------------|
| `path` is absolute        | ✓ correct     |
| `new_name` is leaf only   | ✓ correct     |
| `/` rejected in `new_name`| ✓ line 221-223|
| Root rename rejected      | ✓ line 228-230|
| Children rebase prefix bug| ✓ avoided     |
| Disk-level move           | ✓ via h5py    |

**No changes needed in the rename logic.** The architecture is robust.

---

## 3. Proposed fix options for the UX

### Option A — Recommended (minimal)

- Delete the top "Apply changes in a new file" checkbox.
- Delete the bottom "Reemplazar si existe" duplicate.
- Replace the output section with a single `ui.input` + picker button, always visible,
  bound to `app.storage.user["output_path"]`.
- Keep a single independent checkbox `Overwrite if exists` bound to a new key
  `app.storage.user["output_path_overwrite"]`.
- In `_apply_changes()`, if `output_path` is empty → autocompletion with the
  source path from `app.storage.user["h5_path"]`.

### Option B — Keep the "in-place vs new file" idea

- Keep the top checkbox, rename to something clear (e.g. *"Save as a new file"*
  / *"Save to a different file"*).
- **Separate the bindings**: top → `app.storage.user["apply_to_new_file"]`,
  bottom → `app.storage.user["output_overwrite"]`.
- Wrap the output block in `@ui.refreshable` and refresh on change of the top
  checkbox, showing/hiding with `set_visibility()` or a conditional inside the
  function.
- When `apply_to_new_file` is `False`, hide the entire output block and
  internally default to `source`.

### Option C — Hybrid (cleanest)

- Delete the top checkbox and the duplicate.
- The output section is always visible, with two implicit modes:
  - **Empty `output_path`** → "in-place" mode (overwrites the original,
    overwrite flag is implicitly `True`).
  - **Filled `output_path`** → "new file" mode (the `Overwrite if exists`
    checkbox applies only here).
- This removes one UI control and the confusion without losing functionality.

### Additional suggestions (independent of option chosen)

- Move `output_input` and the (kept) checkbox state to unique keys in
  `app.storage.user` to prevent the double-binding bug class entirely.
- i18n: translate "Reemplazar si existe" → "Overwrite if exists". Decide whether
  to translate all labels to English or introduce an i18n dictionary (the file
  already mixes English comments and Spanish labels inconsistently).

---

## 4. Open questions before implementation

1. **Which option (A, B, or C)?** C is the cleanest; A is the most minimal.
2. **Keep in-place overwrite as a default**, or force an explicit output path?
3. **Translate all labels to English**, or introduce i18n?
4. Should the editor tab read `h5_path` directly from `app.storage.user` for the
   "no output path filled → overwrite original" case? (Yes, that's how it
   already works in `_apply_changes`.)

---

## 5. Files involved

| File                                      | Role                                  |
|-------------------------------------------|---------------------------------------|
| `src/hdf5_manager/web_gui/editor.py`      | Editor tab UI + pending-change queue  |
| `src/hdf5_manager/core/operations.py`     | `apply_changes()` + `rename_node()`   |
| `src/hdf5_manager/core/tree.py`           | `build_tree()` (used by viewer/editor)|
| `src/hdf5_manager/web_gui/main_window.py` | Toolbar; owns `h5_path`               |

`tree.py` and `operations.py` are zero-GUI; the changes would be **UI-only** in
`editor.py` (and possibly `main_window.py` if you choose Option B/C and want to
reuse the source path label).
