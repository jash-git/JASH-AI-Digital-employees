---
name: proxy-property-cleanup
description: 安全地刪除 MainWindow.axaml.cs 中的代理屬性存根，包含全目錄 cascade 替換與內部直接引用處理。
---

# Proxy Property Cleanup — TASK-014 完整流程

## 適用場景
- MainWindow.axaml.cs 中有 `public static T m_xxx { get => MainWindowState.Instance.xxx; set => ... }` 代理屬性
- 所有外部引用已遷移至 `MainWindowState.Instance.mXxx`
- 需要安全地刪除這些 dead code 存根

## 完整流程（鐵律）

### Step 1: 全目錄掃描（CRITICAL）
```bash
# 找出所有引用舊屬性的檔案
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'
```
**⚠️ 不要依賴派單清單！** 子代理容易陷入「管窺效應」，只處理派單提供的檔案而遺漏其他。

### Step 2: 排查三種引用模式
```bash
# 外部檔案引用
grep -rn 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs'

# MainWindow.axaml.cs 內部直接賦值
grep -n '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs

# MainWindow.axaml.cs 內部直接讀取
grep -n '\\bm_xxx\\.\\|\\bm_xxx\\s*==' VPOS_Avalonia/Views/MainWindow.axaml.cs
```

### Step 3: 外部 cascade 替換
對所有 Views/, WebAPI/, Thread/ 等檔案執行：
```
MainWindow.m_xxx → MainWindowState.Instance.mXxx
```

### Step 4: 內部直接引用替換
對 MainWindow.axaml.cs 內部方法中的直接存取：
```
m_xxx = value → MainWindowState.Instance.mXxx = value
m_xxx.property → MainWindowState.Instance.mXxx.property
m_xxx == value → MainWindowState.Instance.mXxx == value
```

### Step 5: 獨立 grep 驗證
```bash
grep 'MainWindow\\.m_xxx' VPOS_Avalonia/ --include='*.cs' → 0 matches
grep '\\bm_xxx\\s*=' VPOS_Avalonia/Views/MainWindow.axaml.cs → 0 matches (應已改為 Instance.mXxx)
```

### Step 6: 刪除存根
```bash
grep -n 'public static.*m_xxx' VPOS_Avalonia/Views/MainWindow.axaml.cs
```
刪除整段 property block（包含 `{ get; set; }`）。

### Step 7: 最終驗證
```bash
grep 'public static.*m_xxx' VPOS_Avalonia/Views/MainWindow.axaml.cs → 0 matches
# WinAPI 方法例外：FindTrayButtonWindow, ShowTouchKeyboard, ShowSoftKeyboard, SoftKeyboard_OSK, CloseVTCD
```

## 命名慣例（m_XXX → mXxx）

| 原始名稱 | 正確轉換 | 錯誤示範 |
|---------|---------|---------|
| `m_UBER_EATS_params` | `mUBER_EATS_params` | `muberEatsParams` ❌ |
| `m_FOODPANDA_params` | `mFOODPANDA_params` | `mfoodpandaParams` ❌ |
| `m_VTSTORE_params` | `mVTSTORE_params` | `mvtsToreParams` ❌ |
| `m_NIDIN_POS_params` | `mNIDIN_POS_params` | `mnidinPosParams` ❌ |
| `m_YORES_POS_params` | `mYORES_POS_params` | `myoresPosParams` ❌ |
| `m_StrVersion` | `mStrVersion` | `strVersion` ❌ |
| `m_StrDeviceCode` | `mStrDeviceCode` | `strDeviceCode` ❌ |
| `m_StrPosExpenseNumber` | `mStrPosExpenseNumber` | `strPosExpenseNumber` ❌ |
| `m_StrPosReportNumber` | `mStrPosReportNumber` | `strPosReportNumber` ❌ |

**規則**：
1. 保留 `m` 前綴
2. 後接 camelCase（駝色）
3. 全大寫縮寫（UBER_EATS、FOODPANDA、VTSTORE、NIDIN_POS、YORES_POS）視為單一單字不拆
4. 底線分隔的單字各取首字母大寫：`m_intOrderTypeIdSelected` → `mIntOrderTypeIdSelected`

## 常見陷阱

### 陷阱 0: Patch fuzzy matching 在大量空白 proxy stub 上失敗（TASK-014-A7 教訓）
**問題**: 當 proxy property stub 內部有大量空行（如 `get => ...;` 與 `set => ...;` 之間 3~5 行空白），`patch` fuzzy matching 會因為空白行數量不匹配而失敗。

**修復方式**：
1. **先刪除單一 stub**：用 `patch(mode='replace')` 刪除一個 stub（包含完整 `{ get; set; }` 區塊），一次只刪一個
2. **不要嘗試一次刪除多個 stub**：即使它們相鄰，fuzzy matching 也容易誤刪
3. **若 patch 連續 2 次失敗** → 改用 `replace_all=True` 刪除該 stub 的宣告行（如 `public static.*m_xxx`）
4. **刪除後立即 grep 驗證**：確認沒有 orphan get/set body 殘留（CS1519 編譯錯誤）

**關鍵規則**：
- 刪除 proxy stub 時，**每次只刪除一個 stub 的完整區塊**（從 `public static T m_xxx` 到 `}`）
- 刪除後檢查相鄰 stub 是否被誤刪（看 get/set body 是否懸空）
- 若有懸空 get/set body → 立即 patch 刪除

### 陷阱 1: 內部直接屬性引用（最嚴重）
MainWindow.axaml.cs 中的方法內部（如 `takeaways_params2Var()`）使用 `m_xxx = value`（直接存取），而非 `MainWindow.m_xxx`。這些在刪除存根後會斷裂成 CS0103。

**修復順序（鐵律）**：
1. 外部 cascade 替換
2. MainWindow.axaml.cs 內部所有引用替換
3. 獨立 grep 驗證
4. 刪除存根
5. 最終驗證

### 陷阱 2: 子代理 DoD 計數不可靠
子代理回報的計數可能不準確（如 TASK-014-A5f 回報 9 處但實際 7 處）。**vpos_lead 必須獨立執行 grep 驗證**。

### 陷阱 3: Cascade 替換全目錄掃描
派單時必附「請先 grep 全 Views 目錄取得完整清單，對所有檔案執行替換，最後再 grep 確認殘留為 0」。

### 陷阱 4: using 宣告遺漏
替換為 `MainWindowState.Instance.mXxx` 後，檔案可能需要 `using VPOS_Avalonia.ViewModels;`。檢查並補上。

### 陷阱 5: WinAPI 方法不應刪除
以下方法保留在 MainWindow.axaml.cs：
- FindTrayButtonWindow
- ShowTouchKeyboard
- ShowSoftKeyboard
- SoftKeyboard_OSK
- CloseVTCD

## QA 審查檢查清單

1. [ ] 外部引用：`grep 'MainWindow\\.m_xxx'` → 0 matches
2. [ ] 內部直接賦值：`grep '\\bm_xxx\\s*='` → 0 matches
3. [ ] 內部直接讀取：`grep '\\bm_xxx\\.\\|\\bm_xxx\\s*=='` → 0 matches
4. [ ] 存根刪除：`grep 'public static.*m_xxx'` → 0 matches（WinAPI 例外）
5. [ ] 命名慣例：全大寫縮寫不拆（UBER_EATS、FOODPANDA 等）
6. [ ] using 宣告：所有檔案都有 `using VPOS_Avalonia.ViewModels;`
7. [ ] 全目錄殘留：`grep -r 'MainWindow\\.m_xxx' VPOS_Avalonia/Views/` → 0

## 交付驗證
- grep 舊模式 → 0 matches (exit code 1)
- grep 新模式 → 符合預期數量 matches
- ls -la 確認檔案修改時間
- 更新 docs/task_board.json 狀態為 REVIEW
