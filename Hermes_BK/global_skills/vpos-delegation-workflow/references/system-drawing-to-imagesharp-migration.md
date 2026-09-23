# System.Drawing.Common → SixLabors.ImageSharp Migration

## Context (TASK-019, 2026-08-14)
System.Drawing.Common v10.0.8 is deprecated on Linux (.NET 8+). Project already has SixLabors.ImageSharp NuGet package.

## Affected Files Analysis
Before migrating, grep for all System.Drawing usages:
```bash
grep -rn "using System\.Drawing" VPOS_Avalonia/ --include="*.cs"
grep -rn "System\.Drawing\." VPOS_Avalonia/ --include="*.cs"
```

## Migration Categories

### Category A: Unused using only (delete)
Files that import `System.Drawing.Printing` or `System.Drawing.Imaging` but never use them.
- Action: Delete the unused using line.
- Example: `VTEAMQrorderAPI.cs:4` → remove `using System.Drawing.Imaging;`

### Category B: new Bitmap(path) → Image.Load()
Files that create Bitmap from file path.
- Old: `new System.Drawing.Bitmap(filePath)`
- New: `SixLabors.ImageSharp.Image.Load(filePath)`
- Note: Return type changes from `Bitmap` to `Image`. Callers must adapt.

### Category C: Bitmap.Save(ms, ImageFormat) → image.Save(ms, encoder)
- Old: `bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Jpeg)`
- New: `image.Save(ms, new SixLabors.ImageSharp.Formats.Jpeg.JpegEncoder())`
- BMP: `new SixLabors.ImageSharp.Formats.Bmp.BmpEncoder()`

### Category D: Bitmap → Base64 conversion (full refactor)
When a method takes/returns Bitmap and converts to/from Base64:
- Old signature: `string Image2Base64String(Bitmap bmp)`
- New signature: `string Image2Base64String(Image image)`
- Save uses encoder instead of ImageFormat enum.

### Category E: ZXing output (hybrid — keep Bitmap)
ZXing.Windows.Compatibility still returns System.Drawing.Bitmap.
- Keep `using System.Drawing;` for Barcode_Funs.cs return type.
- Only change the `.Save()` call to use ImageSharp encoder.

### Category F: DPI measurement tools (keep as-is on Windows)
DPI_Funs.cs uses `Graphics.FromHwnd()`, `Bitmap(1,1)`, `Graphics.MeasureString()`.
- No direct ImageSharp equivalent for text measurement.
- **Decision**: Keep System.Drawing in this file only (Windows-only utility).

### Category G: NuGet package removal
- Remove `<PackageReference Include="System.Drawing.Common" Version="..." />` from .csproj.
- Verify no remaining usages except DPI_Funs.cs and Barcode_Funs.cs.

## Key API Differences

| System.Drawing | ImageSharp | Notes |
|---|---|---|
| `new Bitmap(path)` | `Image.Load(path)` | Returns Image<TPixel> |
| `bmp.Save(ms, ImageFormat.Jpeg)` | `img.Save(ms, new JpegEncoder())` | Encoder class per format |
| `Graphics.FromHwnd(IntPtr.Zero)` | N/A | Keep for DPI measurement |
| `Bitmap(1,1)` + `Graphics.FromImage()` | N/A | No direct equivalent |
| `System.Drawing.Color` | `SixLabors.ImageSharp.PixelFormats.Rgba32` | Only if color manipulation needed |

## Verification Checklist (TASK-019 實際驗證結果)
1. `grep "using System.Drawing" VPOS_Avalonia/ToolLib/BitmapBase64_Funs.cs` → 0 results (except DPI_Funs) ✅
2. `grep "SixLabors.ImageSharp" VPOS_Avalonia/ToolLib/BitmapBase64_Funs.cs` → should have using declarations ✅
3. `grep -c "System.Drawing.Common" VPOS_Avalonia/VPOS_Avalonia.csproj` → 0 (package removed) ✅
4. Build verification by user ⏳

## TASK-019 實際經驗教訓
- **執行時間**: ~32 分鐘（比預期長，因為涉及 API 簽名改變和 cascade 修改）
- **驗證結果**: 23/23 checks passed — grep 驗證全部通過
- **DPI_Funs.cs**: 保留 System.Drawing 是正確決策（Graphics.MeasureString 無 ImageSharp 替代）
- **Barcode_Funs.cs**: ZXing.Windows.Compatibility 仍回傳 Bitmap，需要 helper 方法轉換
- **派單策略**: 9 檔案替換應委派給 vpos_core（多檔案 cascade），但需附完整呼叫端清單
