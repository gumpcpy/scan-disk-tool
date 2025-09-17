# 硬碟掃描器 (Hard Disk Scanner)

一個基於PyQt5的硬碟掃描應用程序，可以根據特定規則掃描硬碟中的文件並輸出為CSV格式。

## Screenshots
<img width="702" height="534" alt="EN" src="https://github.com/user-attachments/assets/87d6d4ba-6216-4dcb-ba19-3074caa9f85f" />
<img width="703" height="528" alt="TW" src="https://github.com/user-attachments/assets/956777e4-5ab2-451d-980a-99adff38feec" />
<img width="786" height="528" alt="csv" src="https://github.com/user-attachments/assets/a9fe1544-5336-4a35-a5f2-a50009fb0797" />

## 功能特點

- **多語言支持**: 支持英文、繁體中文、簡體中文
- **三種掃描規則**:
  - 找到.RDC結尾的文件就停止
  - 找到影像序列時就停止
  - 找到.MOV文件（不分大小寫）就停止
- **實時日誌**: 顯示掃描進度和結果
- **CSV輸出**: 包含raw和path兩個欄位
- **用戶友好界面**: 清晰的布局和操作流程

## 安裝要求
目前為Mac M Chip DMG版本

## 使用方法
   - 選擇要掃描的路徑
   - 選擇CSV輸出位置
   - 配置掃描規則（三個checkbox，預設全選）
   - 點擊"開始處理"按鈕
   - 查看日誌區域的掃描進度

## 掃描規則詳解

### 1. RDC文件規則
- 掃描所有.RDC結尾的文件
- RAW欄位：.RDC之前的字串
- PATH欄位：找到.RDC文件的路徑

### 2. 影像序列規則
- 識別影像序列（如：IMG_001.jpg, IMG_002.jpg）
- 支持的影像格式：jpg, jpeg, png, tiff, tif, bmp, gif, exr, dpx, cin, r3d, ari, arri, mxf
- RAW欄位：影像序列上一級的名稱
- PATH欄位：影像序列上一級的路徑

### 3. MOV文件規則
- 掃描所有.MOV文件（不分大小寫）
- RAW欄位：.MOV之前的字串
- PATH欄位：找到.MOV文件的路徑

## 輸出格式

CSV文件包含兩個欄位：
- `raw`: 根據規則提取的文件名或目錄名
- `path`: 文件或目錄的完整路徑

## 版本信息

當前版本：1.0.1

## 技術特點

- 使用PyQt5構建GUI界面
- 多線程處理，避免界面卡頓
- 支持多語言切換
- 實時日誌顯示
- 錯誤處理和用戶提示

## 注意事項

- 掃描大型目錄可能需要較長時間
- 影像序列識別需要至少2個相同命名模式的文件
- 建議在掃描前確保有足夠的磁碟空間保存CSV文件