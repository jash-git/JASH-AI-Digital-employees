---
name: system-drawing-to-imagesharp
description: Migrate System.Drawing.Common to SixLabors.ImageSharp, removing libgdiplus dependency for cross-platform compatibility. Covers Bitmap loading, Base64 conversion, ZXing barcode generation, and Graphics.DrawImage bridge patterns.
tags: [csharp, refactoring, imagesharp, system-drawing, vpos-avalonia]
---

# System.Drawing.Common → SixLabors.ImageSharp Migration

## Scope
Migrate `System.Drawing` API usage to `SixLabors.ImageSharp`, removing the `System.Drawing.Common` NuGet package. This eliminates the `libgdiplus` dependency for cross-platform compatibility (Linux/macOS).

## File Categorization

Before starting, inventory all System.Drawing usage:
```bash
grep -rn "System\.Drawing" VPOS_Avalonia/ --include="*.cs" | grep -v "^Binary"
```

Categorize each file into one of five groups:

| Category | Description | Action |
|----------|-------------|--------|
| **A** | Unused `using System.Drawing.*;` only | Delete the line |
| **B** | `new Bitmap(path)` for loading images | Replace with `ImageSharp.Image.Load()` |
| **C** | Base64 ↔ Image conversion functions | Full refactor (see below) |
| **D** | ZXing barcode generator | Add ImageSharp-returning bridge methods |
| **E** | Windows-only tools (`Graphics.MeasureString`, DPI) | Keep System.Drawing |

## Step-by-step procedure

### Category A: Remove unused using directives
```diff
-using System.Drawing.Imaging;
-using System.Drawing.Printing;
```

### Category B: Replace Bitmap loading
```diff
-System.Drawing.Bitmap bitmap = new System.Drawing.Bitmap(path);
+SixLabors.ImageSharp.Image bitmap = SixLabors.ImageSharp.Image.Load(path);
```

If the caller uses `Graphics.DrawImage(bitmap, rect)` (System.Drawing.Graphics), convert ImageSharp→Bitmap:
```csharp
using SixLabors.ImageSharp.Image imgSharp = BitmapBuf;
using System.Drawing.Bitmap bmpForDraw = new System.Drawing.Bitmap(imgSharp.Width, imgSharp.Height);
using var tempStream = new MemoryStream();
imgSharp.Save(tempStream, new SixLabors.ImageSharp.Formats.Bmp.BmpEncoder());
tempStream.Position = 0;
bmpForDraw.LoadFromStream(tempStream);
g.DrawImage(bmpForDraw, rect);
```

### Category C: Refactor Base64 ↔ Image conversion

**Image2Base64String**: Change parameter from `Bitmap` to `ImageSharp.Image`:
```csharp
// Before:
public static string Image2Base64String(Bitmap bmp) {
    MemoryStream ms = new MemoryStream();
    bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Jpeg);
    byte[] arr = new byte[ms.Length];
    ms.Position = 0;
    ms.Read(arr, 0, (int)ms.Length);
    return Convert.ToBase64String(arr);
}

// After:
public static string Image2Base64String(SixLabors.ImageSharp.Image image) {
    using MemoryStream ms = new MemoryStream();
    image.Save(ms, new SixLabors.ImageSharp.Formats.Jpeg.JpegEncoder());
    return Convert.ToBase64String(ms.ToArray());
}
```

**Base64String2Image**: Change return type from `Bitmap` to `ImageSharp.Image`:
```csharp
// Before:
public static Bitmap Base64String2Image(string strbase64) {
    byte[] arr = Convert.FromBase64String(strbase64);
    MemoryStream ms = new MemoryStream(arr);
    Bitmap bmp = new Bitmap(ms);
    return bmp;
}

// After:
public static SixLabors.ImageSharp.Image Base64String2Image(string strbase64) {
    byte[] arr = Convert.FromBase64String(strbase64);
    using MemoryStream ms = new MemoryStream(arr);
    return SixLabors.ImageSharp.Image.Load(ms);
}
```

### Category D: Handle ZXing barcode generator

ZXing.Windows.Compatibility still returns `System.Drawing.Bitmap`. Strategy: **keep original methods for backward compatibility, add ImageSharp-returning variants**:

```csharp
// Keep original (backward compat):
public static Bitmap QrCode(String StrData, String ErrorCorrection = "H") { ... }

// New ImageSharp variant:
public static SixLabors.ImageSharp.Image QrCodeToImageSharp(String StrData, String ErrorCorrection = "H") {
    var barcodeWriter = new BarcodeWriter();
    // ... same options as original ...
    Bitmap bmp = barcodeWriter.Write(StrData);
    return ConvertBitmapToImageSharp(bmp);  // helper below
}

// Helper: System.Drawing.Bitmap → ImageSharp.Image
private static SixLabors.ImageSharp.Image ConvertBitmapToImageSharp(Bitmap bmp) {
    using var ms = new MemoryStream();
    bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
    ms.Position = 0;
    return SixLabors.ImageSharp.Image.Load(ms);
}
```

For saving barcodes to file (replacing `bmp.Save("file.bmp", ImageFormat.Bmp)`):
```csharp
using var ms = new MemoryStream();
using var img = SixLabors.ImageSharp.Image.Load((System.Drawing.Bitmap)barcodeBitmap.Clone());
img.Save(ms, new SixLabors.ImageSharp.Formats.Bmp.BmpEncoder());
File.WriteAllBytes("qrcode.bmp", ms.ToArray());
```

### Category E: Preserve System.Drawing for Windows-only tools

Files like `DPI_Funs.cs` that use `Graphics.FromHwnd()`, `Bitmap(1,1)` + `Graphics.MeasureString()` should **keep** `using System.Drawing;`. These are Windows-specific and have no ImageSharp equivalent.

### Final step: Remove NuGet package reference
Delete from `.csproj`:
```diff
-<PackageReference Include="System.Drawing.Common" Version="..." />
```

## Pitfalls
- **ImageSharp.Image is not disposable in the same way** — use `using` blocks or let GC handle it for short-lived images. For long-lived images, call `image.Dispose()` when done.
- **Base64 data URIs**: If input contains `data:image/png;base64,...`, strip the prefix first: `strbase64.Split(',')[1]`.
- **ImageSharp.Image.Load() throws** on invalid images — always wrap in try/catch for user-provided paths/Base64.
- **ZXing.Windows.Compatibility is Windows-only** — if targeting Linux, use ZXing.Net with a different writer (e.g., `BarcodeWriterPixelData` → SkiaSharp).
- **ImageSharp does NOT have Graphics.MeasureString()** — text measurement requires SkiaSharp or keeping System.Drawing for DPI tools.
- **Do NOT remove System.Drawing.Common from csproj if any file still uses it** (DPI_Funs, CS_PrintTemplate for Font/Graphics/Brush, Barcode_Funs for ZXing). Only remove when all remaining usages are in files that will keep the package.

## Verification Checklist (DoD)
1. `grep "System\.Drawing" BitmapBase64_Funs.cs` → no `using System.Drawing;` (DPI_Funs.cs excepted)
2. `grep "SixLabors\.ImageSharp" BitmapBase64_Funs.cs` → has using declarations
3. `grep "System\.Drawing\.Common" *.csproj` → not found
4. All callers of refactored methods use correct types (e.g., `ImageSharp.Image` instead of `Bitmap`)

## Ad-hoc Verification Script Pattern
Write a `/tmp/hermes-verify-*.sh` script:
```bash
#!/usr/bin/env bash
BASE="/path/to/project"
PASS=0; FAIL=0
ok() { PASS=$((PASS+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); echo "  ❌ $1"; }

# Category A: unused using removals
! grep -q "^using System\.Drawing\." "$BASE/Target.cs" && ok "No System.Drawing using" || fail "Still has System.Drawing using"

# Category C: method signatures
grep -q "Image2Base64String(SixLabors\.ImageSharp\.Image" "$BASE/BitmapBase64_Funs.cs" && ok "Correct param type" || fail "Wrong param type"
grep -q "SixLabors\.ImageSharp\.Image Base64String2Image" "$BASE/BitmapBase64_Funs.cs" && ok "Correct return type" || fail "Wrong return type"

# csproj: package removed
! grep -q "System\.Drawing\.Common" "$BASE/VPOS_Avalonia.csproj" && ok "PackageReference removed" || fail "Still has PackageReference"

echo "RESULT: $PASS passed, $FAIL failed"
exit "$FAIL"
```
