# 方法提取 { } 計數失準修復模式

## 問題描述
用 Python regex 提取方法時，用 `{` `}` 計數來定位方法範圍會出錯，留下孤立的 `{` 和 `}` 包裹方法定義。

## 連鎖編譯錯誤
- **CS0106**: 修飾元 'public/private' 對此項目無效
- **CS1022**: 必須是類型或命名空間定義，或檔案結尾
- **CS1513**: 必須是 }
- **CS8803**: 最上層陳述式必須在命名空間和型別宣告之前
- **CS1001**: 必須是識別項
- **CS1519**: 成員宣告中的語彙基元 '{' 無效

## 錯誤模式範例
```
L2034: }      ← 多餘的 closing brace
L2035: Window_Loaded   ← 孤立的文字
L2036: {      ← 多餘的 opening brace
L2037: public async void OnWindowLoaded(...)  ← 修飾元無效 (CS0106)
```

## 修復方式

### 步驟 1: 批量移除多餘 { } 包裹方法定義
```python
for i in range(1, len(lines) - 1):
    if lines[i-1].strip() == '}' and lines[i].strip() == '{':
        if re.match(r'(public|private|internal)\s+(async\s+)?void\s+\w+\(', lines[i+1]):
            del lines[i]
            del lines[i-1]
```

### 步驟 2: 移除孤立文字
```python
for i, line in enumerate(lines):
    if line.strip() == 'Window_Loaded' and 'void' not in line and 'Instance' not in line:
        del lines[i]
        break
```

### 步驟 3: 修正內部裸方法呼叫
```python
bare_calls = [
    ('syncthreadCreate();', 'syncthreadCreate(this);'),
    ('printthreadCreate();', 'printthreadCreate(this);'),
    ('InitTimmer();', 'InitTimmer(this);'),
    ('DeleteTimmer();', 'DeleteTimmer(this);'),
    ('syncthreadStop();', 'syncthreadStop(this);'),
    ('printthreadStop();', 'printthreadStop(this);'),
    ('syncthreadStop(0);', 'syncthreadStop(this, 0);'),
]

for i in range(methods_region_start, methods_region_end):
    for old, new in bare_calls:
        if old in ms_lines[i]:
            if 'void ' not in ms_lines[i][:ms_lines[i].index(old)]:
                ms_lines[i] = ms_lines[i].replace(old, new)
```

## 驗證檢查清單
1. grep 確認無 `public void Method` 前面有 `{` 或 `}`
2. grep 確認無孤立方法名稱文字
3. grep 確認所有內部方法呼叫帶 this 參數
4. 讀取修復區域的前 10 行，確認結構正確

## 教訓
- 不要只用 `{` `}` 計數來定位方法範圍
- 改用方法簽名 + 縮排層級來定位方法範圍
- 每次修復後必須驗證結構，不要直接重新提交 QA
