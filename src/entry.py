import base64
import json
import sys
import threading
import time
import traceback
from binascii import Error
from json import JSONDecodeError
from urllib.parse import unquote

import requests

from src.common import inDevelopment
from src.exception.displayable_error import BasicDisplayableError, FailedToConnectError, UnableToDecodeError, \
    NotInRightPathError, NoSettingsFileError
from src.hotupdate import HotUpdateHelper
from src.newupdater import NewUpdater
from src.pywebview.updater_web_view import UpdaterWebView
from src.utils.file import File
from src.utils.logger import info, logger


class Entry:
    def __init__(self):
        self.workDir = None
        self.exe = File(sys.executable)
        self.serverUrl = ''
        self.upgradeApi = ''  # 软件自升级的API
        self.upgradeSource = ''
        self.updateApi = ''  # 文件更新的API
        self.updateSource = ''
        self.exitcode = 0

        # PyWebview
        self.webview: UpdaterWebView = None

        self.initializeWorkDirectory()

        # 删除上次遗留的信号文件
        hotupdateSignal = self.exe.parent('updater.hotupdate.signal')
        errorSignal = self.exe.parent('updater.error.signal')

        hotupdateSignal.delete()
        errorSignal.delete()

    def work(self):
        try:
            self.webview.invokeCallback('init')

            # 读取配置文件
            settingsJson = self.getSettingsJson()

            # 从文件读取服务端url并解码
            self.serverUrl = self.decodeUrl(settingsJson['url'])

            # 发起请求并处理返回的数据
            index = ('/' + settingsJson['index']) if 'index' in settingsJson else ''
            self.webview.invokeCallback('check_for_upgrade', self.serverUrl + index)
            response1 = self.httpGetRequest(self.serverUrl + index)
            upgrade_info = response1['upgrade_info']
            upgrade_dir = response1['upgrade_dir']
            update_info = response1['update_info']
            update_dir = response1['update_dir']
            self.upgradeApi = (self.serverUrl + '/' + upgrade_info) if not upgrade_info.startswith('http') else upgrade_info
            self.upgradeSource = (self.serverUrl + '/' + upgrade_dir) if not upgrade_dir.startswith('http') else upgrade_dir
            self.updateApi = (self.serverUrl + '/' + update_info) if not update_info.startswith('http') else update_info
            self.updateSource = (self.serverUrl + '/' + update_dir) if not update_dir.startswith('http') else update_dir

            # 检查最新版本
            response2 = self.httpGetRequest(self.upgradeApi)
            remoteFilesStructure = response2

            # 与本地进行对比
            hotupdate = HotUpdateHelper(self)
            self.webview.invokeCallback('calculate_differences_for_upgrade')
            comparer = hotupdate.compare(remoteFilesStructure)

            # 如果有需要删除/下载的文件，代表程序需要更新
            if len(comparer.deleteFiles) > 0 or len(comparer.deleteFolders) > 0 or len(comparer.downloadFiles) > 0:
                info('the followings need updating: ')
                info('uselessFiles: ' + str(comparer.deleteFiles))
                info('uselessFolders: ' + str(comparer.deleteFolders))
                info('missingFiles: ' + str(comparer.downloadFiles))

                # filename, length, hash
                newFiles = [[filename, length[0], length[1]] for filename, length in comparer.downloadFiles.items()]
                newFiles += [[file, -1] for file in comparer.downloadFolders]
                oldFiles = [[file, True] for file in comparer.deleteFiles]
                oldFiles += [[file, False] for file in comparer.deleteFolders]

                self.webview.invokeCallback('whether_upgrade', True)
                self.webview.invokeCallback('upgrading_old_files', oldFiles)
                self.webview.invokeCallback('upgrading_new_files', newFiles)

                hotupdate.main(comparer, )
            else:
                self.webview.invokeCallback('whether_upgrade', False)
                info('there are nothing need updating')

                np = NewUpdater(self)
                np.main(response1, settingsJson)

        except BasicDisplayableError as e:
            logger.error('Displayable Exception: ' + traceback.format_exc())
            self.webview.invokeCallback('on_error', 'DisplayableException', e.title + ': ' + e.content, traceback.format_exc())
            self.exitcode = 1
        except BaseException as e:
            logger.error('Unknown error occurred: ' + traceback.format_exc())
            self.webview.invokeCallback('on_error', 'PythonException', '----------Python exception raised----------\n'+str(type(e))+'\n'+str(e), traceback.format_exc())
            self.exitcode = 1
        finally:
            self.webview.close()

    def main(self):
        width = 800
        height = 600

        try:
            settingsJson = self.getSettingsJson()
            width = settingsJson['width']
            height = settingsJson['height']
        except Exception:
            pass

        onStart = lambda window: threading.Thread(target=self.work, daemon=True).start()

        self.webview = UpdaterWebView(self, onStart=onStart, width=width, height=height)
        self.webview.start()

        info('Webview Exited with exit code '+str(self.exitcode))

        # ------------

        hotupdateSignal = self.exe.parent('updater.hotupdate.signal')
        errorSignal = self.exe.parent('updater.error.signal')

        hotupdateSignal.delete()
        errorSignal.delete()

        if self.exitcode == 2:
            hotupdateSignal.create()

        if self.exitcode == 1:
            errorSignal.create()

        self.webview.close()
        sys.exit(self.exitcode)

    def initializeWorkDirectory(self):
        if not inDevelopment:
            self.workDir = File(sys.argv[1]) if len(sys.argv) > 1 else self.exe.parent.parent.parent
            if '.minecraft' not in self.workDir:
                raise NotInRightPathError(self.workDir.path)
        else:
            self.workDir = File('debug-workdir')
            self.workDir.mkdirs()

    def getSettingsJson(self):
        file = self.workDir('.minecraft/updater.settings.json')
        try:
            return json.loads(file.content)
        except FileNotFoundError:
            raise NoSettingsFileError(file)

    @staticmethod
    def decodeUrl(url: str):
        try:
            serverUrl = unquote(base64.b64decode(url, validate=True).decode('utf-8'), 'utf-8')
        except Error:
            serverUrl = url
        return serverUrl

    @staticmethod
    def httpGetRequest(url):
        response = None
        try:
            response = requests.get(url, timeout=6)
            return response.json()
        except requests.exceptions.ConnectionError as e:
            raise FailedToConnectError(e, url)
        except JSONDecodeError as e:
            raise UnableToDecodeError(e, url, response.status_code, response.text)
        except requests.exceptions.ReadTimeout as e:
            raise FailedToConnectError(e, url)
