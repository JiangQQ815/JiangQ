"""
ADB Device Tool
自动识别连接的设备，并将设备号和 xml 文件名填入 bat 文件
支持多设备自动保存到配置
"""

import os
import re
import subprocess
import shutil
from typing import Optional, List


class ADBDeviceTool:
    """ADB设备工具类"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.device_path = None
        self.configured_devices = []  # config 中配置的设备列表
        self.current_devices = []      # 当前实际连接的设备列表
        self.errors = []
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

    def parse_config(self) -> bool:
        """解析配置文件"""
        if not os.path.exists(self.config_path):
            self.errors.append(f'[ERROR] Config file not found: {self.config_path}')
            return False

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            self.errors.append(f'[ERROR] Failed to read config: {str(e)}')
            return False

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('DevicePath='):
                path = line.split('=', 1)[1].strip()
                if not path:
                    self.errors.append('[ERROR] DevicePath cannot be empty')
                    return False

                if not os.path.isabs(path):
                    self.device_path = os.path.abspath(os.path.join(self.script_dir, path))
                else:
                    self.device_path = path

            elif line.startswith('Devices='):
                devices_str = line.split('=', 1)[1].strip()
                if devices_str:
                    self.configured_devices = [d.strip() for d in devices_str.split(',') if d.strip()]

        if not self.device_path:
            self.errors.append('[ERROR] DevicePath not configured')
            return False

        return True

    def save_devices_to_config(self, devices: List[str]) -> bool:
        """保存设备列表到 config"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            devices_str = ','.join(devices)

            # 替换 Devices=那一行
            new_lines = []
            for line in lines:
                if line.startswith('Devices='):
                    new_lines.append(f'Devices={devices_str}\n')
                else:
                    new_lines.append(line)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            return True

        except Exception as e:
            self.errors.append(f'[ERROR] Failed to save devices to config: {str(e)}')
            return False

    def get_adb_devices(self) -> List[str]:
        """获取 ADB 连接的设备列表"""
        try:
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                self.errors.append('[ERROR] adb command failed')
                return []

            output = result.stdout
            devices = []

            lines = output.strip().split('\n')
            for line in lines[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('\t')
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])

            return devices

        except FileNotFoundError:
            self.errors.append('[ERROR] adb not found')
            return []
        except Exception as e:
            self.errors.append(f'[ERROR] Failed to get device list: {str(e)}')
            return []

    def find_xml_file(self) -> tuple:
        """查找文件夹中的 xml 文件"""
        if not os.path.exists(self.device_path):
            return False, None, '[ERROR] Path does not exist'

        if not os.path.isdir(self.device_path):
            return False, None, '[ERROR] Path is not a folder'

        xml_files = [f for f in os.listdir(self.device_path) if f.endswith('.xml')]

        if not xml_files:
            return False, None, '[ERROR] No XML file found in folder'

        if len(xml_files) > 1:
            return False, None, f'[ERROR] Multiple XML files found: {xml_files}'

        return True, xml_files[0], None

    def check_and_fix_bat_xml(self, bat_path: str, xml_filename: str) -> tuple:
        """检查并修正 bat 文件中的 xml 文件名"""
        try:
            with open(bat_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content
            changes = []

            # 查找 bat 中的 xml 文件引用
            xml_pattern = r'"?(\w+\.xml)"?'
            xml_matches = re.findall(xml_pattern, content)

            if xml_matches:
                bat_xml_name = xml_matches[0]
                if bat_xml_name != xml_filename:
                    pattern_to_replace = r'["\']?' + re.escape(bat_xml_name) + r'["\']?'
                    new_content = re.sub(pattern_to_replace, xml_filename, content)

                    if new_content != content:
                        changes.append(f'XML filename: {bat_xml_name} -> {xml_filename}')
                        content = new_content

            if not changes:
                return True, content, None

            # 备份原文件
            shutil.copy2(bat_path, bat_path + '.bak')

            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, content, changes

        except Exception as e:
            return False, None, f'[ERROR] Failed to update bat file: {str(e)}'

    def update_bat_device_serial(self, bat_path: str, device_serial: str) -> tuple:
        """更新 bat 文件中的设备序列号"""
        try:
            with open(bat_path, 'r', encoding='utf-8') as f:
                content = f.read()

            original_content = content

            pattern = r'-s\s+\S+'
            content = re.sub(pattern, f'-s {device_serial}', content)

            if content == original_content:
                return False, content, '[WARN] No -s parameter found in bat file'

            shutil.copy2(bat_path, bat_path + '.bak')

            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True, content, f'Device serial: {device_serial}'

        except Exception as e:
            return False, None, f'[ERROR] Failed to update bat file: {str(e)}'

    def run(self) -> dict:
        """执行主流程"""
        results = {
            'success': False,
            'configured_devices': [],
            'current_devices': [],
            'selected_devices': [],
            'xml_found': None,
            'bat_updated': False,
            'message': '',
            'errors': []
        }

        # 1. 解析配置
        print('[1] Parsing config...')
        if not self.parse_config():
            results['errors'] = self.errors
            results['message'] = '\n'.join(self.errors)
            return results
        print(f'    Device path: {self.device_path}')
        print(f'    Configured devices: {self.configured_devices if self.configured_devices else "(none)"}')

        # 2. 检查 bat 文件
        bat_path = os.path.join(self.device_path, 'a.bat')
        if not os.path.exists(bat_path):
            results['errors'] = [f'[ERROR] a.bat not found: {bat_path}']
            results['message'] = results['errors'][0]
            return results
        print(f'    Found bat: {bat_path}')

        # 3. 查找 xml 文件
        print('\n[2] Finding XML file...')
        ok, xml_filename, msg = self.find_xml_file()
        if not ok:
            results['errors'] = [msg]
            results['message'] = msg
            return results
        print(f'    Found XML: {xml_filename}')
        results['xml_found'] = xml_filename

        # 4. 检查并修正 bat 中的 xml 文件名
        print('\n[3] Checking XML filename in bat...')
        ok, content, msg = self.check_and_fix_bat_xml(bat_path, xml_filename)
        if not ok and msg:
            results['errors'] = [msg]
            results['message'] = msg
            return results
        if msg:
            print(f'    Fixed: {msg}')
        else:
            print(f'    XML filename already correct')

        # 5. 获取当前连接的设备
        print('\n[4] Getting ADB devices...')
        self.current_devices = self.get_adb_devices()
        results['current_devices'] = self.current_devices

        if not self.current_devices:
            print(f'    [WARNING] No ADB device detected')
            results['success'] = True
            results['message'] = 'XML fixed, but no device found'
            return results

        print(f'    Found {len(self.current_devices)} device(s):')
        for d in self.current_devices:
            print(f'      - {d}')

        # 6. 确定要使用的设备
        print('\n[5] Determining devices to use...')

        # 检查 config 中的设备是否都在连接列表中
        valid_configured = [d for d in self.configured_devices if d in self.current_devices]

        if valid_configured:
            # config 中的设备都还连接着，直接使用
            selected_devices = valid_configured
            print(f'    Using configured devices (still connected): {selected_devices}')
        else:
            # config 中的设备不在线或为空，使用当前连接的设备
            selected_devices = self.current_devices
            print(f'    Using currently connected devices: {selected_devices}')

            # 保存到 config
            print(f'    Saving devices to config...')
            if self.save_devices_to_config(selected_devices):
                print(f'    Devices saved: {selected_devices}')
            else:
                print(f'    [WARNING] Failed to save devices to config')

        results['configured_devices'] = self.configured_devices
        results['selected_devices'] = selected_devices

        # 7. 更新 bat 文件
        print('\n[6] Updating device serial in bat...')
        for device in selected_devices:
            ok, content, msg = self.update_bat_device_serial(bat_path, device)
            if ok:
                print(f'    {msg}')
            else:
                print(f'    {msg}')

        results['bat_updated'] = True

        # 8. 成功
        results['success'] = True
        results['message'] = f'Success! Devices filled: {selected_devices}'
        return results


def main():
    print('=' * 60)
    print('ADB Device Tool')
    print('=' * 60)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'config.txt')

    tool = ADBDeviceTool(config_path)
    results = tool.run()

    print()
    print('=' * 60)
    if results['success']:
        print(f'[SUCCESS] {results["message"]}')
    else:
        print('[FAILED]')
        for err in results['errors']:
            print(f'  {err}')
    print('=' * 60)

    return 0 if results['success'] else 1


if __name__ == '__main__':
    exit(main())