# GMax 1.2 SDK and plug-in stamping tool

This directory contains the headers and import libraries needed to build
32-bit C++ plug-ins for GMax 1.2, plus a universal tool that gives the final
linked plug-in the authentication stamp required by the GMax loader.

The stamp is mandatory. A normal Win32 DLL can compile and link correctly,
export every required GMax function, and still produce this message:

```text
DLL <...> failed to initialize.
```

GMax checks the plug-in's PE checksum and a 48-byte cryptographic trailer
before it calls `LoadLibraryExA` or any plug-in export. Run
`stamp_gmax_plugin.py` after the final link to satisfy that check.

## Directory layout

```text
gmax_1.2_SDK\
|-- Include\                  GMax/3ds Max SDK headers
|-- Include\MaxScrpt\         MAXScript SDK headers
|-- Lib\                      Win32 GMax import libraries
|-- cssdk\                    custom-control SDK files
|-- sample plugin\            minimal scene-export plug-in
|-- stamp_gmax_plugin.py      universal GMax 1.2 stamping tool
`-- README.md
```

## Requirements

- Windows 10 or later
- GMax 1.2
- Python 3.8 or later
- A 32-bit Microsoft C++ toolchain; run it from an x86 Native Tools prompt
- Visual Studio 6, 2008, or another compiler compatible with the old SDK ABI

The stamping tool is Windows-only because it uses the same
`ImageHlp.CheckSumMappedFile` API used by the GMax loader.

## Required build settings

Build the final plug-in as Win32/PE32, not x64. Use these settings:

```text
Compiler:
  /LD /MT /GR /DGAME_VER

Include directories:
  <SDK>\Include
  <SDK>\Include\MaxScrpt     only when MAXScript headers are used

Library directory:
  <SDK>\Lib

Linker:
  /MACHINE:X86 /SUBSYSTEM:WINDOWS
```

Important rules:

- Use the static release runtime `/MT`. Do not use `/MD` for a GMax release
  plug-in.
- Define `GAME_VER` so the SDK exposes the GMax ABI and version value.
- Enable RTTI with `/GR`.
- Link against the GMax import libraries in `Lib`, not libraries from another
  3ds Max release.
- Give the output the extension expected by its plug-in superclass, such as
  `.dle`, `.dli`, `.dlm`, `.dlo`, `.dlu`, `.dlt`, `.dlx`, `.bmi`, `.bms`, or
  `.gup`.

Every plug-in DLL must export these exact undecorated C names:

```cpp
extern "C" __declspec(dllexport) const TCHAR* LibDescription();
extern "C" __declspec(dllexport) int LibNumberClasses();
extern "C" __declspec(dllexport) ClassDesc* LibClassDesc(int index);
extern "C" __declspec(dllexport) ULONG LibVersion();
```

`LibVersion()` must return `VERSION_3DSMAX`. A `.def` file is a reliable way
to guarantee that the four export names remain undecorated. `DllMain` must
return `TRUE`. `CanAutoDefer` is optional.

## Build the included sample

Open an x86 Visual Studio Native Tools Command Prompt, then run:

```cmd
cd /d F:\development\steam\emulator_bot\gmax_1.2_SDK
"sample plugin\build_sample.cmd" .
```

The unsigned output is:

```text
sample plugin\build\GmaxTestExporter.dle
```

Check that it is Win32 and exports the four required functions:

```cmd
"sample plugin\check_plugin.cmd" "sample plugin\build\GmaxTestExporter.dle"
```

## Stamp the final plug-in

Stamping is the final build step. By default the tool updates the plug-in in
place:

```powershell
python .\stamp_gmax_plugin.py ".\sample plugin\build\GmaxTestExporter.dle"
```

The tool performs all of the following:

1. Rejects non-PE32 files.
2. Calculates the checksum over the exact bytes GMax authenticates.
3. Writes that value into the PE optional-header checksum field.
4. Generates a new valid GMax 1.2 ElGamal authentication trailer.
5. Appends the 48 hexadecimal trailer bytes.
6. Verifies the finished file before replacing the output.

No donor plug-in is required. The tool works with any GMax PE32 plug-in type
and with plug-ins of any file size.

To keep the unsigned input, provide a separate output path:

```powershell
python .\stamp_gmax_plugin.py unsigned.dle --output signed.dle
```

Multiple plug-ins can be stamped in place in one invocation:

```powershell
python .\stamp_gmax_plugin.py .\build\*.dle .\build\*.dlu .\build\*.dlo
```

If a file already has a valid stamp, the tool leaves it unchanged. Use
`--force` to replace an existing stamp:

```powershell
python .\stamp_gmax_plugin.py --force .\build\MyPlugin.dlu
```

## Verify without changing a file

```powershell
python .\stamp_gmax_plugin.py --verify .\build\MyPlugin.dle
```

A usable stamp reports `VALID`, followed by identical stored and computed
checksums. An invalid result returns a nonzero exit code, so verification can
also be used in a build script or CI job.

## Correct build and installation order

Always use this order:

1. Compile and link the Win32 plug-in.
2. Run `stamp_gmax_plugin.py` on the final linked file.
3. Run `stamp_gmax_plugin.py --verify`.
4. Copy the verified file into one GMax plug-in directory.
5. Start GMax and test the registered class or export format.

Relinking changes the PE checksum and normally removes the overlay trailer.
Therefore every rebuild must be stamped again. Do not run `editbin`, resource
editors, version-resource tools, packers, or binary patchers after stamping;
if the file changes, stamp it again.

## Installing into GMax or RenX

Standard GMax plug-ins commonly go here:

```text
<GMAX>\plugins\
```

A RenX gamepack plug-in commonly goes here:

```text
<GMAX>\gamepacks\Westwood\RenX\Plugins\
```

Use only one active copy of a plug-in with a given `Class_ID`. If the same
plug-in exists in both directories, GMax reports a duplicate class-ID warning
and ignores the later class registration.

For example:

```powershell
Copy-Item ".\sample plugin\build\GmaxTestExporter.dle" `
  "V:\gmax\gamepacks\Westwood\RenX\Plugins\GmaxTestExporter.dle"
```

The RenX shortcut normally launches GMax with the gamepack's INI files:

```text
gmax.exe -a gamepacks\Westwood\RenX\splash.bmp ^
         -i gamepacks\Westwood\RenX\gmax.ini ^
         -p gamepacks\Westwood\RenX\plugin.ini
```

Confirm that the selected `plugin.ini` contains the directory in which the
plug-in was installed.

## Troubleshooting

### `DLL <...> failed to initialize`

First run `--verify`. This message is used when authentication fails or when
`LoadLibraryExA` cannot load the DLL. If the stamp is valid, inspect the DLL's
Win32 dependencies and confirm that it was built with the GMax SDK and `/MT`.

### `DLL <...> is an obsolete version - not loading`

Check the `LibVersion` export. It must return this SDK's `VERSION_3DSMAX`.

### Duplicate class-ID warning

Remove or disable the older duplicate plug-in. Do not install the same class
in both the root and gamepack plug-in directories.

### `Max.h` or `MaxScrpt.h` cannot be found

Add `<SDK>\Include`. For MAXScript extensions, also add
`<SDK>\Include\MaxScrpt`.

### Required exports are missing

Use `dumpbin /exports MyPlugin.dle` and confirm the exact undecorated names
`LibDescription`, `LibNumberClasses`, `LibClassDesc`, and `LibVersion`.

The authentication stamp only gives an otherwise compatible plug-in authority
to reach the Windows loader. It cannot repair a wrong architecture, missing
dependency, incompatible class implementation, duplicate `Class_ID`, or an
incorrect `LibVersion` value.
