# ADB Device Tool

## 功能说明

自动识别通过 ADB 连接的 Android 设备，并将设备序列号填入指定的 bat 文件。

## 使用方法

### 1. 配置 config.txt

```
DevicePath=.\test_folder
DeviceSerial=
```

- `DevicePath`: 包含 a.xml 和 a.bat 的文件夹路径
- `DeviceSerial`: 留空则自动检测设备，填入则强制使用指定设备

### 2. 准备文件夹

在指定路径下放置两个文件：
- `a.xml` - XML 配置文件
- `a.bat` - 批处理文件（需包含 `-s 设备号` 格式）

### 3. 运行

双击 `run.bat` 即可

## 目录结构

```
adb_device_tool/
├── config.txt       # 配置文件
├── main.py          # 主程序
├── run.bat         # 运行脚本
├── README.txt      # 说明文档
└── test_folder/    # 测试文件夹（示例）
    ├── a.xml
    └── a.bat
```

## 注意

- 需要安装 Android SDK Platform Tools 并配置到系统 PATH
- bat 文件中需要包含 `-s 设备号` 格式的内容才能被替换