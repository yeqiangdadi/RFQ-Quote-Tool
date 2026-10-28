# 图纸询价单生成器

把管道图纸（PDF / 图片）里的材料表识别成报价单，按公司现有询价模板导出 Excel，也可直接打印 / 另存 PDF。识别全程在本机完成，运行时不需要联网。

## 快速开始

| 系统 | 安装（只做一次，需联网） | 启动 | 自检 |
| --- | --- | --- | --- |
| macOS | 双击 `install.command` | 双击 `start.command` | `selftest.command` |
| Windows | 双击 `install.bat` | 双击 `start.bat` | `selftest.bat` |

启动后浏览器会自动打开 `http://127.0.0.1:8765`（端口被占用时自动顺延）。终端窗口是服务进程，关闭即停止。

环境要求：Python 3.10–3.13（64 位）。安装后占用约 1.5 GB，之后可断网使用。

**Windows 安装完全离线**：包内自带 Python 3.12 安装程序和全部依赖 wheels（`python/`、`wheels/`），装的时候不需要联网、不需要梯子、不需要管理员权限。整个 zip 约 380 MB。

**电脑上没有 Python 也能装**：`install.bat` 找不到 Python 时会询问一次，选 `Y` 就自动装到当前用户，约 1 分钟。

### Windows 常见问题

- **必须先把 zip 解压再运行**。右键压缩包 →「全部解压缩」或用 7-Zip；直接在资源管理器里双击 zip 内的 `install.bat` 会失败（那是个只读临时目录，装不了环境）。解压路径建议全英文，例如 `D:\RFQ-Quote-Tool`。
- 安装脚本会校验 Python 位数和版本、测试文件夹可写，失败时打印具体原因，并把完整日志写到同目录的 `install.log`——还装不上就把这个文件发回来。
- 依赖优先用包内 `wheels/` 离线安装；只有 wheels 缺失时才会尝试 PyPI / 清华 / 阿里云镜像。
- 看到 `No module named 'fastapi'` 之类报错：说明依赖没装完（多半是安装窗口被提前关了）。新版的 `start.bat` 检测到缺依赖会自动重跑 `install.bat`；还失败就把 `install.log` 发回来。
- 首次运行 `.bat` 若弹出 SmartScreen：点「更多信息」→「仍要运行」。
- zip 由网盘/聊天软件下载后可能带锁定标记：右键压缩包 → 属性 → 勾选「解除锁定」再解压。
- 提示缺少 DLL 时，安装微软 VC++ 2015–2022 运行库（x64）；自带的 Python 安装程序会一并装好。
- macOS 若提示「无法打开」，右键脚本 → 打开 即可放行。

## 安装后自检

双击 `selftest.bat`（macOS 用 `selftest.command`），约 1–3 分钟。看到 `SELF-TEST PASSED` 说明 OCR 环境正常。

- 用 `samples/00-A-0001-12-1CS3.pdf` 跑一遍完整识别，结果写到 `output/selftest/actual_quote.xlsx`，可与 `samples/expected_quote.xlsx` 对照。
- 期望的 16 条结果列在 `samples/README.md`；通过标准：16 条、每行有描述、描述一致率 ≥ 80%。不同电脑的 OCR 可能有个别空格/标点差异，不算故障。
- 自检失败时会打印不一致的行，并把原因留在 `install.log` 同级的终端里，截图发回即可。

## 使用流程

1. 把图纸拖进页面，点「开始识别」，等待 OCR 完成。单页约 2–5 分钟，多页 PDF 逐页处理。
2. 核对表格：所有单元格可直接改；填单价会自动算总价（QTY 是纯数字的行）。
3. 「下载 Excel」得到按模板排版的询价单；「打印 / 存 PDF」打开 A4 横向打印页。

识别结果会标注在图纸预览上（绿框），可点开原图对照。

## 输出位置

- `output/exports/<文件名>_报价单.xlsx`：Excel 同时保存一份到这里，方便回查。
- `output/<时间戳>/`：每次识别的原图预览（`pageN.jpg`），不需要可定期清理。

刷新页面后可用地址栏里的 `?job=...` 恢复上次结果；服务重启后需重新识别。

## Excel 模板

**列 = 图纸原始列（原样保留）+ 询价模板列**。例如图纸材料表是 `ID / ND / DESCRIPTION / QTY`，导出就是：

`ID | ND | DESCRIPTION | QTY | 单重 | 总重 | 单价 | 总价`

- 图纸里的原始列名和文字逐字保留，方便和原图对照、也方便供应商按图核价。
- 数量、单位一律沿用图纸 QTY 栏原值，不做换算；模板列 `单重 / 总重 / 单价 / 总价` 留空待供应商填写（页面上填了会一并导出）。
- 宋体 11、细边框、水平垂直居中、自动换行、数据行高 69。

## 识别范围与规则

- 按图纸里的表格框线切分单元格，表头用中英文同义词匹配（Item / Code / Description / QTY / 数量 / 单位 / 备注…）。
- 管道长度 `18'-4"`、`4"` 这类英尺英寸原样保留在 QTY 列，不做单位换算。
- 管道规格 OCR 常见误识别（`3/4*`、`12°`）会修正为 `3/4"`、`12"`。
- 一张图里有多组不同表头的表格时，默认取条目最多的一组，并在页面上提示；无框线表格、手写内容、低分辨率扫描件识别效果差，导出前请人工核对。

## 目录说明

```
quote_app/
  server.py     本地 Web 服务（上传、任务轮询、导出）
  pipeline.py   渲染 → OCR → 表格提取 → 报价条目
  ocr_engine.py 离线 PaddleOCR 封装
  extractor.py  框线成表、表头映射
  exporter.py   按样例模板写 xlsx
  static/       页面与打印页
offline/        离线 OCR 模型缓存（约 143 MB）
python/         自带 Python 3.12 安装程序（电脑没有 Python 时使用）
wheels/         Windows 依赖 wheels（离线安装用，约 252 MB）
samples/        自检图纸、期望结果（expected_quote.xlsx / expected.json）
requirements.txt
安装 / 启动 / 自检脚本
```

分发时把整个文件夹压缩发给同事，排除 `.venv`、`output`、`tmp` 即可；模型已随包附带，同事只需联网执行一次安装。压缩包内文件名全部为英文、UTF-8 编码，避免 Windows 解压乱码。
