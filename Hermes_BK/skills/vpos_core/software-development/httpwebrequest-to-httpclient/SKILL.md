---
name: httpwebrequest-to-httpclient
description: "Migrate synchronous HttpWebRequest/HttpWebResponse calls to HttpClient + Timeout while preserving sync signatures."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [csharp, dotnet, networking, migration, async]
---

# Migrate HttpWebRequest → HttpClient (Sync Signature)

## When to Use

When a C# codebase uses the legacy `HttpWebRequest`/`HttpWebResponse` pattern and needs modernization with `HttpClient`, but callers expect synchronous String returns.

## Migration Pattern

### Before (HttpWebRequest)
```csharp
public static String RESTfulAPI_get(String StrDomain, String path, ...) {
    HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
    setHeader(ref request, name, value);
    request.KeepAlive = false;
    HttpRequestCachePolicy noCachePolicy = new HttpRequestCachePolicy(HttpRequestCacheLevel.NoCacheNoStore);
    request.CachePolicy = noCachePolicy;
    request.Method = "GET";
    Thread.Sleep(100);
    ServicePointManager.DefaultConnectionLimit = 200;
    HttpWebResponse response = (HttpWebResponse)request.GetResponse();
    string encoding = response.ContentEncoding;
    if (encoding == null || encoding.Length < 1) encoding = "UTF-8";
    StreamReader reader = new StreamReader(response.GetResponseStream(), Encoding.GetEncoding(encoding));
    StrData = reader.ReadToEnd();
    response.Close();
    request.Abort();
}
```

### After (HttpClient)
```csharp
// Assumes: private static readonly HttpClient _httpClient = new HttpClient() { Timeout = TimeSpan.FromSeconds(30) };

public static String RESTfulAPI_get(String StrDomain, String path, ...) {
    try {
        var response = _httpClient.GetAsync(url).GetAwaiter().GetResult();
        if (!response.IsSuccessStatusCode) {
            StrData = response.StatusCode.ToString();
#if DEBUG
            LogFile.Write("HttpsError ; " + ...);
#endif
            return StrData;
        }
        StrData = response.Content.ReadAsStringAsync().GetAwaiter().GetResult();
#if DEBUG
        LogFile.Write("HttpsNormal ; " + ...);
#endif
        return StrData;
    } catch (Exception e) {
        LogFile.Write("HttpsError ; RESTfulAPI_get (" + url + "): " + e.Message);
        return "";
    }
}
```

## What to Remove

| Legacy pattern | Why |
|---|---|
| `HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url)` | Replaced by `_httpClient.GetAsync(url)` |
| `setHeader(ref request, ...)` | HttpClient uses different header API; keep method but it's no-op for GET |
| `request.KeepAlive = false` | HttpClient manages connections automatically |
| `HttpRequestCachePolicy` | HttpClient default behavior is sufficient |
| `Thread.Sleep(100)` | No longer needed (was a workaround for connection pooling) |
| `ServicePointManager.DefaultConnectionLimit = 200` | HttpClient uses different connection management |
| `response.ContentEncoding` + manual encoding detection | HttpClient returns UTF-8 by default; Content.ReadAsStringAsync handles it |
| `StreamReader` + `GetResponseStream()` | Replaced by `Content.ReadAsStringAsync()` |
| `request.Abort()` / `response.Close()` | HttpClient is disposable but short-lived calls don't need explicit disposal |
| `GC.Collect()` | No longer needed |

## What to Keep

- **Sync signature** — use `.GetAwaiter().GetResult()` for blocking callers
- **URL construction** with `HttpUtility.UrlEncode(StrInput)`
- **#if DEBUG logging blocks** (both error and normal paths)
- **Catch block structure** — log error, return `""` instead of concatenating e.Message to StrData

## Prerequisites

Ensure `_httpClient` exists as a static readonly field:
```csharp
private static readonly HttpClient _httpClient = new HttpClient() { Timeout = TimeSpan.FromSeconds(30) };
```

If multiple overloads share the same client, reuse it. Do NOT create per-call HttpClient instances (causes socket exhaustion).

## Verification Steps

When no .NET SDK is available for compilation:

1. **Count methods:** `grep -c "^        public static String RESTfulAPI_get(" file.cs` → expect 3
2. **No legacy types in refactored section:** `sed -n 'START,ENDp' file | grep "HttpWebRequest\|HttpWebResponse"` → empty
3. **No Thread.Sleep:** `sed -n 'START,ENDp' file | grep "Thread.Sleep"` → empty
4. **No Abort():** `sed -n 'START,ENDp' file | grep "\.Abort()"` → empty
5. **All use HttpClient:** `sed -n 'START,ENDp' file | grep "_httpClient.GetAsync" | wc -l` → equals method count
6. **Brace balance:** Count `{` and `}` in the section — must be equal

## Pitfalls

- **Socket exhaustion:** Never create new HttpClient per call. Always reuse a static readonly instance.
- **Async deadlock:** If callers are already async, prefer `await client.GetAsync(url)` instead of `.GetAwaiter().GetResult()`.
- **Encoding changes:** HttpWebRequest respected server Content-Encoding headers; HttpClient returns UTF-8 by default. If the API sends non-UTF-8 responses, add explicit encoding handling.
- **Header differences:** `request.Headers[name] = value` (HttpWebRequest) maps to `client.DefaultRequestHeaders.Add(name, value)` or per-request `HttpRequestMessage.Headers`. For GET requests with few headers, this is usually fine to skip.
