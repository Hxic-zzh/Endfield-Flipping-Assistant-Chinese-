# 终末地物资交易助手

教学文件：https://github.com/Hxic-zzh/Endfield-Flipping-Assistant-Chinese-/blob/main/%E6%95%99%E5%AD%A6%E6%96%87%E4%BB%B6.pptx
**⚠️ 重要警告：这个代码非常难绷！**

这是一个专门为《终末地》游戏开发的物资交易辅助工具，主要用于管理好友商店商品价格和利润计算。

## 🚨 运行环境要求（严格！）

### 1. 系统分辨率
- **必须**是 **Windows 11**
- **必须**是 **2560×1440** 分辨率
- ❗ 代码中的坐标硬编码严重，仅在2560×1440分辨率下才能"大致"正常运行
- ❗ 其他分辨率可能导致截图位置错误、识别失败等问题

### 2. Python环境
- **Python 3.13+** 必须
- 低于3.13的版本可能无法正常运行

## 📦 安装依赖库

运行以下命令安装所有必需的Python库：直接最新版，管那么多呢哥们

```cmd
pip install PyQt5
pip install pillow
pip install opencv-python
pip install numpy
pip install pytesseract
pip install keyboard
```

## 🔧 外部工具安装（必须！）

### 1. Tesseract OCR
1. 下载: `tesseract-ocr-w64-setup-5.5.0.20241111.exe`
2. 安装时**必须**勾选中文语言包（简体中文）
3. 安装后**必须**将Tesseract添加到系统PATH
4. 验证安装：
   ```cmd
   tesseract --version
   ```

### 2. Real-ESRGAN 图像放大工具
1. 下载: `realesrgan-ncnn-vulkan-20220424-windows.zip`
2. 解压到项目根目录下的 `realesrgan-ncnn-vulkan` 文件夹
3. **文件夹结构必须如下：**

```
realesrgan-ncnn-vulkan/
├── realesrgan-ncnn-vulkan.exe    # 主程序
├── models/                       # 模型文件
│   ├── realesrgan-x4plus.bin
│   ├── realesrgan-x4plus.param
│   ├── realesrgan-animevideov3.bin
│   ├── realesrgan-animevideov3.param
│   └── ... 其他模型文件
├── vcomp140.dll                     # 运行时库
├── vcomp140d.dll

```

4. 测试运行：
   ```cmd
   cd realesrgan-ncnn-vulkan
   realesrgan-ncnn-vulkan.exe --help
   ```

## 🚀 运行程序

```cmd
python main.py
```

## 📁 项目结构

```
终末地物资助手/
├── main.py                      # 程序入口
├── ui_main.py                   # 主界面
├── friend_window.py             # 好友管理窗口
├── capture_overlay.py           # 截图覆盖层
├── config.py                    # 配置文件
├── image_ocr_utils.py           # OCR图像处理
├── json_data_manager.py         # JSON数据管理
├── product_matcher.py           # 商品名称匹配器
├── ocr_processor.py             # OCR处理器（备用）
├── realesrgan-ncnn-vulkan/      # 图像放大工具（需手动放置）
│   └── ...（如上结构）
├── images/                      # 截图保存目录
├── tempJson/                    # 数据存储目录
├── debug_cells/                 # 调试图像目录
├── debug_cells_x/               # 放大后图像目录
└── friend_mapping.json          # 好友映射文件
```


## 📦 打包发布

使用PyInstaller打包：

```cmd
pip install pyinstaller
pyinstaller --onefile --console --name="物资助手" main.py
```

### Release包内容
在Release区域，您可以找到在win11环境下编译或者使用的完整包

## 📦 已收录弹性物资列表

1. **锚点厨具货组**
2. **悬空鼷兽骨雕货组**
3. **巫术矿钻货组**
4. **天使罐头货组**
5. **谷地水培肉货组**
6. **团结牌口服液货组**
7. **源石树幼苗货组**
8. **赛什卡髀石货组**
9. **警戒者矿镐货组**
10. **硬脑壳头盔货组**
11. **边角料积木货组**
12. **星体晶块货组**



### 1. **主配置文件**
- `ui_main.py` - 主界面的商品下拉列表
- `product_matcher.py` - 商品名称匹配器的基准列表
- `friend_window.py` - 好友窗口的商品预设列表

### 2. **功能说明**
- **OCR自动纠正**：当OCR识别出错时（如"锁点厨具和任组"→"锚点厨具货组"），会自动纠正为正确名称
-

## ⚠️ 已知问题

1. **分辨率硬编码**：坐标值仅在2560×1440下有效
2. **OCR准确率**：依赖图像清晰度，模糊图像识别效果差
3. **游戏更新风险**：游戏UI变化会导致坐标失效
4. **内存占用**：处理大量图像时内存占用较高

## 📝 注意事项

1. 本工具仅供学习和交流使用
2. 请遵守游戏用户协议
3. 截图功能需要游戏窗口在最前端
4. 建议配合游戏进程比对使用

## 🐛 问题反馈
问AI去吧，哈哈哈

**再次强调：这个代码非常难绷！仅推荐在Win11+2560×1440环境下使用！**

祝您使用愉快！🎮
