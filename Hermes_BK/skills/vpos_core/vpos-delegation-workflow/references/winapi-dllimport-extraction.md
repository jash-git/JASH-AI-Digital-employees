# WinAPI DllImport 提取模式 (WinApiHelper.cs)

## 適用場景
單一 .axaml.cs 檔案包含多個 `[DllImport]` extern 方法，需要提取至獨立 ToolLib 類別。

## 實例：TASK-013c (2026-08-10)
- **來源**: VPOS_Avalonia/Views/MainWindow.axaml.cs (lines 41-71)
- **提取內容**: 6 個 DllImport extern + 4 個常數 (SW_RESTORE, WM_LBUTTONDOWN, etc.)

## 產出結構 (VPOS_Avalonia/ToolLib/WinApiHelper.cs)
```csharp
using System;
using System.Runtime.InteropServices;

namespace VPOS_Avalonia.ToolLib
{
    public static class WinApiHelper
    {
        // ── Constants ──────────────────────────────────────────────
        public const int SW_RESTORE = 9;
        public const uint WM_LBUTTONDOWN = 0x0201;
        public const uint WM_LBUTTONUP = 0x0202;
        public const int MK_LBUTTON = 0x0001;

        // ── user32.dll ─────────────────────────────────────────────
        [DllImport("user32.dll", SetLastError = true)]
        public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        // ... etc.
    }
}
```

## 交付前強制驗證 (Definition of Done)
1. `ls -la VPOS_Avalonia/ToolLib/WinApiHelper.cs` — 確認檔案存在且有內容
2. `grep "public static extern\|private static extern" VPOS_Avalonia/Views/MainWindow.axaml.cs | wc -l` — 應該為 0 (所有 DllImport 已移除)
3. `grep "WinApiHelper\." VPOS_Avalonia/Views/MainWindow.axaml.cs | wc -l` — 應該 > 0 (有使用 WinApiHelper 引用)

## 注意事項
- 常數也一併提取，不要留在 MainWindow.axaml.cs
- namespace 改為 `VPOS_Avalonia.ToolLib`（與 ToolLib 其他類別一致）
- 保留原有的 XML comments
- 所有呼叫端改為 `WinApiHelper.MethodName()` 格式
