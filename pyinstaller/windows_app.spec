# PyInstaller specification for Windows application.

import os
from pyinstaller_versionfile import create_versionfile

import comet_pqc

# Application configurations
app_root = os.path.abspath(os.path.dirname(comet_pqc.__file__))
app_version = comet_pqc.__version__
app_filename = f"pqc-{app_version}.exe"
app_icon = os.path.join(app_root, "assets", "icons", "pqc.ico")
app_title = "PQC"
app_description = "Process Quality Control for CMS outer tracker"
app_copyright = "Copyright © 2021-2023 HEPHY"
app_organization = "HEPHY"

# Entry point for the application
launcher_code = "from comet_pqc.__main__ import main; main()"

# Data files to be included in the output executable
datas = [
    (os.path.join(app_root, "assets", "icons", "*.svg"), "comet_pqc/assets/icons"),
    (os.path.join(app_root, "assets", "icons", "*.ico"), "comet_pqc/assets/icons"),
    (os.path.join(app_root, "assets", "config", "chuck", "*.yaml"), "comet_pqc/assets/config/chuck"),
    (os.path.join(app_root, "assets", "config", "sequence", "*.yaml"), "comet_pqc/assets/config/sequence"),
    (os.path.join(app_root, "assets", "config", "sample", "*.yaml"), "comet_pqc/assets/config/sample"),
    (os.path.join(app_root, "assets", "schema", "*.yaml"), "comet_pqc/assets/schema"),
]

# Console will be displayed when the application is run
console = False

version_info = os.path.join(os.getcwd(), "version_info.txt")

# Create windows version info
create_versionfile(
    output_file=version_info,
    version=f"{app_version}.0",
    company_name=app_organization,
    file_description=app_description,
    internal_name=app_title,
    legal_copyright=app_copyright,
    original_filename=app_filename,
    product_name=app_title,
)

a = Analysis(
    ["entry_point.py"],
    pathex=[os.getcwd()],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "pyvisa",
        "pyvisa_py",
        "PyQt5.sip",
        "usb",
        "serial",
        "gpib_ctypes",
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
    name=app_filename,
    version=version_info,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=console,
    icon=app_icon,
)
