#include <windows.h>
#include <commctrl.h>
#include <stdio.h>
#include <max.h>
#include <impexp.h>

static HINSTANCE g_instance = NULL;
static int g_controls_initialized = FALSE;

#define GMAX_TEST_EXPORTER_CLASS_ID Class_ID(0x6f1c2d31, 0x4a5b6c7d)

class GmaxTestExporter : public SceneExport
{
public:
    int ExtCount()
    {
        return 1;
    }

    const TCHAR* Ext(int index)
    {
        return index == 0 ? _T("gtest") : _T("");
    }

    const TCHAR* LongDesc()
    {
        return _T("Gmax test scene exporter");
    }

    const TCHAR* ShortDesc()
    {
        return _T("Gmax Test");
    }

    const TCHAR* AuthorName()
    {
        return _T("Gmax SDK Builder");
    }

    const TCHAR* CopyrightMessage()
    {
        return _T("");
    }

    const TCHAR* OtherMessage1()
    {
        return _T("");
    }

    const TCHAR* OtherMessage2()
    {
        return _T("");
    }

    unsigned int Version()
    {
        return 100;
    }

    void ShowAbout(HWND parent)
    {
        MessageBox(
            parent,
            _T("The Gmax test exporter loaded successfully."),
            _T("Gmax Test Exporter"),
            MB_OK | MB_ICONINFORMATION
        );
    }

    int DoExport(
        const TCHAR* output_path,
        ExpInterface* export_interface,
        Interface* max_interface,
        BOOL suppress_prompts,
        DWORD options
    )
    {
        FILE* output;
        INode* root;
        int child_count;

        if (output_path == NULL || max_interface == NULL) {
            return IMPEXP_FAIL;
        }

        output = _tfopen(output_path, _T("wt"));
        if (output == NULL) {
            return IMPEXP_FAIL;
        }

        root = max_interface->GetRootNode();
        child_count = root != NULL ? root->NumberOfChildren() : 0;

        _ftprintf(output, _T("Gmax exporter test\n"));
        _ftprintf(output, _T("Top-level nodes: %d\n"), child_count);
        _ftprintf(output, _T("VERSION_3DSMAX: 0x%08lX\n"), (unsigned long)VERSION_3DSMAX);

        fclose(output);
        return IMPEXP_SUCCESS;
    }
};

class GmaxTestExporterDesc : public ClassDesc
{
public:
    int IsPublic()
    {
        return TRUE;
    }

    void* Create(BOOL loading)
    {
        return new GmaxTestExporter();
    }

    const TCHAR* ClassName()
    {
        return _T("GmaxTestExporter");
    }

    SClass_ID SuperClassID()
    {
        return SCENE_EXPORT_CLASS_ID;
    }

    Class_ID ClassID()
    {
        return GMAX_TEST_EXPORTER_CLASS_ID;
    }

    const TCHAR* Category()
    {
        return _T("Export");
    }
};

static GmaxTestExporterDesc g_exporter_desc;

BOOL WINAPI DllMain(HINSTANCE instance, ULONG reason, LPVOID reserved)
{
    g_instance = instance;

    if (!g_controls_initialized) {
        g_controls_initialized = TRUE;
        InitCustomControls(instance);
        InitCommonControls();
    }

    return TRUE;
}

extern "C" {

__declspec(dllexport) const TCHAR* LibDescription()
{
    return _T("Gmax SDK test exporter");
}

__declspec(dllexport) int LibNumberClasses()
{
    return 1;
}

__declspec(dllexport) ClassDesc* LibClassDesc(int index)
{
    return index == 0 ? &g_exporter_desc : NULL;
}

__declspec(dllexport) ULONG LibVersion()
{
    return VERSION_3DSMAX;
}

}
