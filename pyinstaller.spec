import os
import comet_pqc

# Metadata
name = "comet-pqc"
organization = "HEPHY"
version = comet_pqc.__version__
license = "GPLv3"

# Paths
comet_icon = os.path.join(os.path.dirname(comet_pqc.__file__), "assets", "icons", "pqc.ico")

# Windows version info template
version_info = """
VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=({version[0]}, {version[1]}, {version[2]}, 0),
        prodvers=({version[0]}, {version[1]}, {version[2]}, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x4,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo(
            [
            StringTable(
                u'000004b0',
                [StringStruct(u'CompanyName', u'{organization}'),
                StringStruct(u'FileDescription', u'{name}'),
                StringStruct(u'FileVersion', u'{version[0]}.{version[1]}.{version[2]}.0'),
                StringStruct(u'InternalName', u'{name}'),
                StringStruct(u'LegalCopyright', u'{license}'),
                StringStruct(u'OriginalFilename', u'{name}.exe'),
                StringStruct(u'ProductName', u'{name}'),
                StringStruct(u'ProductVersion', u'{version[0]}.{version[1]}.{version[2]}.0'),
                ])
            ]),
        VarFileInfo([VarStruct(u'Translation', [0, 1200])])
    ]
)
"""

# Pyinstaller entry point template
entry_point = """
from comet_pqc import main
if __name__ == "__main__":
    main.main()
"""

# Create pyinstaller entry point
with open("entry_point.pyw", "wt") as f:
    f.write(entry_point)

# Create windows version info
with open("version_info.txt", "wt") as f:
    f.write(version_info.format(
        name=name,
        organization=organization,
        version=version.split("."),
        license=license
    ))

a = Analysis(["entry_point.pyw"],
    pathex=[
      os.getcwd()
    ],
    binaries=[],
    datas=[
        (os.path.join("comet_pqc", "assets", "icons", "*.svg"), os.path.join("comet", "assets", "icons")),
        (os.path.join("comet_pqc", "assets", "icons", "*.ico"), os.path.join("comet", "assets", "icons")),
        (os.path.join("comet_pqc", "assets", "config", "chuck", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "chuck")),
        (os.path.join("comet_pqc", "assets", "config", "sequence", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "sequence")),
        (os.path.join("comet_pqc", "assets", "config", "sample", "*.yaml"), os.path.join("comet_pqc", "assets", "config", "sample")),
        (os.path.join("comet_pqc", "assets", "schema", "*.yaml"), os.path.join("comet_pqc", "assets", "schema"))
    ],
    hiddenimports=[
        "pyvisa",
        "pyvisa-py",
        "pyvisa-sim",
        "PyQt5.sip"
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=name,
    version="version_info.txt",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=comet_icon,
)
