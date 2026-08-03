# Test exporter

`GmaxTestExporter.cpp` is deliberately written in old C++ syntax so it can be
compiled by Visual Studio 2008.

Build it from an x86 Visual Studio command prompt:

```cmd
build_sample.cmd ..\output\gmax12-sdk
```

Verify the architecture and required exports:

```cmd
check_plugin.cmd build\GmaxTestExporter.dle
```

The exporter adds a `.gtest` scene-export format. Exporting writes the number
of top-level scene nodes and the SDK version value into a text file.

This sample is intentionally small. It tests:

- SDK header compatibility
- import-library compatibility
- `GAME_VER`
- `VERSION_3DSMAX`
- 32-bit linking
- required Gmax plug-in exports
- `SceneExport` registration
