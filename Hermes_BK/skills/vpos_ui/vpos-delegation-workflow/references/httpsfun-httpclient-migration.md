# HttpsFun.cs HttpClient 遷移記錄 (TASK-007a~d)

## 背景
- **檔案**: `VPOS_Avalonia/ToolLib/HttpsFun.cs` (1086行)
- **問題**: #7同步阻塞、#8淘汰HttpWebRequest、#9request.Abort()不安全、#10無Timeout、#12無效Thread.Sleep(100)
- **嚴重度**: HIGH

## 呼叫方分析
| 檔案 | 呼叫次數 | API |
|------|----------|-----|
| `SyncDBData.cs` | ~40處 | RESTfulAPI_get |
| `SyncThread.cs` | ~10處 | RESTfulAPI_postBody |
| `App.axaml.cs`, `MainWindow.axaml.cs`, 其他Views | 各1~5處 | GET/POST |

## 修改策略 — 保持同步 signature (關鍵)

**核心原則**: 不改變 public API signature，所有呼叫端不需修改。內部改用 HttpClient + `.GetAwaiter().GetResult()`。

### Step 1: _httpClient Timeout 初始化 (TASK-007a)
```csharp
// 修改前
private static readonly HttpClient _httpClient = new HttpClient();

// 修改後
private static readonly HttpClient _httpClient = new HttpClient()
{
    Timeout = TimeSpan.FromSeconds(30)
};
```

### Step 2: RESTfulAPI_get 重構 (TASK-007b) — 3個overload
```csharp
public static String RESTfulAPI_get(String StrDomain, String path, String StrInput, ...)
{
    String url = StrDomain + path;
    if (StrInput.Length > 0) { url += "/" + HttpUtility.UrlEncode(StrInput); }

    try
    {
        // ✅ 正確：使用 HttpRequestMessage 支援自訂 Header
        var request = new HttpRequestMessage(HttpMethod.Get, url);
        if (StrHeaderName.Length > 0 && StrHeaderValue.Length > 0)
            request.Headers.Add(StrHeaderName, StrHeaderValue);

        var response = _httpClient.SendAsync(request).GetAwaiter().GetResult();

        if (!response.IsSuccessStatusCode)
        {
#if DEBUG
            LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + response.StatusCode);
#endif
            return response.StatusCode.ToString();
        }

        String StrData = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
#if DEBUG
        LogFile.Write("HttpsNormal ; RESTfulAPI_get (" + url + "): " + StrData);
#endif
        return StrData;
    }
    catch (Exception e)
    {
        LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + e.Message);
        return "";
    }
}
```

**移除項目**: Thread.Sleep(100), request.Abort(), HttpRequestCachePolicy, ServicePointManager.DefaultConnectionLimit
**保留項目**: #if DEBUG Log 區塊、URL 建構邏輯（UrlEncode）、try-catch 結構

### ⚠️ TASK-007b 實戰教訓 (2026-08-10)
子代理初次修改時遺漏了 `setHeader()` Header 支援，改用 `_httpClient.GetAsync(url)` 導致所有呼叫端無法傳送 Authorization。修復方式：改用 `HttpRequestMessage` + `_httpClient.SendAsync(request)`。

**派單必附提醒**: "注意需支援自訂 Header（如 Authorization: Basic ***），使用 HttpRequestMessage + SendAsync，勿用 GetAsync。"
{
    String url = StrDomain + path;
    if (StrInput.Length > 0) { url += "/" + HttpUtility.UrlEncode(StrInput); }

    try
    {
        var response = _httpClient.GetAsync(url).GetAwaiter().GetResult();
        
        if (!response.IsSuccessStatusCode)
        {
#if DEBUG
            LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + response.StatusCode);
#endif
            return response.StatusCode.ToString();
        }

        String StrData = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
#if DEBUG
        LogFile.Write("HttpsNormal ; RESTfulAPI_get (" + url + "): " + StrData);
#endif
        return StrData;
    }
    catch (Exception e)
    {
        LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + e.Message);
        return "";
    }
}
```

**移除項目**: Thread.Sleep(100), request.Abort(), HttpRequestCachePolicy, ServicePointManager.DefaultConnectionLimit

### Step 3: RESTfulAPI_postBody 重構 (TASK-007c) — 5個overload
同上模式，差異在 POST body 使用 `_httpClient.PostAsync(url, new StringContent(StrInput, Encoding.UTF8, "application/json"))`。

## 驗證檢查清單
1. `grep -n "Timeout = TimeSpan" HttpsFun.cs` → L157: Timeout = TimeSpan.FromSeconds(30)
2. `grep -n "GetAwaiter().GetResult()" HttpsFun.cs` → 確認所有呼叫點保留
3. `grep -n "HttpWebRequest\|HttpWebResponse" HttpsFun.cs` → RESTfulAPI_get/postBody 中應為 0
4. `ls -la HttpsFun.cs` → 確認時間戳記最新

## 執行順序
1. TASK-007a: _httpClient Timeout (2處方法)
2. TASK-007b: RESTfulAPI_get (3個overload, ~150行×3)
3. TASK-007c: RESTfulAPI_postBody (5個overload, ~100行×5)
4. TASK-007d: WebRequestTest() + setHeader() 微調

## 風險評估
- **低**: HttpClient 行為與 HttpWebRequest 略有差異（如 header 設定方式），但所有呼叫端只讀取回傳 String，不受影響。
- **中**: Thread.Sleep(100) 移除後可能增加網路負載，但實際上是「建立連線前」的無效等待，移除後應改善效能。

## CS0136 陷阱（重要）
`#if DEBUG` 區塊內若有多處 `String StrLog = String.Format(...)` 宣告會觸發 CS0136（同一方法範圍內同名變數）。

**修復方式**: inline `LogFile.Write()`，不宣告中間變數。

```csharp
// ❌ 錯誤：兩個地方都宣告 StrLog
#if DEBUG
    String StrLog = String.Format("RESTfulAPI_get ({0}): {1}", url, StrData);
    LogFile.Write("HttpsError ; " + StrLog);
#endif
...
#if DEBUG
    String StrLog = String.Format("RESTfulAPI_get ({0}): {1}", url, StrData);  // CS0136!
    LogFile.Write("HttpsNormal ; " + StrLog);
#endif

// ✅ 正確：直接 inline
#if DEBUG
    LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + StrData);
#endif
...
#if DEBUG
    LogFile.Write("HttpsNormal ; RESTfulAPI_get (" + url + "): " + StrData);
#endif
```

## 回報原則（使用者偏好）
- 只在 Task 完成（QA PASS）或失敗時回報最終結果。
- 不要在每個 micro-task dispatch、verify、patch 時都回報，除非使用者主動問「進度？」。
