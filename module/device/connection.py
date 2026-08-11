# This Python file uses the following encoding: utf-8
import time

import ipaddress
import logging
import platform
import re
import socket
import subprocess
import uiautomator2 as u2
from adbutils import AdbClient, AdbDevice, AdbTimeout, ForwardItem, ReverseItem
from adbutils.errors import AdbError
from functools import wraps
from module.base.decorator import Config, cached_property, del_cached_property
from module.base.utils import ensure_time
from module.config.server import set_server
from module.device.connection_attr import ConnectionAttr
from module.device.method.utils import (
    RETRY_TRIES, remove_shell_warning, retry_sleep,
    handle_adb_error, PackageNotInstalled,
    recv_all, possible_reasons,
    random_port, get_serial_pair)
from module.exception import RequestHumanTakeover, EmulatorNotRunningError
from module.logger import logger
from module.map.map_grids import SelectedGrids


def retry(func):
    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        """
        Args:
            self (Adb):
        """
        init = None
        for _ in range(RETRY_TRIES):
            try:
                if callable(init):
                    retry_sleep(_)
                    init()
                return func(self, *args, **kwargs)
            # Can't handle
            except RequestHumanTakeover:
                break
            # When adb server was killed
            except ConnectionResetError as e:
                logger.error(e)

                def init():
                    self.adb_reconnect()
            # AdbError
            except AdbError as e:
                if handle_adb_error(e):
                    def init():
                        self.adb_reconnect()
                else:
                    break
            # Package not installed
            except PackageNotInstalled as e:
                logger.error(e)

                def init():
                    self.detect_package()
            # Unknown, probably a trucked image
            except Exception as e:
                logger.exception(e)

                def init():
                    pass

        logger.critical(f'Retry {func.__name__}() failed')
        raise RequestHumanTakeover

    return retry_wrapper


class AdbDeviceWithStatus(AdbDevice):
    def __init__(self, client: AdbClient, serial: str, status: str):
        self.status = status
        super().__init__(client, serial)

    def __str__(self):
        return f'AdbDevice({self.serial}, {self.status})'

    __repr__ = __str__

    def __bool__(self):
        return True


class Connection(ConnectionAttr):
    def __init__(self, config):
        """
        Args:
            config (AzurLaneConfig, str): Name of the user config under ./config
        """
        super().__init__(config)
        if not self.is_over_http:
            self.detect_device()

        # Connect
        self.adb_connect(self.serial)
        logger.attr('AdbDevice', self.adb)

        # Package
        # self.package = self.config.Emulator_PackageName
        self.package = self.config.script.device.package_name.value
        if self.package == 'auto':
            self.detect_package()
        else:
            pass
            # 因为用不到就注释掉了
            # set_server(self.package)
        logger.attr('PackageName', self.package)
        # logger.attr('Server', self.config.SERVER)

    @Config.when(DEVICE_OVER_HTTP=False)
    def adb_command(self, cmd, timeout=10):
        """
        Execute ADB commands in a subprocess,
        usually to be used when pulling or pushing large files.

        Args:
            cmd (list):
            timeout (int):

        Returns:
            str:
        """
        cmd = list(map(str, cmd))
        cmd = [self.adb_binary, '-s', self.serial] + cmd
        logger.info(f'执行: {cmd}')

        # Use shell=True to disable console window when using GUI.
        # Although, there's still a window when you stop running in GUI, which cause by gooey.
        # To disable it, edit gooey/gui/util/taskkill.py

        # No gooey anymore, just shell=False
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=False)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            logger.warning(f'调用 {cmd} 时超时，stdout={stdout}, stderr={stderr}')
        return stdout

    @Config.when(DEVICE_OVER_HTTP=True)
    def adb_command(self, cmd, timeout=10):
        logger.warning(
            f'通过HTTP连接时 adb_command() 不可用: {self.serial}, '
        )
        raise RequestHumanTakeover

    @Config.when(DEVICE_OVER_HTTP=False)
    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        Equivalent to `adb -s <serial> shell <*cmd>`

        Args:
            cmd (list, str):
            stream (bool): Return stream instead of string output (Default: False)
            recvall (bool): Receive all data when stream=True (Default: True)
            timeout (int): (Default: 10)
            rstrip (bool): Strip the last empty line (Default: True)

        Returns:
            str if stream=False
            bytes if stream=True and recvall=True
            socket if stream=True and recvall=False
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            if recvall:
                # bytes
                return recv_all(result)
            else:
                # socket
                return result
        else:
            result = self.adb.shell(cmd, stream=stream, timeout=timeout, rstrip=rstrip)
            result = remove_shell_warning(result)
            # str
            return result

    @Config.when(DEVICE_OVER_HTTP=True)
    def adb_shell(self, cmd, stream=False, recvall=True, timeout=10, rstrip=True):
        """
        Equivalent to http://127.0.0.1:7912/shell?command={command}

        Args:
            cmd (list, str):
            stream (bool): Return stream instead of string output (Default: False)
            recvall (bool): Receive all data when stream=True (Default: True)
            timeout (int): (Default: 10)
            rstrip (bool): Strip the last empty line (Default: True)

        Returns:
            str if stream=False
            bytes if stream=True
        """
        if not isinstance(cmd, str):
            cmd = list(map(str, cmd))

        if stream:
            result = self.u2.shell(cmd, stream=stream, timeout=timeout)
            # Already received all, so `recvall` is ignored
            result = remove_shell_warning(result.content)
            # bytes
            return result
        else:
            result = self.u2.shell(cmd, stream=stream, timeout=timeout).output
            if rstrip:
                result = result.rstrip()
            result = remove_shell_warning(result)
            # str
            return result
    
    def adb_getprop(self, name):
        """
        Get system property in Android, same as `getprop <name>`

        Args:
            name (str): Property name

        Returns:
            str:
        """
        return self.adb_shell(['getprop', name]).strip()

    @cached_property
    def cpu_abi(self) -> str:
        """
        Returns:
            str: arm64-v8a, armeabi-v7a, x86, x86_64
        """
        abi = self.adb_shell(['getprop', 'ro.product.cpu.abi']).strip()
        if not len(abi):
            logger.error(f'CPU ABI 无效: "{abi}"')
        return abi

    @cached_property
    def sdk_ver(self) -> int:
        """
        Android SDK/API levels, see https://apilevels.com/
        """
        sdk = self.adb_shell(['getprop', 'ro.build.version.sdk']).strip()
        try:
            return int(sdk)
        except ValueError:
            logger.error(f'SDK 版本无效: {sdk}')

        return 0

    @cached_property
    def is_avd(self):
        if get_serial_pair(self.serial)[0] is None:
            return False
        if 'ranchu' in self.adb_shell(['getprop', 'ro.hardware']):
            return True
        if 'goldfish' in self.adb_shell(['getprop', 'ro.hardware.audio.primary']):
            return True
        return False
    
    @cached_property
    def nemud_app_keep_alive(self) -> str:
        res = self.adb_getprop('nemud.app_keep_alive')
        logger.attr('nemud.app_keep_alive', res)
        return res
    
    @cached_property
    def is_mumu_over_version_356(self) -> bool:
        """
        Returns:
            bool: If MuMu12 version >= 3.5.6,
                which has nemud.app_keep_alive and always be a vertical device
        """
        return self.nemud_app_keep_alive != ''

    @cached_property
    def _nc_server_host_port(self):
        """
        Returns:
            str, int, str, int:
                server_listen_host, server_listen_port, client_connect_host, client_connect_port
        """
        # For BlueStacks hyper-v, use ADB reverse
        if self.is_bluestacks_hyperv:
            host = '127.0.0.1'
            logger.info(f'连接到 BlueStacks hyper-v，使用主机 {host}')
            port = self.adb_reverse(f'tcp:{self.config.REVERSE_SERVER_PORT}')
            return host, port, host, self.config.REVERSE_SERVER_PORT
        # For emulators, listen on current host
        if self.is_emulator or self.is_over_http:
            try:
                host = socket.gethostbyname(socket.gethostname())
            except socket.gaierror as e:
                logger.error(e)
                logger.error(f'未知的主机名: {socket.gethostname()}')
                host = '127.0.0.1'
            if platform.system() == 'Linux' and host == '127.0.1.1':
                host = '127.0.0.1'
            logger.info(f'连接到本地模拟器，使用主机 {host}')
            port = random_port(self.config.FORWARD_PORT_RANGE)

            # For AVD instance
            if self.is_avd:
                return host, port, "10.0.2.2", port

            return host, port, host, port
        # For local network devices, listen on the host under the same network as target device
        if self.is_network_device:
            hosts = socket.gethostbyname_ex(socket.gethostname())[2]
            logger.info(f'当前主机: {hosts}')
            ip = ipaddress.ip_address(self.serial.split(':')[0])
            for host in hosts:
                if ip in ipaddress.ip_interface(f'{host}/24').network:
                    logger.info(f'连接到本地网络设备，使用主机 {host}')
                    port = random_port(self.config.FORWARD_PORT_RANGE)
                    return host, port, host, port
        # For other devices, create an ADB reverse and listen on 127.0.0.1
        host = '127.0.0.1'
        logger.info(f'连接到未知设备，使用主机 {host}')
        port = self.adb_reverse(f'tcp:{self.config.REVERSE_SERVER_PORT}')
        return host, port, host, self.config.REVERSE_SERVER_PORT

    @cached_property
    def reverse_server(self):
        """
        Setup a server on Alas, access it from emulator.
        This will bypass adb shell and be faster.
        """
        del_cached_property(self, '_nc_server_host_port')
        host_port = self._nc_server_host_port
        logger.info(f'反向服务器监听在 {host_port[0]}:{host_port[1]}, '
                    f'客户端可以发送数据到 {host_port[2]}:{host_port[3]}')
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(host_port[:2])
        server.settimeout(5)
        server.listen(5)
        return server

    @cached_property
    def nc_command(self):
        """
        Returns:
            list[str]: ['nc'] or ['busybox', 'nc']
        """
        sdk = self.sdk_ver
        logger.info(f'sdk_ver: {sdk}')
        if sdk >= 28:
            # Android 9 emulators does not have `nc`, try `busybox nc`
            # BlueStacks Pie (Android 9) has `nc` but cannot send data, try `busybox nc` first
            trial = [
                ['busybox', 'nc'],
                ['nc'],
            ]
        else:
            trial = [
                ['nc'],
                ['busybox', 'nc'],
            ]
        for command in trial:
            # About 3ms
            result = self.adb_shell(command)
            # Result should be command help if success
            # `/system/bin/sh: nc: not found`
            if 'not found' in result:
                continue
            # `/system/bin/sh: busybox: inaccessible or not found\n`
            if 'inaccessible' in result:
                continue
            logger.attr('nc 命令', command)
            return command

        logger.error('没有可用的 `netcat` 命令，请使用不带 `_nc` 后缀的截图方法')
        raise RequestHumanTakeover

    def adb_shell_nc(self, cmd, timeout=5, chunk_size=262144):
        """
        Args:
            cmd (list):
            timeout (int):
            chunk_size (int): Default to 262144

        Returns:
            bytes:
        """
        # Server start listening
        server = self.reverse_server
        server.settimeout(timeout)
        # Client send data, waiting for server accept
        # <command> | nc 127.0.0.1 {port}
        cmd += ["|", *self.nc_command, *self._nc_server_host_port[2:]]
        stream = self.adb_shell(cmd, stream=True, recvall=False)
        try:
            # Server accept connection
            conn, conn_port = server.accept()
        except socket.timeout:
            output = recv_all(stream, chunk_size=chunk_size)
            logger.warning(str(output))
            raise AdbTimeout('reverse server accept timeout')

        # Server receive data
        data = recv_all(conn, chunk_size=chunk_size, recv_interval=0.001)

        # Server close connection
        conn.close()
        return data

    def adb_exec_out(self, cmd, serial=None):
        cmd.insert(0, 'exec-out')
        return self.adb_command(cmd, serial)

    def adb_forward(self, remote):
        """
        Do `adb forward <local> <remote>`.
        choose a random port in FORWARD_PORT_RANGE or reuse an existing forward,
        and also remove redundant forwards.

        Args:
            remote (str):
                tcp:<port>
                localabstract:<unix domain socket name>
                localreserved:<unix domain socket name>
                localfilesystem:<unix domain socket name>
                dev:<character device name>
                jdwp:<process pid> (remote only)

        Returns:
            int: Port
        """
        port = 0
        for forward in self.adb.forward_list():
            if forward.serial == self.serial and forward.remote == remote and forward.local.startswith('tcp:'):
                if not port:
                    logger.info(f'重用转发: {forward}')
                    port = int(forward.local[4:])
                else:
                    logger.info(f'移除冗余转发: {forward}')
                    self.adb_forward_remove(forward.local)

        if port:
            return port
        else:
            # Create new forward
            port = random_port(self.config.FORWARD_PORT_RANGE)
            forward = ForwardItem(self.serial, f'tcp:{port}', remote)
            logger.info(f'创建转发: {forward}')
            self.adb.forward(forward.local, forward.remote)
            return port

    def adb_reverse(self, remote):
        port = 0
        for reverse in self.adb.reverse_list():
            if reverse.remote == remote and reverse.local.startswith('tcp:'):
                if not port:
                    logger.info(f'重用反向: {reverse}')
                    port = int(reverse.local[4:])
                else:
                    logger.info(f'移除冗余反向: {reverse}')
                    self.adb_forward_remove(reverse.local)

        if port:
            return port
        else:
            # Create new reverse
            port = random_port(self.config.FORWARD_PORT_RANGE)
            reverse = ReverseItem(f'tcp:{port}', remote)
            logger.info(f'创建反向: {reverse}')
            self.adb.reverse(reverse.local, reverse.remote)
            return port

    def adb_forward_remove(self, local):
        """
        Equivalent to `adb -s <serial> forward --remove <local>`
        More about the commands send to ADB server, see:
        https://cs.android.com/android/platform/superproject/+/master:packages/modules/adb/SERVICES.TXT

        Args:
            local (str): Such as 'tcp:2437'
        """
        with self.adb_client._connect() as c:
            list_cmd = f"host-serial:{self.serial}:killforward:{local}"
            c.send_command(list_cmd)
            c.check_okay()

    def adb_reverse_remove(self, local):
        """
        Equivalent to `adb -s <serial> reverse --remove <local>`

        Args:
            local (str): Such as 'tcp:2437'
        """
        with self.adb_client._connect() as c:
            c.send_command(f"host:transport:{self.serial}")
            c.check_okay()
            list_cmd = f"reverse:killforward:{local}"
            c.send_command(list_cmd)
            c.check_okay()

    def adb_push(self, local, remote):
        """
        Args:
            local (str):
            remote (str):

        Returns:
            str:
        """
        cmd = ['push', local, remote]
        return self.adb_command(cmd)

    @Config.when(DEVICE_OVER_HTTP=False)
    def adb_connect(self, serial):
        """
        Connect to a serial, try 3 times at max.
        If there's an old ADB server running while Alas is using a newer one, which happens on Chinese emulators,
        the first connection is used to kill the other one, and the second is the real connect.

        Args:
            serial (str):

        Returns:
            bool: If success
        """
        # Disconnect offline device before connecting
        for device in self.list_device():
            if device.status == 'offline':
                logger.warning(f'设备 {serial} 离线，连接前断开它')
                self.adb_disconnect(serial)
            elif device.status == 'unauthorized':
                logger.error(f'设备 {serial} 未授权，请在设备上接受 ADB 调试')
            elif device.status == 'device':
                pass
            else:
                logger.warning(f'设备 {serial} 具有未知状态: {device.status}')

        # Skip for emulator-5554
        if 'emulator-' in serial:
            logger.info(f'"{serial}" 是 `emulator-*` 序列号，跳过 adb connect')
            return True
        if re.match(r'^[a-zA-Z0-9]+$', serial):
            logger.info(f'"{serial}" 似乎是 Android 序列号，跳过 adb connect')
            return True

        # Try to connect
        for _ in range(3):
            msg = self.adb_client.connect(serial)
            logger.info(msg)
            if 'connected' in msg:
                # Connected to 127.0.0.1:59865
                # Already connected to 127.0.0.1:59865
                return True
            elif 'bad port' in msg:
                # bad port number '598265' in '127.0.0.1:598265'
                logger.error(msg)
                possible_reasons('Serial incorrect, might be a typo')
                raise RequestHumanTakeover
            elif '(10061)' in msg:
                # cannot connect to 127.0.0.1:55555:
                # No connection could be made because the target machine actively refused it. (10061)
                logger.info(msg)
                logger.warning('设备不存在，请重启模拟器或设置正确的序列号')
                raise EmulatorNotRunningError

        # Failed to connect
        logger.warning(f'尝试3次后仍无法连接 {serial}，假设已连接')
        self.detect_device()
        return False

    @Config.when(DEVICE_OVER_HTTP=True)
    def adb_connect(self, serial):
        # No adb connect if over http
        return True

    def adb_disconnect(self, serial):
        msg = self.adb_client.disconnect(serial)
        if msg:
            logger.info(msg)

        del_cached_property(self, 'hermit_session')
        del_cached_property(self, 'droidcast_session')
        del_cached_property(self, 'minitouch_builder')
        del_cached_property(self, 'reverse_server')

    def adb_restart(self):
        """
            Reboot adb client
        """
        logger.info('重启 adb')
        # Kill current client
        self.adb_client.server_kill()
        # Init adb client
        del_cached_property(self, 'adb_client')
        _ = self.adb_client

    @Config.when(DEVICE_OVER_HTTP=False)
    def adb_reconnect(self):
        """
           Reboot adb client if no device found, otherwise try reconnecting device.
        """
        # if self.config.Emulator_AdbRestart and len(self.list_device()) == 0:
        if self.config.script.device.adb_restart and len(self.list_device()) == 0:
            # Restart Adb
            logger.warning('重启整个ADB服务')
            self.adb_restart()
            # Connect to device
            self.adb_connect(self.serial)
            self.detect_device()
        else:
            # logger.warning('重连当前设备ADB')
            self.adb_disconnect(self.serial)
            self.adb_connect(self.serial)
            self.detect_device()

    @Config.when(DEVICE_OVER_HTTP=True)
    def adb_reconnect(self):
        logger.warning(
            f'通过HTTP连接设备时: {self.serial} '
            f'adb_reconnect() 被跳过，您可能需要手动重启 ATX'
        )

    def install_uiautomator2(self):
        """
        Init uiautomator2 and remove minicap.
        """
        logger.info('安装 uiautomator2')
        init = u2.init.Initer(self.adb, loglevel=logging.DEBUG)
        # MuMu X has no ro.product.cpu.abi, pick abi from ro.product.cpu.abilist
        if init.abi not in ['x86_64', 'x86', 'arm64-v8a', 'armeabi-v7a', 'armeabi']:
            init.abi = init.abis[0]
        init.set_atx_agent_addr('127.0.0.1:7912')
        try:
            init.install()
        except ConnectionError:
            u2.init.GITHUB_BASEURL = 'http://tool.appetizer.io/openatx'
            init.install()
        self.uninstall_minicap()

    def uninstall_minicap(self):
        """ minicap can't work or will send compressed images on some emulators. """
        logger.info('移除 minicap')
        self.adb_shell(["rm", "/data/local/tmp/minicap"])
        self.adb_shell(["rm", "/data/local/tmp/minicap.so"])

    @Config.when(DEVICE_OVER_HTTP=False)
    def restart_atx(self):
        """
        Minitouch supports only one connection at a time.
        Restart ATX to kick the existing one.
        """
        logger.info('重启 ATX')
        atx_agent_path = '/data/local/tmp/atx-agent'
        self.adb_shell([atx_agent_path, 'server', '--stop'])
        self.adb_shell([atx_agent_path, 'server', '--nouia', '-d', '--addr', '127.0.0.1:7912'])

    @Config.when(DEVICE_OVER_HTTP=True)
    def restart_atx(self):
        logger.warning(
            f'通过HTTP连接设备时: {self.serial} '
            f'restart_atx() 被跳过，您可能需要手动重启 ATX'
        )

    @staticmethod
    def sleep(second):
        """
        Args:
            second(int, float, tuple):
        """
        time.sleep(ensure_time(second))

    _orientation_description = {
        0: 'Normal',
        1: 'HOME key on the right',
        2: 'HOME key on the top',
        3: 'HOME key on the left',
    }
    orientation = 0

    @retry
    def get_orientation(self):
        """
        Rotation of the phone

        Returns:
            int:
                0: 'Normal'
                1: 'HOME key on the right'
                2: 'HOME key on the top'
                3: 'HOME key on the left'
        """
        _DISPLAY_RE = re.compile(
            r'.*DisplayViewport{.*valid=true, .*orientation=(?P<orientation>\d+), .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*'
        )
        output = self.adb_shell(['dumpsys', 'display'])

        res = _DISPLAY_RE.search(output, 0)

        if res:
            o = int(res.group('orientation'))
            if o in Connection._orientation_description:
                pass
            else:
                o = 0
                logger.warning(f'无效的设备方向: {o}，假设正常')
        else:
            o = 0
            logger.warning('无法获取设备方向，假设正常')

        self.orientation = o
        logger.attr('Device Orientation', f'{o} ({Connection._orientation_description.get(o, "Unknown")})')
        return o

    @retry
    def list_device(self):
        """
        Returns:
            SelectedGrids[AdbDeviceWithStatus]:
        """
        devices = []
        try:
            with self.adb_client._connect() as c:
                c.send_command("host:devices")
                c.check_okay()
                output = c.read_string_block()
                logger.debug(output)
                for line in output.splitlines():
                    parts = line.strip().split("\t")
                    if len(parts) != 2:
                        continue
                    device = AdbDeviceWithStatus(self.adb_client, parts[0], parts[1])
                    devices.append(device)
        except ConnectionResetError as e:
            # Happens only on CN users.
            # ConnectionResetError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。
            logger.error(e)
            if '强迫关闭' in str(e):
                logger.critical('无法连接至ADB服务，请关闭UU加速器、原神私服、以及一些劣质代理软件。'
                                '它们会劫持电脑上所有的网络连接，包括与模拟器之间的本地连接。')
        return SelectedGrids(devices)

    def detect_device(self):
        """
        Find available devices
        If serial=='auto' and only 1 device detected, use it
        """
        logger.hr('检测设备')
        devices = self.list_device()

        # Show available devices
        available = devices.select(status='device')
        for device in available:
            logger.info(device.serial)
        if not len(available):
            logger.info('没有可用设备')

        # Show unavailable devices if having any
        unavailable = devices.delete(available)
        if len(unavailable):
            logger.info('以下是检测到但不可用的设备')
            for device in unavailable:
                logger.info(f'{device.serial} ({device.status})')

        # Auto device detection
        if self.config.script.device.serial == 'auto':
        # if self.config.Emulator_Serial == 'auto':
            if available.count == 0:
                logger.critical('未找到可用设备，自动设备检测无法工作，'
                                '请设置确切的序列号，而不是使用 "auto"')
                raise RequestHumanTakeover
            elif available.count == 1:
                logger.info(f'自动设备检测只找到一个设备，使用它')
                self.serial = devices[0].serial
                del_cached_property(self, 'adb')
            else:
                logger.critical('找到多个设备，自动设备检测无法决定选择哪个，'
                                '请将上面列出的可用设备之一复制到 Emulator.Serial')
                raise RequestHumanTakeover

        # Handle LDPlayer
        # LDPlayer serial jumps between `127.0.0.1:5555+{X}` and `emulator-5554+{X}`
        port_serial, emu_serial = get_serial_pair(self.serial)
        if port_serial and emu_serial:
            # Might be LDPlayer, check connected devices
            port_device = devices.select(serial=port_serial).first_or_none()
            emu_device = devices.select(serial=emu_serial).first_or_none()
            if port_device and emu_device:
                # Paired devices found, check status to get the correct one
                if port_device.status == 'device' and emu_device.status == 'offline':
                    self.serial = port_serial
                    logger.info(f'找到 LDPlayer 设备对: {port_device}, {emu_device}. '
                                f'使用序列号: {self.serial}')
                elif port_device.status == 'offline' and emu_device.status == 'device':
                    self.serial = emu_serial
                    logger.info(f'找到 LDPlayer 设备对: {port_device}, {emu_device}. '
                                f'使用序列号: {self.serial}')
            elif not devices.select(serial=self.serial):
                # Current serial not found
                if port_device and not emu_device:
                    logger.info(f'未找到当前序列号 {self.serial}，但找到配对设备 {port_serial}. '
                                f'使用序列号: {port_serial}')
                    self.serial = port_serial
                if not port_device and emu_device:
                    logger.info(f'未找到当前序列号 {self.serial}，但找到配对设备 {emu_serial}. '
                                f'使用序列号: {emu_serial}')
                    self.serial = emu_serial

    @retry
    def list_package(self, show_log=True):
        """
        Find all packages on device.
        Use dumpsys first for faster.
        """
        # 80ms
        if show_log:
            logger.info('获取包列表')
        output = self.adb_shell(r'dumpsys package | grep "Package \["')
        packages = re.findall(r'Package \[([^\s]+)\]', output)
        if len(packages):
            return packages

        # 200ms
        if show_log:
            logger.info('获取包列表')
        output = self.adb_shell(['pm', 'list', 'packages'])
        packages = re.findall(r'package:([^\s]+)', output)
        return packages

    def list_app_packages(self, keywords=('onmyoji', 'yys'), show_log=True):
        """
        Args:
            keywords:
            show_log:

        Returns:
            list[str]: List of package names
        """
        packages = self.list_package(show_log=show_log)
        packages = [p for p in packages if any([k in p.lower() for k in keywords])]
        return packages

    # def list_known_packages(self, show_log=True):
    #     """
    #     Args:
    #         show_log:
    #
    #     Returns:
    #         list[str]: List of package names
    #     """
    #     packages = self.list_package(show_log=show_log)
    #     packages = [p for p in packages if p in server_.VALID_PACKAGE or p in server_.VALID_CLOUD_PACKAGE]
    #     return packages

    def detect_package(self, keywords=('onmyoji', 'yys'), set_config=True):
        """
        Show all possible packages with the given keyword on this device.
        """
        logger.hr('检测包')
        packages = self.list_app_packages(keywords=keywords)

        # 显示包
        logger.info(f'以下是设备 "{self.serial}" 中可用的包，'
                    f'复制到 Alas.Emulator.PackageName 以使用它')
        if len(packages):
            for package in packages:
                logger.info(package)
        else:
            logger.info(f'设备 "{self.serial}" 上没有可用的包')

        # Auto package detection
        if len(packages) == 0:
            logger.critical(f'未找到 {keywords[0]} 包，'
                            f'请确认 {keywords[0]} 已安装在设备 "{self.serial}" 上')
            raise RequestHumanTakeover
        if len(packages) == 1:
            logger.info('自动包检测只找到一个包，使用它')
            self.package = packages[0]
            # Set config
            if set_config:
                self.config.Emulator_PackageName = self.package
            # Set server
            logger.info('服务器变更，释放资源')
            set_server(self.package)
        else:
            logger.critical(
                f'找到多个 {keywords[0]} 包，自动包检测无法决定选择哪个，'
                '请将上面列出的可用设备之一复制到 Alas.Emulator.PackageName')
            raise RequestHumanTakeover
