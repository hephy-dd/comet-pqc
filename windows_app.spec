# PyInstaller specification for creating a windows application

import os
import comet
import comet_pqc
from pyinstaller_versionfile import create_versionfile

version = comet_pqc.__version__
filename = f"pqc-{version}.exe"
console = False

entry_point = "entry_point.pyw"
version_info = "version_info.txt"

# Paths
package_root = os.path.join(os.path.dirname(comet_pqc.__file__))
package_icon = os.path.join(package_root, "assets", "icons", "pqc.ico")

# Create entry point
def create_entrypoint(output_file):
    with open(output_file, "wt") as fp:
        fp.write("from comet_pqc.__main__ import main; main()")

create_entrypoint(output_file=entry_point)

# Create windows version info
create_versionfile(
    output_file=version_info,
    version=f"{version}.0",
    company_name="HEPHY",
    file_description="Process Quality Control for CMS outer tracker",
    internal_name="PQC",
    legal_copyright="Copyright 2021-2023 HEPHY. This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it under certain conditions; see the LICENSE file for details.",
    original_filename=filename,
    product_name="PQC",
)

a = Analysis([entry_point],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        (os.path.join("comet_pqc", "assets", "icons", "*.svg"), os.path.join("comet_pqc", "assets", "icons")),
        (os.path.join("comet_pqc", "assets", "icons", "*.ico"), os.path.join("comet_pqc", "assets", "icons")),
        (os.path.join("comet_pqc", "assets", "config", "chuck", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "chuck")),
        (os.path.join("comet_pqc", "assets", "config", "sequence", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "sequence")),
        (os.path.join("comet_pqc", "assets", "config", "sample", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "sample")),
        (os.path.join("comet_pqc", "assets", "schema", "*.yaml"), os.path.join("comet_pqc", "assets", "schema"))
    ],
    hiddenimports=[
        "pyvisa",
        "pyvisa_py",
        "pyvisa_sim",
        "pyserial",
        "pyusb",
        "PyQt5.sip"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=filename,
    version=version_info,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    icon=package_icon,
)
