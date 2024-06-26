import os
import random
import sys
import logging
from os.path import exists
from time import localtime, sleep
from types import MethodType
import json
import time
import click
import socket
import requests
from requests import get
from requests.exceptions import ConnectionError, ConnectTimeout
from base64 import b64decode

# 改变脚本的工作目录
abs_name = os.path.abspath(__file__)
abs_dir = os.path.dirname(abs_name)
os.chdir(abs_dir)


class FormatFilter(logging.Filter):

    def filter(self, record: logging.LogRecord) -> int:
        def getMessage(obj):
            msg = str(obj.msg)
            if obj.args:
                msg = msg.format(*obj.args)
            return msg

        # 使用`{`风格格式化
        record.getMessage = MethodType(getMessage, record)

        # context: dict = record.__getattribute__('context')
        # record.msg += '\n' + '\n'.join([f'{str(k)}: {str(v)}' for k, v in context.items()])

        return True


#log记录

def init_logger(log_dir='log', level=logging.INFO) -> logging.Logger:
    if not exists(log_dir):
        os.mkdir(log_dir)
    file_handler = logging.FileHandler(f"{log_dir}/"
                                       f"{localtime().tm_year}-"
                                       f"{localtime().tm_mon}-"
                                       f"{localtime().tm_mday}--"
                                       f"{localtime().tm_hour}h-"
                                       f"{localtime().tm_min}m-"
                                       f"{localtime().tm_sec}s.log",
                                       encoding="utf-8")
    formatter = logging.Formatter('[{asctime}]'
                                  '[{levelname!s:5}]'
                                  '[{name!s:^16}]'
                                  '[{lineno!s:4}行]'
                                  '[{module}.{funcName}]\n'
                                  '{message!s}',
                                  style='{',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(formatter)

    _logger = logging.Logger(__name__)
    console = logging.StreamHandler()

    _logger.addHandler(file_handler)
    console.setFormatter(formatter)

    _logger.addHandler(file_handler)
    _logger.addHandler(console)
    _logger.addFilter(FormatFilter())
    return _logger


logger = init_logger()

headers = {"User-Agent": r"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " +
                         "Chrome/86.0.4240.111 Safari/537.36"}
socket.setdefaulttimeout(2)


# todo 设置超时
def getIp():
    """
    查询本机ip地址
    :return: ip
    """
    retry = 0
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('192.168.254.226', 80))
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    except socket.SO_ERROR:
        if retry >= 300:
            raise
        retry += 1
        logger.info('不能连接网络,重试......')
        sleep(1)


def isInternetAccess():
    try:
        if "<title>上网登录页</title>" in get("http://www.baidu.com", timeout=2).text:
            return False
        else:
            return True
    except requests.RequestException:
        return False


def get_config_file_path():
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    return os.path.join(script_dir, ".config")

def getProperties(prop):
    config_file = get_config_file_path()
    # 使用config_file来代替"./.config"
    f = open(config_file, "a+")
    f.close()
    kv = {}
    f = open(config_file, "r")
    for line in f:
        temp = line.split("=")
        kv[temp[0].strip()] = temp[1].strip()
    f.close()
    return kv[prop] if prop in kv else ""

def setProperties(key, value):
    config_file = get_config_file_path()
    key, value = str(key), str(value)
    kv = {}
    f = open(config_file, "r")
    for line in f:
        temp = line.split("=")
        kv[temp[0].strip()] = temp[1].strip()
    kv[key] = value
    f.close()
    f = open(config_file, "w+")
    for k, v in kv.items():
        f.write(k + " = " + v)
        f.write("\n")
    f.close()

@click.group()
def cli():
    """当遇到bug时尝试重新输入密码登录 运行`python login`"""
    pass



# noinspection PyBroadException
@click.command()
@click.option("--username", '-u', prompt="你的学号", default=getProperties("username"))
@click.option("--password", '-p', hide_input=True, prompt="你的校园网密码",
              default=("*" * len(getProperties("password")) if getProperties("password") else None))  # 能够回车直接输入默认值
@click.option("--operator", '-o', prompt="运营商选择[dx,yd,lt,xyw]（代号分别对应电信,移动,联通,校园网）", default=getProperties("operator"))

#自动登录校园网功能

def login(username, password, operator):
    """
    用校园网用户名（学号）和校园网密码登录校园网。（如果你用了路由器，请使用router命令）
    """
    # 如果网络可以访问则直接退出程序
    if isInternetAccess():
        logger.info('网络可以访问')
        print("5秒后开始循环自动登录")
        time.sleep(5)

        # 因为密码是不能给别人看见的，所有要在这里检测缓存的密码

    if password == "*" * len(getProperties("password")) or password is None:
        password = getProperties("password")

    setProperties("username", username)
    setProperties("password", password)
    setProperties("operator", operator)

    operatorMap = {"dx": "%40telecom",
                   "yd": "%40cmcc", "lt": "%40unicom", "xyw": ""}

    retry = 0
    # todo抽象成一个方法来检测是否能上网
    while True:  # 检测是否能够连接上网
        resp = ''
        try:
            resp = get(
                f"http://login.hnust.cn:801/eportal/?c=Portal&a=login&callback=dr1004&login_method=1&user_account=%2C0" +
                f"%2C{username}{operatorMap[operator]}&user_password={password}&wlan_user_ip={getIp()}&wlan_user_ipv6" +
                f"=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&jsVersion=3.3.3&v={random.randint(1000, 9999)}",
                # 防止缓存
                timeout=5)
            if resp.text == r'dr1004({"result":"1","msg":"\u8ba4\u8bc1\u6210\u529f"})':
                message = f"[登录状态]: 登录成功: 运营商是: [{operator}]"
                logger.info(message)
            elif resp.text == r'dr1004({"result":"0","msg":"","ret_code":2})':
                message = "[登录状态]: 已经登录了"
                logger.info(message)
                logger.info("退出登录中......")
                _logOut()
                continue  # 都已经退出登录了,就不要在检测是否可以连接至internet了
            elif "dXNlcmlkIGVycm9y" in resp.text:  # 检测userid error是否在返回值里面
                message = "[登录状态]: 密码错误(检查是否有绑定运营商账号)"
                logger.warning(message)
                break
            elif r"\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a" in resp.text:
                message = "[登录状态]: 密码不能为空"
                logger.info(message)
                break
            else:
                message = "[登录状态]: 芜湖, 未处理信息: " + \
                    b64decode(json.loads(resp.text[7:-1])['msg']).decode()
                logger.error(message)
                break

            logger.info("检测是否可以连接到互联网......")
            if isInternetAccess():
                logger.info("可以连接互联网  登陆成功")
                return
            else:
                if retry >= 10:
                    logger.info("该账号不能连接至Internet(你可能使用校园网登录,因此不能连接至互联网)")
                    return
                logger.info("不能连接互联网, 重试")
        except ConnectTimeout:
            message = "超时(你可能没有连接校园网wifi)"
            logger.error(message)
        except ConnectionError:
            message = "找不到主机(你可能没有连接校园网wifi)"
            logger.error(message)
        except BaseException as e:
            logger.error("未知错误（大概率是因为已经登录校园网导致的登录网页报错，请无视）[{}]".format(type(e)))
            if resp != '':
                logger.error("resp.text: {}".format(resp.text))
        finally:
            retry += 1
            sleep(5)
 #           if retry >= 600:
 #               break
            # logger.info("尝试次数: " + str(retry))


# todo 返回网页包含了用户网络信息，使用re库来获取script标签里面的变量
@click.command()
def getInfo():
    """
    【这个功能还没写】
    返回网页包含了用户网络信息，使用re库来获取script标签里面的变量
    """
    resp = get("http://login.hnust.cn/?isReback=1")
    print(resp.text)
    print("都说了这个功能还没写")


def _logOut():
    try:
        resp = get(f"http://login.hnust.cn:801/eportal/?c=Portal&a=logout&callback=dr1003&login_method=1&user_account" +
                   f"=drcom&user_password=123&ac_logout=0&register_mode=1&wlan_user_ip={getIp()}&wlan_user_ipv6" +
                   f"=&wlan_vlan_id=1&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&jsVersion=3.3.3&v="
                   f"{random.randint(1000, 9999)}",
                   timeout=5)
        if resp.text == r'dr1003({"result":"0","msg":"\u6ce8\u9500\u5931\u8d25"})':
            message = "注销失败(你可能已经注销了)"
        elif resp.text == r'dr1003({"result":"1","msg":"\u6ce8\u9500\u6210\u529f"})':
            message = f"IP：【{getIp()}】注销成功"
        else:
            message = "芜湖, 未处理信息: " + \
                resp.text[7:-1].encode().decode("unicode_escape")
    except ConnectTimeout:
        message = "超时(你可能没有连接校园网wifi)"
    except ConnectionError:
        message = "找不到主机(你可能没有连接校园网wifi)"
    except BaseException as e:
        message = f"未知错误[{type(e)}]：\n" + str(e)
    logger.error(message)


# noinspection PyBroadException
@click.command()
@click.confirmation_option(prompt=f"你确定要注销登陆【你当前IP为：{getIp()}】", default=True)
def logOut():
    """退出登录"""
    _logOut()


# noinspection PyBroadException
@click.command()
def addStartup():
    """把这个程序添加到开机启动里面 这样每次开机就能够自动检测登录了"""
    print("已经禁用此功能, 若要实现开机自启请使用windows计划任务或者创建快捷方式复制到自启动目录代替之")
    ifop = input("是否打开Windows自启动目录[Y,n]") or "Y"

    if ifop == "Y":
        os.popen(
            "explorer.exe \"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp")
        print("已为您打开Windows自启动文件夹，请创建程序快捷方式并复制到自启动文件夹")
        
    else:
        return
#    try:
#        os.popen(
#            "explorer.exe \"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp")
#        logger.info("记得使用管理员的身份运行")
#        logger.warning("已经禁用此功能, 若要实现开机自启请使用windows计划任务代替之")
#        cmd1 = r"copy hnust.py \"C:\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp\\hnust.py\""
#        cmd2 = r"copy .config \"C:\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp\\.config\""
#        cmd3 = r"copy hnust.exe \"C:\ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\StartUp\\hnust.exe\""
#
#        logger.info("cmd1: " + cmd1)
#       logger.info("cmd2: " + cmd2)
#        logger.info("cmd3: " + cmd3)
#
#        result1 = os.popen(
#            cmd1).read()
#        result2 = os.popen(
#            cmd2).read()
#        result3 = os.popen(
#            cmd3).read()
#        logger.info(result1)
#        logger.info(result2)
#        logger.info(result3)
#
#    except IOError as e:
#        logger.error("Unable to copy file. %s" % e)
#        raise
#    except BaseException:
#        logger.error("Unexpected error:", sys.exc_info())
#        raise


#自动登录校园网功能（连接路由器版本）

# noinspection PyBroadException
@click.command()
@click.option("--username", '-u', prompt="你的学号", default=getProperties("username"))
@click.option("--password", '-p', hide_input=True, prompt="你的校园网密码",
              default=("*" * len(getProperties("password")) if getProperties("password") else None))  # 能够回车直接输入默认值
@click.option("--operator", '-o', prompt="运营商选择[dx,yd,lt,xyw]（代号分别对应电信,移动,联通,校园网）", default=getProperties("operator"))

@click.option("--rip", '-i', prompt="你的路由器IP地址", default=getProperties("rip"))

def router(username, password, operator,rip,):
    """
    login命令的路由器网络版本，填写路由器ip地址使得路由器可登录校园网
    """
    # 如果网络可以访问则直接退出程序
    if isInternetAccess():
        logger.info('网络可以访问')
        print("5秒后开始循环自动登录")
        time.sleep(5)

        # 因为密码是不能给别人看见的，所有要在这里检测缓存的密码

    if password == "*" * len(getProperties("password")) or password is None:
        password = getProperties("password")

    setProperties("username", username)
    setProperties("password", password)
    setProperties("rip", rip)
    setProperties("operator", operator)

    operatorMap = {"dx": "%40telecom",
                   "yd": "%40cmcc", "lt": "%40unicom", "xyw": ""}

    retry = 0
    # todo抽象成一个方法来检测是否能上网
    while True:  # 检测是否能够连接上网
        resp = ''
        try:
            resp = get(
                f"http://login.hnust.cn:801/eportal/?c=Portal&a=login&callback=dr1004&login_method=1&user_account=%2C0" +
                f"%2C{username}{operatorMap[operator]}&user_password={password}&wlan_user_ip={rip}&wlan_user_ipv6" +
                f"=&wlan_user_mac=000000000000&wlan_ac_ip=&wlan_ac_name=&jsVersion=3.3.3&v={random.randint(1000, 9999)}",
                # 防止缓存
                timeout=5)
            if resp.text == r'dr1004({"result":"1","msg":"\u8ba4\u8bc1\u6210\u529f"})':
                message = f"[登录状态]: 登录成功: 运营商是: [{operator}]"
                logger.info(message)
            elif resp.text == r'dr1004({"result":"0","msg":"","ret_code":2})':
                message = "[登录状态]: 已经登录了"
                logger.info(message)
                logger.info("退出登录中......")
                _logOut()
                continue  # 都已经退出登录了,就不要在检测是否可以连接至internet了
            elif "dXNlcmlkIGVycm9y" in resp.text:  # 检测userid error是否在返回值里面
                message = "[登录状态]: 密码错误(检查是否有绑定运营商账号)"
                logger.warning(message)
                break
            elif r"\u5bc6\u7801\u4e0d\u80fd\u4e3a\u7a7a" in resp.text:
                message = "[登录状态]: 密码不能为空"
                logger.info(message)
                break
            else:
                message = "[登录状态]: 芜湖, 未处理信息: " + \
                    b64decode(json.loads(resp.text[7:-1])['msg']).decode()
                logger.error(message)
                break

            logger.info("检测是否可以连接到互联网......")
            if isInternetAccess():
                logger.info("可以连接互联网  登陆成功")
                return
            else:
                if retry >= 10:
                    logger.info("该账号不能连接至Internet(你可能使用校园网登录,因此不能连接至互联网)")
                    return
                logger.info("不能连接互联网, 重试")
        except ConnectTimeout:
            message = "超时(你可能没有连接校园网wifi)"
            logger.error(message)
        except ConnectionError:
            message = "找不到主机(你可能没有连接校园网wifi)"
            logger.error(message)
        except BaseException as e:
            logger.error("未知错误（大概率是因为已经登录校园网导致的登录网页报错，请无视）[{}]".format(type(e)))
            if resp != '':
                logger.error("resp.text: {}".format(resp.text))
        finally:
            retry += 1
            sleep(5)
            # logger.info("尝试次数: " + str(retry))

# noinspection PyBroadException
@click.command()
def autologin():
    """设置默认登录选项，请确保程序已记录您的配置信息，否则自动登录无效"""
    mode = input("请选择默认自动登录模式[login,router]:")

    if mode == "login":
        with open(".autologin","w") as file:
            pass
        print("已开启默认直连模式自动登录，以后启动程序将默认采用直连模式自动登录，若要关闭请删除工作目录下.autologin文件")

    elif mode == "router":
        with open(".router","w") as file:
            pass
        print("已开启默认路由器网络模式自动登录，以后启动程序将默认采用路由器网络模式自动登录，若要关闭请删除工作目录下.router文件")

    else:
        print("无效的选择，请输入login或router")
        return

cli.add_command(login)
cli.add_command(logOut)
cli.add_command(getInfo)
cli.add_command(addStartup)
cli.add_command(router)
cli.add_command(autologin)

init_logger(level=logging.DEBUG)
if __name__ == '__main__':
    wdir = os.getcwd()
    dir_name = os.path.basename(wdir)
    if os.path.exists(".autologin") or os.path.exists(".router"):  # 检测自动登录标记文件则自动登录
        if os.path.exists(".autologin"):
            sys.argv = [sys.argv[0], "login",
                    "--username", getProperties(
                        "username") if getProperties("username") else None,
                    "--password", getProperties(
                        "password") if getProperties("password") else None,
                    "--operator", getProperties(
                        "operator") if getProperties("operator") else None,]
        else:
            sys.argv = [sys.argv[0], "router",
                    "--username", getProperties(
                        "username") if getProperties("username") else None,
                    "--password", getProperties(
                        "password") if getProperties("password") else None,
                    "--operator", getProperties(
                        "operator") if getProperties("operator") else None,
                    "--rip", getProperties(
                        "rip") if getProperties("rip") else None,
                    ]
    cli()

#init_logger(level=logging.DEBUG)
#if __name__ == '__main__':
  #  if "StartUp" in sys.argv[0] and len(sys.argv) <= 1:  # 如果在启动目录下则自动检测登录
   #     if os.path.exists(".router"):
    #        sys.argv = [sys.argv[0], "router",]
     #   else:
      #      sys.argv = [sys.argv[0], "login",
       #             "--username", getProperties(
        #                "username") if getProperties("username") else None,
         #           "--password", getProperties(
          #              "password") if getProperties("password") else None,
           #         "--operator", getProperties(
            #            "operator") if getProperties("operator") else None,
             #       "--rip", getProperties(
              #          "rip") if getProperties("rip") else None,
               #     ]
#    cli()
#此版本为Notype学长的hnust-auto-login的改进版，原版无法在路由器环境下工作，故我基于原版新增了路由器网络功能，将login命令中的自动获取设备ip改成手动填写自己的路由器ip，使得软件可在路由器环境下自动登录校园网。