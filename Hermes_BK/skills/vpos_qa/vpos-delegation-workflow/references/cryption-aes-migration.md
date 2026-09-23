# Cryption.cs AES 遷移記錄 (TASK-005)

## 背景
- **檔案**: `VPOS_Avalonia/ToolLib/Cryption.cs`
- **問題**: 使用已淘汰的 `RijndaelManaged` + `CipherMode.ECB`
- **嚴重度**: HIGH

## 呼叫方分析 (2026-08-07)
| 檔案 | 呼叫次數 | 用途 |
|------|----------|------|
| `SqliteDataAccess.cs` | 7 | 解密 DB 連線字串 |
| `SQLDataTableModel.cs` | 7 | 解密 DB 連線字串 |
| **總計** | **14** | |

所有呼叫方使用硬編碼密文 + 金鑰 `"0123456789987654"`。

## 修改策略
### Phase 1 (TASK-005 - 已完成)
- `RijndaelManaged` → `Aes.Create()`
- 維持 `CipherMode.ECB` + `PKCS7`
- 加入 `using` 確保資源釋放
- 移除無效的 `IV = new Byte[16]` (ECB 不需要 IV)
- 加入 TODO 註解指引未來遷移至 AesGcm

### Phase 2 (TASK-006 或後續)
- 金鑰外置 (移至組態檔或環境變數)
- 同時更改加密模式並重新加密所有密文

## 驗證結果
- `RijndaelManaged` 僅在註解中出現 (0 處程式碼)
- `Aes.Create()` 出現在 L73 (AesEncrypt) + L98 (AesDecrypt)
- `using (Aes aes)` 確保資源釋放
- `ivArray` 已移除 (0 處)
- 檔案時間戳記已更新