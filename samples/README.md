# 自检样例

- `00-A-0001-12-1CS3.pdf`：随包附带的测试图纸（碳钢管道材料表，共 16 条）。内部资料，不要外发。
- `expected_quote.xlsx`：这台机器识别后导出的正确结果，用来对照。
- `expected.json`：`selftest` 比对用的期望数据。

## 怎么自检

1. 先完成安装：双击 `install.bat`；如果问 `Install Python 3.12 now? [Y/N]`，选 `Y`。
2. 双击 `selftest.bat`，等 1–3 分钟。看到 `SELF-TEST PASSED` 表示 OCR 环境正常。
3. 识别结果同时写到 `output/selftest/actual_quote.xlsx`，可以和 `expected_quote.xlsx` 对照。
4. 也可以双击 `start.bat`，把这张 PDF 拖进页面，肉眼核对表格。

通过标准：条目数 16 条、每行都有描述、描述与期望一致率 ≥ 80%。不同电脑的 OCR 可能在个别空格或标点上不同，少量差异不影响使用。

## 期望识别结果（16 条）

导出列 = 图纸原始列（ID / ND / DESCRIPTION / QTY，原样保留）+ 询价模板列（单重 / 总重 / 单价 / 总价）。

| ID | ND | DESCRIPTION | QTY |
|---|---|---|---|---|---|
| 1 | 3/4" | PIPE, XS, CS, SMLS, ASTM A53-B, TYPE S | 4" | 0.1 | m(meter) |
| 2 | 8" | PIPE, STD, CS, ERW, ASTM A53-B, TYPE E (EJ=0.85) | 18'-4" | 5.59 | m(meter) |
| 3 | 12" | PIPE, STD, CS, ERW, ASTM A53-B, TYPE E (EJ=0.85) | 58'-4" | 17.78 | m(meter) |
| 4 | 12" | CAP. WELD. CS. ASTM A234-WPB-S. ASME B16.9 | 2 | 2 | EA(each) |
| 5 | 8" | 90 LR ELL, WELD, CS, ASTM A234-WPB-W, ASME B16.9 | 2 | 2 | EA(each) |
| 6 | 12" | 90 LR ELL, WELD, CS, ASTM A234-WPB-W, ASME B16.9 | 4 | 4 | EA(each) |
| 7 | 12"X8" | REDUCER (CONC), WELD, CS, ASTM A234-WPB-W, ASME B16.9 | 1 | 1 | EA(each) |
| 8 | 12" | TEE, WELD, CS, ASTM A234-WPB-W, ASME B16.9 | 2 | 2 | EA(each) |
| 9 | 12"X3/4" | SOCKOLET, CLASS 3000, WELD, CS, ASTM A105N, MSS SP-97 | 1 | 1 | EA(each) |
| 10 | 8" | FLANGE SLIP-ON, CLASS 150, RF, CS, ASTM A105N, ASME B16.5 | 1 | 1 | EA(each) |
| 11 | 12" | FLANGE SLIP-ON, CLASS 150, RF, CS, ASTM A105N, ASME B16.5 | 7 | 7 | EA(each) |
| 12 | 3/4"X4 1/4" | STUD BOLT, ASTM A193, GR B7 STUD, W/ 2 HEAVY HEX NUTS, ASTM A194, GR 2H | 8 | 8 | EA(each) |
| 13 | 7/8"X4 3/4" | STUD BOLT, ASTM A193, GR B7 STUD, W/ 2 HEAVY HEX NUTS, ASTM A194, GR 2H | 48 | 48 | EA(each) |
| 14 | 8" | GASKET, CLASS 150, 3/16" THK, SPIRAL WOUND TYPE 304 SS WINDING. W/ FLEXIBLE GRAPHITE FILLER, W/ 304 SS INNER RING AND CS OUTER RING, ASME B16.20 | 1 | 1 | EA(each) |
| 15 | 12" | GASKET, CLASS 150, 3/16" THK, SPIRAL WOUND TYPE 304 SS WINDING, W/ FLEXIBLE GRAPHITE FILLER, W/ 304 SS INNER RING AND CS OUTER RING, ASME B16.20 | 4 | 4 | EA(each) |
| 16 | 3/4" | GATE VALVE, SW, CLASS 800, CS BODY, TRIM 8 | 1 | 1 | EA(each) |

材料表里的英制长度（`4"`、`18'-4"`、`58'-4"`）和件数原样保留在 QTY 列，不做换算。
