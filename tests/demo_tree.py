"""Quick demo of build_tree output."""
from hdf5_manager.core.tree import build_tree
import h5py, numpy as np, tempfile, json
from tkinter import filedialog as fd
import os

def select_file():
    filetypes = (
        ('hdf5 files', '*.hdf5'),
        ('All files', '*.*')
    )

    filename = fd.askopenfilename(
        title='Open a file',
        initialdir='/home/dibarra/Documents',
        filetypes=filetypes
    )
    return filename

tmp = select_file()

if not tmp:  # usuario canceló
    print("No file selected. Using temporary example.")
    tmp_file = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
    tmp = tmp_file.name
    tmp_file.close()

    print(f"File path: {tmp}")

    with h5py.File(tmp.name, "w") as f:
        f.create_group("group_a")
        f.create_dataset("dset_1", data=np.array([1, 2, 3]))
        grp = f.create_group("group_b")
        grp.create_dataset("dset_2", data=np.array([[1, 2], [3, 4]]))

    with h5py.File(tmp.name, "r") as f:
        tree = build_tree(f)
        print(json.dumps(tree, indent=2))

    os.unlink(tmp.name)

else:
    print(f"File path: {tmp}")
    with h5py.File(tmp, "r") as f:
        tree = build_tree(f)
        print(tree)