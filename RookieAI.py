import gc
import os
import threading
import time
import sys
import requests
import base64
import tkinter as tk
import webbrowser
import mouse
import dxcam
import psutil
from math import sqrt
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from multiprocessing import freeze_support
import cv2
import numpy as np
import pyautogui
import win32api
import win32con
import customtkinter as ctk
from mss import mss
from ultralytics import YOLO
from utils.config import Option
from utils.logger import Logger
from utils.exception import handle_exception
from module.const import *
import ctypes
import random

# ------------------------------------------判断AMD显卡-----------------------------------------------------------------
import torch
#if not torch.cuda.is_available():
#    torch.backends.cudnn.enabled = False
# ------------------------------------------类声明----------------------------------------------------------------------


class AutoFire:
    def __init__(self, interval=0.2):
        self.interval = interval
        self.running = False
        self.destroyed = False
        self.thread = threading.Thread(target=self._mouse_press_loop)
        self.thread.daemon = True
        self.thread.start()

    def _mouse_press_loop(self):
        """循环监听"""
        while not self.destroyed:
            if self.running:
                match mouse_control:
                    case '飞易来USB':
                        dll.M_KeyDown2(ctypes.c_uint64(hdl), int(1))  # 左键按下
                        dll.M_KeyDown2(ctypes.c_uint64(hdl), int(2))  # 左键抬起
                        pass
                    case 'win32':
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                        win32api.mouse_event(
                            win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                    case 'mouse':
                        mouse.click('left')
                    case 'Logitech':
                        LG_driver.click_Left_down()
                        LG_driver.click_Left_up()
                        pass
                time.sleep(self.interval)
            else:
                time.sleep(0.1)

    def start(self):
        """开始开火"""
        self.running = True

    def stop(self):
        """停止开火"""
        self.running = False

    def destroy(self):
        """释放资源"""
        self.running = False
        self.destroyed = True
        self.thread = None

# ------------------------------------------函数声明---------------------------------------------------------------------

# 根据按键名称获取对应的虚拟键码


def get_lock_key(key: str) -> int | None:
    KEY_MAP = {
        '左键': 0x01,
        '右键': 0x02,
        '下侧键': 0x05,
        '左Ctrl': 0xA2,
        '右Ctrl': 0xA3,
        '左Shift': 0xA0,
        '右Shift': 0xA1,
        '左Alt': 0xA4,
        '右Alt': 0xA5,
    }
    return KEY_MAP.get(key)


# ------------------------------------------全局变量---------------------------------------------------------------------

# 选择模型
model_file = "yolov8n.pt"

# 新建一个 MSS 对象（获取截图）
sct = mss()

# 新建一个Option对象
Opt = Option()

# 新建一个AutoFire对象
AFe = AutoFire()

# returns a DXCamera instance on primary monitor
# Primary monitor's BetterCam instance
camera = dxcam.create(output_idx=0, output_color="BGR", max_buffer_len=2048)


# 初始化帧数计时器（帧数计算）
frame_counter = 0
start_time = time.time()
start_test_time = time.time()
last_console_update = time.time()
last_gui_update = time.time()
last_screenshot_mode_update = time.time()

# 初始化gc计时器（垃圾清理）
gc_time = time.time()


# 人体示意图
img = Image.open("body_photo.png")

last_offset_time = time.time()
last_recoil_time = time.time()  # 压枪间隔时间初始化


# ------------------------------------------def部分---------------------------------------------------------------------


def calculate_screen_monitor(capture_width=640, capture_height=640):  # 截图区域
    # 获取屏幕的宽度和高度
    screen_width, screen_height = pyautogui.size()

    # 计算中心点坐标
    center_x, center_y = screen_width // 2, screen_height // 2

    # 定义截图区域，以中心点为基准，截取一个 capture_width x capture_height 的区域
    monitor = {
        "top": center_y - capture_height // 2,
        "left": center_x - capture_width // 2,
        "width": capture_width,
        "height": capture_height,
    }

    return monitor


def calculate_frame_rate(frame_counter, start_time, end_time):  # 帧率计算
    # 避免被零除
    if end_time - start_time != 0:
        frame_rate = frame_counter / (end_time - start_time)
        # 重置下一秒的frame_counter和start_time
        frame_counter = 0
        start_time = time.time()
    else:
        frame_rate = 0  # Or assign something that makes sense in your case
    return frame_rate, frame_counter, start_time


def update_and_display_fps(frame_, frame_counter, start_time, end_time):
    global last_console_update, last_gui_update
    frame_counter += 1
    frame_rate, frame_counter, start_time = calculate_frame_rate(
        frame_counter, start_time, end_time)

    # 每2秒在控制台打印帧率
    current_time = time.time()
    if current_time - last_console_update > 2:
        Logger.debug(f"FPS: {frame_rate:.0f}")  # 在控制台打印帧率
        last_console_update = current_time

    # 每1秒在图形用户界面上更新帧率
    if current_time - last_gui_update > 0.5:
        text_fps = "实时FPS：{:.0f}".format(frame_rate)
        image_label_FPSlabel.configure(text=text_fps)
        last_gui_update = current_time

    # 在 cv2 窗口中继续显示帧率
    cv2.putText(frame_, f"FPS: {frame_rate:.0f}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    return frame_, frame_counter, start_time


def capture_screen(monitor, sct):
    # 使用 MSS 来抓取屏幕
    screenshot = sct.grab(monitor)
    # 把 PIL/Pillow Image 转为 OpenCV ndarray 对象，然后从 BGR 转换为 RGB
    frame = np.array(screenshot)[:, :, :3]

    return frame


def DXcam():
    # 获取屏幕的宽度和高度
    screen_width, screen_height = pyautogui.size()
    
    assert isinstance(screen_width, int)
    assert isinstance(DXcam_screenshot, int)
    assert isinstance(dxcam_maxFPS, int)

    # 计算截图区域
    left, top = (
        screen_width - DXcam_screenshot) // 2, (screen_height - DXcam_screenshot) // 2
    right, bottom = left + DXcam_screenshot, top + DXcam_screenshot
    region = (left, top, right, bottom)

    camera.start(region=region, video_mode=True,
                 target_fps=dxcam_maxFPS)  # 用于捕获区域的可选参数


def display_debug_window(frame):  # 调试窗口
    # 在主循环中显示图像
    cv2.imshow('frame', frame)

    if cv2.waitKey(1) & 0xFF == ord('.'):
        cv2.destroyAllWindows()
        return True
    else:
        return False


def get_desired_size(screen_width_1, screen_height_1):
    # 根据屏幕尺寸判断调整的大小
    if screen_width_1 == 1920 and screen_height_1 == 1080:
        desired_size = (300, 300)
    elif screen_width_1 >= 2560 and screen_height_1 >= 1440:
        desired_size = (370, 370)
    else:
        desired_size = (300, 300)  # 默认大小

    return desired_size


def fetch_readme():  # 从github更新公告
    Logger.info("开始获取公告......")
    try:
        readme_url = "https://api.github.com/repos/Passer1072/RookieAI_yolov8/readme"
        response = requests.get(readme_url, timeout=10)
        response_text = base64.b64decode(
            response.json()['content']).decode('utf-8')
        Logger.info("获取成功")

        # 找到 "更新日志：" 在字符串中的位置
        update_log_start = response_text.find("更新日志：")

        # 若找不到 "更新日志："，则返回全部内容
        if update_log_start == -1:
            return response_text

        # 截取 "更新日志：" 及其后的所有文本
        update_log = response_text[update_log_start:]
        return update_log

    except Exception as e:
        Logger.warn("获取失败：", e)
        return "无法加载最新的 README 文件，这可能是因为网络问题或其他未知错误。"


def fetch_readme_version_number():  # 从github更新公告
    Logger.info("开始获取版本号......")
    try:
        readme_url = "https://api.github.com/repos/Passer1072/RookieAI_yolov8/readme"
        response = requests.get(readme_url, timeout=10)
        response_text = base64.b64decode(
            response.json()['content']).decode('utf-8')
        Logger.info("获取成功")

        # 创建搜索字符串
        search_str = "Current latest version:"

        # 找到 "更新日志：" 在字符串中的位置
        update_log_start = response_text.find(search_str)

        # 截取 "Current latest version: " 及其后的所有文本
        # Move the index to the end of "Current latest version: "
        update_log_start += len(search_str)
        update_log = response_text[update_log_start:]

        # 使用 strip 方法去除两侧空格
        update_log = update_log.strip()

        # 检查获取到的版本号的长度
        if len(update_log) > 20:
            return "版本号格式化错误"
        else:
            return update_log

    except Exception as e:
        Logger.warn("获取失败：", e)
        return "版本号获取失败"


# 加载DLL文件
def load_DLL():  # 加载易键鼠DLL
    global dll, hdl, startup_successful
    # 加载DLL文件
    Logger.debug("开始加载飞易来盒子文件...")
    dll = ctypes.windll.LoadLibrary('./x64_msdk.dll')  # 加载DLL
    Logger.info("启动飞易来盒子...")
    dll.M_Open_VidPid.restype = ctypes.c_uint64  # 声明M_Open函数的返回类型为无符号整数
    hdl = dll.M_Open_VidPid(u_vid, u_pid)  # 打开端口代码
    Logger.debug(f"open handle = {str(hdl)}")

    # 盒子启动测试
    # print("鼠标移动:" + str(dll.M_MoveR(ctypes.c_uint64(hdl), 100, 100) == 0))  # 相对移动
    startup_successful = True  # 初始化启动状态
    if dll.M_MoveR(ctypes.c_uint64(hdl), 100, 100) == 0:
        Logger.info("鼠标移动:True", "启动盒子成功")
        startup_successful = True  # 纪律启动状态为True
    else:
        Logger.warn("鼠标移动:False", "启动盒子失败")
        startup_successful = False  # 记录启动状态为False


def load_lg_dll():  # 加载罗技移动dll
    global LG_driver
    global dll_lg_loaded
    dll_path = r'.\MouseControl.dll'
    if os.path.exists(dll_path):
        LG_driver = ctypes.CDLL(dll_path)
        # 相对移动测试
        LG_driver.move_R(100, 100)
        dll_lg_loaded = True
    else:
        dll_lg_loaded = False


def check_Ubox_startup():
    if not startup_successful:
        Logger.error("未检测到盒子或盒子启动失败无法使用")
        messagebox.showerror("错误", "未检测到盒子或盒子启动失败无法使用")
        mouseMove_var.set('win32')


def check_Logitech_startup():
    global dll_loaded
    if not dll_loaded:
        messagebox.showerror("错误", "未找到罗技MouseControl.dll文件")
        mouseMove_var.set('win32')


def crawl_information_by_github():
    global readme_content, readme_version
    if crawl_information:
        # 读取在线公告
        readme_content = fetch_readme()
        readme_version = fetch_readme_version_number()


def open_web(event):
    webbrowser.open('https://github.com/Passer1072/RookieAI_yolov8')  # 要跳转的网页


def string_to_list(s: str) -> list:  # 忽略颜色保存样式格式化
    s = s.replace('[', '').replace(']', '')
    return [int(num_str) for num_str in s.split(',')]


def choose_model():  # 选择模型
    global model_file
    model_file = filedialog.askopenfilename()  # 在这里让用户选择文件
    model_file_label.config(text=model_file)  # 更新标签上的文本为选择的文件路径


def open_settings_config():
    os.startfile("settings.json")


def load_model_file():  # 加载模型文件
    # 默认的模型文件地址
    default_model_file = "yolov8n.pt"
    model_file = Opt.get('model_file', default_model_file)
    assert isinstance(model_file, str)
    # 检查文件是否存在，如果不存在，使用默认模型文件
    if not os.path.isfile(model_file):
        Logger.warn("设置文件中的模型文件路径无效; 使用默认模型文件")
        model_file = default_model_file

    # 检测文件后缀名并设置 half_precision_model
    file_extension = os.path.splitext(model_file)[1].lower()  # 获取文件扩展名并转换为小写
    half_precision_model = file_extension != ".onnx" and file_extension in [
        ".pt",
        ".engine",
    ]
    Logger.info(f"加载模型文件: {model_file}")
    Logger.info(f"半精度推理 设置为: {half_precision_model}")

    # 如果 model_file 为 None 或者空，我们返回 None，否则我们返回对应的 YOLO 模型
    return YOLO(model_file) if model_file else None


def track_box_id(centerx, centery, box_width, box_height, monitor):  # 跟踪框ID
    global counter_id, buffer_tracks, last_updated, crossed_boxes

    # 计算框的面积
    box_area = box_width * box_height

    # 根据框的面积动态调整identification_range，最大100最小5
    min_range = 90
    max_range = 100
    identification_range = min_range + \
        (max_range - min_range) * (box_area /
                                   (monitor["width"] * monitor["height"]))

    box_id = None
    for id, past_positions in buffer_tracks.items():
        if len(past_positions) > 0 and np.linalg.norm(
                past_positions[-1][0] - np.array([centerx, centery])) < identification_range:
            box_id = id
            break

    if box_id is None:
        box_id = counter_id
        counter_id += 1
        buffer_tracks[box_id] = []
        crossed_boxes[box_id] = False

    buffer_tracks[box_id].append((np.array([centerx, centery]), time.time()))
    last_updated[box_id] = time.time()

    return box_id


def count_pixels_of_color(image, target_color, tolerance=30):  # 颜色忽略
    target_color_bgr = target_color[::-1]
    lower_bound = np.array([max(0, c - tolerance)
                           for c in target_color_bgr], dtype=np.uint8)
    upper_bound = np.array([min(255, c + tolerance)
                           for c in target_color_bgr], dtype=np.uint8)
    mask = cv2.inRange(image, lower_bound, upper_bound)
    return cv2.countNonZero(mask)


def filter_color_above_box(frame_, box, ignore_colors, height=33, width_ratio=1, tolerance=80):  # 颜色忽略
    x1, y1, x2, y2 = map(int, box)
    box_width = x2 - x1
    region_width = int(box_width * width_ratio)
    center_x = x1 + box_width // 2
    region_x1 = max(0, center_x - region_width // 2)
    region_x2 = min(frame_.shape[1], center_x + region_width // 2)
    region_above = frame_[max(0, y1 - height):y1, region_x1:region_x2]

    if region_above.size == 0:
        return False

    for ignore_color in ignore_colors:
        ignore_color_count = count_pixels_of_color(
            region_above, ignore_color, tolerance)
        # print(f"忽略颜色 ({ignore_color}) 像素数: {ignore_color_count}")

        if ignore_color_count >= 5:
            ignore_color_bgr = ignore_color[::-1]
            # cv2.rectangle(frame_, (region_x1, max(0, y1-height)), (region_x2, y1), ignore_color_bgr, -1)
            # print(f"用颜色填充框上方的区域: {ignore_color}")
            return True

    # print("盒子经过了彩色滤光片")
    return False


def process_aiming(centerx_predicted, centery_predicted, previous_centerx, previous_centery,  # 鼠标移动平滑
                   reverse_threshold_x, reverse_threshold_y, smoothing_factor, lockSpeed,
                   threshold, slowDownFactor):
    """
    处理瞄准逻辑，包括短时间内反向移动的过滤、更新锁定速度和平滑处理。

    :param centerx_predicted: 当前预测的X轴瞄准点
    :param centery_predicted: 当前预测的Y轴瞄准点
    :param previous_centerx: 前一帧的X轴瞄准点
    :param previous_centery: 前一帧的Y轴瞄准点
    :param reverse_threshold_x: X轴反向移动的阈值
    :param reverse_threshold_y: Y轴反向移动的阈值
    :param smoothing_factor: 平滑因子（接近1表示更平滑的跟踪）
    :param lockSpeed: 当前的锁定速度
    :param threshold: 检测目标是否“停止”的速度阈值
    :param slowDownFactor: 目标停止时的减速因子
    :return: 平滑处理后的瞄准点 (centerx, centery)
    """
    global centerx_smoothed, centery_smoothed

    # 检测短时间内反向移动，并进行过滤
    if abs(centerx_predicted - previous_centerx) < reverse_threshold_x:
        centerx_predicted = previous_centerx  # 忽略反向移动，保持原方向
    if abs(centery_predicted - previous_centery) < reverse_threshold_y:
        centery_predicted = previous_centery  # 忽略反向移动，保持原方向

    # 更新锁定速度
    if abs(centerx_predicted) < threshold and abs(centery_predicted) < threshold:
        lockSpeed *= slowDownFactor  # 目标停止时，减慢速度以精确瞄准

    # 指数平滑
    centerx_smoothed = (previous_centerx * (1 - smoothing_factor)
                        ) + (centerx_predicted * smoothing_factor)
    centery_smoothed = (previous_centery * (1 - smoothing_factor)
                        ) + (centery_predicted * smoothing_factor)

    # 使用平滑后的位置和锁定速度来计算鼠标移动距离
    centerx = centerx_smoothed * lockSpeed
    centery = centery_smoothed * lockSpeed

    return centerx, centery


def show_random_offset_window():  # 显示随机瞄准偏移配置窗口
    global random_offset_window
    random_offset_window.deiconify()  # 显示随机瞄准偏移配置窗口


def random_offset_set_window():  # 随机瞄准偏移配置窗口
    global random_offset_window, max_offset_entry, min_offset_entry, offset_time_entry

    def close_random_offset_window():
        random_offset_window.destroy()  # 销毁窗口
        random_offset_set_window()  # 打开并隐藏窗口，方便下次直接显示
        load_random_offset()  # 加载随机瞄准参数

    def load_random_offset():  # 加载随机瞄准参数
        global model_file, test_window_frame, screenshot_mode, crawl_information, DXcam_screenshot, dxcam_maxFPS, \
            loaded_successfully, stage1_scope, stage1_intensity, stage2_scope, stage2_intensity, segmented_aiming_switch
        Logger.debug('加载随机瞄准参数...')
        random_offset_mode_var.set(Opt.get(
            "enable_random_offset", False))  # 随机瞄准偏移开关
        offset_time_entry.insert(
            0, str(Opt.get("time_interval", 1)))  # 随即瞄准时间间隔
        offset_range = tuple(Opt.get(
            "offset_range", [0, 1]))  # 随机瞄准偏移范围（0-1）
        max_offset_entry.insert(0, str(offset_range[1]))  # 插入瞄准偏移最大值
        min_offset_entry.insert(0, str(offset_range[0]))  # 插入瞄准偏移最小值

        Logger.debug("设置加载成功！")
        loaded_successfully = True  # 加载成功标识符

    def save_random_offset():  # 保存设置
        global model_file
        Logger.debug("保存随机瞄准部位参数...")
        Opt.update('enable_random_offset', random_offset_mode_var.get())
        Opt.update('time_interval', float(offset_time_entry.get()))
        Opt.update('offset_range', [
                   float(min_offset_entry.get()), float(max_offset_entry.get())])
        Opt.save()

    def save_button():
        update_values()
        save_random_offset()

    random_offset_win_width = 245
    random_offset_win_hight = 200

    random_offset_window = ctk.CTkToplevel(root)
    random_offset_window.title("随机偏移配置")
    random_offset_window.geometry(
        f"{random_offset_win_width}x{random_offset_win_hight}")  # GUI页面大小x
    random_offset_window.resizable(False, False)  # 禁止窗口大小调整
    # 设置当用户点击窗口的关闭按钮时要做的操作
    random_offset_window.protocol("WM_DELETE_WINDOW",
                                  close_random_offset_window)  # 将WM_DELETE_WINDOW的默认操作设置为 _on_closing 函数
    random_offset_window.attributes('-topmost', 1)  # 置顶窗口
    random_offset_window.withdraw()  # 创建后立即隐藏窗口

    random_offset_window_frame = ctk.CTkFrame(
        random_offset_window, width=random_offset_win_width, height=random_offset_win_hight, fg_color="transparent")
    random_offset_window_frame.grid(row=0, column=0, sticky="nsew")

    # 最大值输入框
    max_offset_lable = ctk.CTkLabel(random_offset_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="偏移最大值:")  # 设置标题文本属性
    max_offset_lable.grid(row=1, column=0, sticky="w",
                          padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    max_offset_entry = ctk.CTkEntry(random_offset_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="请输入（1-0）")
    max_offset_entry.grid(row=1, column=0, sticky="n",
                          padx=(120, 0), pady=(20, 0))
    # 最小值输入框
    min_offset_lable = ctk.CTkLabel(random_offset_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="偏移最小值:")  # 设置标题文本属性
    min_offset_lable.grid(row=2, column=0, sticky="w",
                          padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    min_offset_entry = ctk.CTkEntry(random_offset_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="请输入（1-0）")
    min_offset_entry.grid(row=2, column=0, sticky="n",
                          padx=(120, 0), pady=(20, 0))
    # 间隔时间值输入框
    offset_time_lable = ctk.CTkLabel(random_offset_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="切换间隔(秒):")  # 设置标题文本属性
    offset_time_lable.grid(row=3, column=0, sticky="w",
                           padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    offset_time_entry = ctk.CTkEntry(random_offset_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位：秒")
    offset_time_entry.grid(row=3, column=0, sticky="n",
                           padx=(120, 0), pady=(20, 0))
    # 应用按钮
    set_button = ctk.CTkButton(random_offset_window_frame, width=50, image=None,
                               command=save_button, text="保存并应用", font=("Microsoft YaHei", 16))
    set_button.grid(row=5, column=0, sticky="n", padx=(20, 0), pady=(10, 0))


def show_recoil_window():  # 显示辅助压枪配置窗口
    global recoil_window
    recoil_window.deiconify()  # 显示辅助压枪配置窗口


def recoil_set_window():  # 辅助压枪配置窗口
    global recoil_window, recoil_interval_entry, recoil_boosted_distance_time_entry, recoil_boosted_distance_entry, recoil_standard_distance_entry, recoil_transition_time_entry

    def close_recoil_window():
        recoil_window.destroy()  # 销毁窗口
        recoil_set_window()  # 打开并隐藏窗口，方便下次直接显示
        load_recoil()  # 加载辅助压枪参数

    def load_recoil():  # 加载辅助压枪参数
        global loaded_successfully, recoil_interval_entry, recoil_boosted_distance_time_entry, recoil_boosted_distance_entry, recoil_standard_distance_entry, recoil_transition_time_entry
        Logger.debug('加载辅助压枪参数...')
        recoil_interval_entry.insert(
            0, str(Opt.get("recoil_interval", 0.1)))  # 压枪间隔
        recoil_boosted_distance_entry.insert(
            0, str(Opt.get("recoil_boosted_distance", 5)))  # 一阶段单次距离
        recoil_boosted_distance_time_entry.insert(
            0, str(Opt.get("recoil_boosted_distance_time", 0.5)))  # 一阶段时间
        recoil_standard_distance_entry.insert(
            0, str(Opt.get("recoil_standard_distance", 1)))  # 二阶段单次距离
        recoil_transition_time_entry.insert(
            0, str(Opt.get("recoil_transition_time", 0.2)))  # 缓冲时间

        Logger.debug("设置加载成功！")
        loaded_successfully = True  # 加载成功标识符

    def save_recoil():  # 保存设置
        global model_file
        Logger.debug("保存辅助压枪参数...")
        Opt.update('recoil_interval', float(recoil_interval_entry.get()))
        Opt.update('recoil_boosted_distance', float(
            recoil_boosted_distance_entry.get()))
        Opt.update('recoil_boosted_distance_time', float(
            recoil_boosted_distance_time_entry.get()))
        Opt.update('recoil_standard_distance', float(
            recoil_standard_distance_entry.get()))
        Opt.update('recoil_transition_time', float(
            recoil_transition_time_entry.get()))
        Opt.save()

    def save_button():
        # 检查所有输入的值是否均为数字
        entries = [recoil_interval_entry, recoil_boosted_distance_entry, recoil_boosted_distance_time_entry,
                   recoil_standard_distance_entry, recoil_transition_time_entry]
        for entry in entries:
            try:
                float(entry.get())
            except ValueError:  # 如果输入的不是数字
                tk.messagebox.showerror("输入错误", "所有输入值必须为数字，请重新输入。")
                for e in entries:
                    e.delete(0, 'end')  # 清除每个输入框的内容
                load_recoil()  # 重新加载每个输入框的值
                return  # 结束函数
        # 如果所有输入值均符合要求
        update_values()
        save_recoil()

    recoil_win_width = 460
    recoil_win_hight = 220

    recoil_window = ctk.CTkToplevel(root)
    recoil_window.title("辅助压枪配置")
    recoil_window.geometry(
        f"{recoil_win_width}x{recoil_win_hight}")  # GUI页面大小x
    recoil_window.resizable(False, False)  # 禁止窗口大小调整
    # 设置当用户点击窗口的关闭按钮时要做的操作
    recoil_window.protocol("WM_DELETE_WINDOW",
                           close_recoil_window)  # 将WM_DELETE_WINDOW的默认操作设置为 _on_closing 函数
    recoil_window.attributes('-topmost', 1)  # 置顶窗口
    recoil_window.withdraw()  # 创建后立即隐藏窗口

    recoil_window_frame = ctk.CTkFrame(
        recoil_window, width=recoil_win_width, height=recoil_win_hight, fg_color="transparent")
    recoil_window_frame.grid(row=0, column=0, sticky="nsew")

    # 压枪间隔
    recoil_interval_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="压枪间隔(s):")  # 设置标题文本属性
    recoil_interval_lable.grid(row=1, column=0, sticky="w", padx=(
        20, 0), pady=(20, 0))  # 设置标题文本位置属性
    recoil_interval_entry = ctk.CTkEntry(recoil_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位（秒）")
    recoil_interval_entry.grid(
        row=1, column=0, sticky="n", padx=(120, 0), pady=(20, 0))
    # 阶段平滑过度(缓冲时间)
    recoil_transition_time_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="缓冲时间(s):")  # 设置标题文本属性
    recoil_transition_time_lable.grid(
        row=1, column=1, sticky="w", padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    recoil_transition_time_entry = ctk.CTkEntry(recoil_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位（秒）")
    recoil_transition_time_entry.grid(
        row=1, column=1, sticky="n", padx=(120, 0), pady=(20, 0))
    # 一阶段力度
    recoil_boosted_distance_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="一阶段力度:")  # 设置标题文本属性
    recoil_boosted_distance_lable.grid(
        row=2, column=0, sticky="w", padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    recoil_boosted_distance_entry = ctk.CTkEntry(recoil_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位（像素）")
    recoil_boosted_distance_entry.grid(
        row=2, column=0, sticky="n", padx=(120, 0), pady=(20, 0))
    # 一阶段持续时间
    recoil_boosted_distance_time_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="一阶段时间:")  # 设置标题文本属性
    recoil_boosted_distance_time_lable.grid(
        row=2, column=1, sticky="w", padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    recoil_boosted_distance_time_entry = ctk.CTkEntry(recoil_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位：秒")
    recoil_boosted_distance_time_entry.grid(
        row=2, column=1, sticky="n", padx=(120, 0), pady=(20, 0))
    # 二阶段力度
    recoil_standard_distance_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=(
        "Microsoft YaHei", 16), fg_color="transparent", text="二阶段力度:")  # 设置标题文本属性
    recoil_standard_distance_lable.grid(
        row=3, column=0, sticky="w", padx=(20, 0), pady=(20, 0))  # 设置标题文本位置属性
    recoil_standard_distance_entry = ctk.CTkEntry(recoil_window_frame, width=100, font=(
        "Microsoft YaHei", 14), fg_color="#8B8989", text_color="black", placeholder_text="单位（像素）")
    recoil_standard_distance_entry.grid(
        row=3, column=0, sticky="n", padx=(120, 0), pady=(20, 0))
    # 应用按钮
    set_button = ctk.CTkButton(recoil_window_frame, width=50, image=None,
                               command=save_button, text="保存并应用", font=("Microsoft YaHei", 16))
    set_button.grid(row=5, column=0, sticky="n", padx=(20, 0), pady=(20, 0))
    recoil_set_tips_lable = ctk.CTkLabel(recoil_window_frame, width=20, height=0, font=("Microsoft YaHei", 12),
                                         fg_color="transparent", text="Tips:触发方式与所选自瞄触发方式相同\n"
                                                                      "力度为每次移动距离，像素点为单位\n"
                                                                      "缓冲时间为一阶段至二阶段中间的过度时间")  # 设置标题文本属性
    recoil_set_tips_lable.grid(row=5, column=1, sticky="w", padx=(
        0, 0), pady=(10, 0))  # 设置标题文本位置属性


def create_gui_tkinter():  # 软件主题GUI界面
    global aimbot_var, lockSpeed_scale, triggerType_var, arduinoMode_var, lockKey_var, confidence_scale, closest_mouse_dist_scale, screen_width_scale, screen_height_scale, root, model_file, model_file_label, aimOffset_scale, draw_center_var, mouse_Side_Button_Witch_var, LookSpeed_label_text, lockSpeed_variable, confidence_variable, closest_mouse_dist_variable, aimOffset_variable, screen_width_scale_variable, screen_height_scale_variable, image_label, image_label_switch, image_label_FPSlabel, target_selection_var, target_mapping, prediction_factor_variable, prediction_factor_scale, method_of_prediction_var, extra_offset_x_scale, extra_offset_y_scale, extra_offset_y, extra_offset_x, extra_offset_x_variable, extra_offset_y_variable, readme_content, screenshot_mode_var, screenshot_mode, segmented_aiming_switch_var, stage1_scope, stage1_scope_scale, stage1_scope_variable, stage1_intensity_variable, stage1_intensity, stage1_intensity_scale, stage2_scope_variable, stage2_intensity_variable, stage2_scope_scale, stage2_intensity_scale, aimOffset_x, aimOffset_variable_x, aimOffset_x_scale, mouseMove_var, random_offset_mode_var, random_offset_mode_check, recoil_check, recoil_var, tolerance_variable, tolerance_scale, ignore_colors_entry, ignore_colors_variable, automatic_Trigger_var, mouse_movement_smoothing_switch, smooth_aiming_var, predict_model_var

    # 版本号
    version_number = "V2.5.4"
    # 使用customtkinter创建根窗口
    root = ctk.CTk()
    # ctk.set_appearance_mode("system")  # default
    ctk.set_appearance_mode("dark")
    # 在启动页面结束前隐藏主窗口
    root.withdraw()
    # 创建一个启动画面窗口
    top = tk.Toplevel(root)
    top.title("启动中")
    top.attributes('-topmost', 1)

    logo_file = "logo-bird.png"  # 您的LOGO文件路径
    photo = tk.PhotoImage(file=logo_file)
    label = tk.Label(top, image=photo)
    label.pack()

    # 在1秒后关闭启动画面窗口并显示主窗口
    def end_splash():
        top.destroy()  # 销毁启动画面
        root.deiconify()  # 显示主窗口

    root.after(2000, end_splash)  # 1秒后运行

    # 主程序窗口置顶
    root.attributes('-topmost', 1)
    root.update()

    root.title("RookieTIM")  # 标题名称

    root.geometry(f"{_win_width}x{_win_height}")

    # 设置当用户点击窗口的关闭按钮时要做的操作
    # 将WM_DELETE_WINDOW的默认操作设置为 _on_closing 函数
    root.protocol("WM_DELETE_WINDOW", stop_program)

    # 禁止窗口大小调整
    root.resizable(False, True)

    random_offset_set_window()  # 打开随机瞄准设置窗口
    recoil_set_window()  # 打开辅助压枪配置窗口

    # 实例化 CTkTabview 对象
    tab_view = ctk.CTkTabview(root, width=320, height=500)
    # 创建选项卡
    tab_view.add("基础设置")
    tab_view.add("高级设置")
    tab_view.add("其他设置")
    tab_view.add("测试窗口")
    # 锁定 tab_view 的大小，防止改变
    tab_view.grid_propagate(True)

    # 将 CTkTabview 对象添加到主窗口
    tab_view.grid(row=0, column=0, padx=(15, 0), pady=(0, 0))

    # 创建一个Frame来包含aimbot开关和其左边的显示瞄准范围
    aimbot_draw_center_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    aimbot_draw_center_frame.grid(
        row=0, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 'Aimbot' 的复选框
    aimbot_var = ctk.BooleanVar(value=aimbot)
    aimbot_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='Aimbot', variable=aimbot_var,
                                   command=update_values, )
    aimbot_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐
    # 是否显示瞄准范围的开关
    draw_center_var = ctk.BooleanVar(value=False)  # 默认值为False
    draw_center_check = ctk.CTkCheckBox(aimbot_draw_center_frame, text='显示瞄准范围(测试用)', variable=draw_center_var,
                                        command=update_values)
    draw_center_check.grid(row=0, column=1)

    # 创建一个Frame来包含arduinoMode开关和其左边的显示瞄准范围
    arduinoMode_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    arduinoMode_frame.grid(row=1, column=0, sticky='w',
                           pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 'Arduino Mode(未启用)' 的复选框
    arduinoMode_var = ctk.BooleanVar(value=arduinoMode)
    arduinoMode_check = ctk.CTkCheckBox(arduinoMode_frame, text='Arduino Mode(待开发)', variable=arduinoMode_var,
                                        command=update_values, state="DISABLED")
    arduinoMode_check.grid(row=0, column=0, sticky="w",
                           pady=(0, 0))  # 使用grid布局并靠左对齐

    triggerType_var = tk.StringVar(value=triggerType)
    # 创建一个Frame来包含OptionMenu和其左边的Label
    triggerType_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    triggerType_frame.grid(row=2, column=0, sticky='w',
                           pady=5)  # 使用grid布局并靠左对齐
    # 添加一个Label
    triggerType_label = ctk.CTkLabel(triggerType_frame, text="当前触发方式为:")
    triggerType_label.pack(side='left')  # 在Frame中靠左对齐
    # 添加一个OptionMenu小部件
    options = ["按下", "切换", "shift+按下"]
    triggerType_option = ctk.CTkOptionMenu(triggerType_frame, variable=triggerType_var, values=options,
                                           command=update_values)
    triggerType_option.pack(side='left')  # 在Frame中靠左对齐

    # 创建新的Frame部件以容纳标签和OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    frame.grid(row=3, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(frame, text="当前热键为:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    lockKey_var = ctk.StringVar()
    lockKey_var.set('右键')  # 设置选项菜单初始值为'右键'
    options = ['左键', '右键', '下侧键',
               '左Ctrl', '右Ctrl', '左Shift',
               '右Shift', '左Alt', '右Alt']  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    lockKey_menu = ctk.CTkOptionMenu(
        frame, variable=lockKey_var, values=options, command=update_values)
    lockKey_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 创建一个Frame来包含arduinoMode开关和其左边的显示瞄准范围
    mouse_Side_Button_Witch_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    mouse_Side_Button_Witch_frame.grid(
        row=4, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 '鼠标侧键瞄准开关' 的复选框
    mouse_Side_Button_Witch_var = ctk.BooleanVar(value=False)
    mouse_Side_Button_Witch_check = ctk.CTkCheckBox(mouse_Side_Button_Witch_frame, text='鼠标侧键瞄准开关',
                                                    variable=mouse_Side_Button_Witch_var,
                                                    command=update_values)
    mouse_Side_Button_Witch_check.grid(
        row=0, column=0, sticky="w", pady=5)  # 使用grid布局并靠左对齐

    # 瞄准速度
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    lockSpeed_variable = tk.StringVar()
    lockSpeed_variable.set(str(lockSpeed))
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    LookSpeed_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    LookSpeed_frame.grid(row=6, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 一个Label，显示文字"LockSpeed:"
    LookSpeed_label_0 = ctk.CTkLabel(LookSpeed_frame, text="LockSpeed:")
    LookSpeed_label_0.grid(row=0, column=0)  # 在Frame中靠左对齐
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    lockSpeed_scale = ctk.CTkSlider(
        LookSpeed_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    lockSpeed_scale.set(lockSpeed)
    lockSpeed_scale.grid(row=0, column=1)
    # 使用 textvariable 而非 text
    LookSpeed_label_text = ctk.CTkLabel(
        LookSpeed_frame, textvariable=lockSpeed_variable)
    LookSpeed_label_text.grid(row=0, column=2)
    # 如果分段瞄准打开则停用一般瞄准范围设置
    if segmented_aiming_switch:
        ban_LookSpeed_label_0 = ctk.CTkLabel(
            LookSpeed_frame, text="由于分段瞄准启用，该选项已禁用", width=200)
        ban_LookSpeed_label_0.grid(row=0, column=1, padx=(12, 0))  # 行号
        ban_LookSpeed_label_text = ctk.CTkLabel(
            LookSpeed_frame, text="###", width=25)
        ban_LookSpeed_label_text.grid(row=0, column=2)  # 行号

    # 自瞄范围调整
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    closest_mouse_dist_variable = tk.StringVar()
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    closest_mouse_dist_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    closest_mouse_dist_frame.grid(
        row=7, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    closest_mouse_dist_label = ctk.CTkLabel(
        closest_mouse_dist_frame, text="自瞄范围:")
    closest_mouse_dist_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    closest_mouse_dist_scale = ctk.CTkSlider(
        closest_mouse_dist_frame, from_=0, to=300, command=update_values)
    closest_mouse_dist_scale.set(closest_mouse_dist)
    closest_mouse_dist_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    closest_mouse_dist_text = ctk.CTkLabel(
        closest_mouse_dist_frame, textvariable=closest_mouse_dist_variable)
    closest_mouse_dist_text.grid(row=0, column=3)
    # 如果分段瞄准打开则停用一般瞄准范围设置
    if segmented_aiming_switch:
        ban_closest_mouse_dist_label = ctk.CTkLabel(closest_mouse_dist_frame, text="由于分段瞄准启用，该选项已禁用",
                                                    width=200)
        ban_closest_mouse_dist_label.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_closest_mouse_dist_text = ctk.CTkLabel(
            closest_mouse_dist_frame, text="####", width=30)
        ban_closest_mouse_dist_text.grid(row=0, column=3)  # 行号

    # 创建新的Frame部件以容纳标签和OptionMenu
    frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    frame.grid(row=8, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(frame, text="鼠标加速方法:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    method_of_prediction_var = ctk.StringVar()
    method_of_prediction_var.set('禁用加速')  # 设置选项菜单初始值为'左键'
    options = ['禁用加速', '倍率加速']  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    method_of_prediction_menu = ctk.CTkOptionMenu(frame, variable=method_of_prediction_var, values=options,
                                                  command=update_values)
    method_of_prediction_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 创建新的Frame部件以容纳标签和OptionMenu
    mouseMove_frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    mouseMove_frame.grid(row=9, column=0, sticky='w',
                         pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(mouseMove_frame, text="鼠标移动库:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    mouseMove_var = ctk.StringVar()
    mouseMove_var.set('win32')  # 设置选项菜单初始值为'win32'
    options = ["win32", "mouse", "飞易来USB", "Logitech"]  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    mouseMove_menu = ctk.CTkOptionMenu(
        mouseMove_frame, variable=mouseMove_var, values=options, command=update_values)
    mouseMove_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 创建新的Frame部件以容纳标签和OptionMenu
    predict_model_frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    predict_model_frame.grid(
        row=10, column=0, sticky='w', pady=5)  # frame在root窗口中的位置
    # 创建一个标签文本并将其插入frame中
    lbl = ctk.CTkLabel(predict_model_frame, text="预测方法:")
    lbl.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    predict_model_var = ctk.StringVar()
    predict_model_var.set('禁用预测')  # 设置选项菜单初始值为'win32'
    options = ["禁用预测", "自动预测", "手动预测"]  # 定义可用选项的列表
    # 创建OptionMenu并使用lockKey_var和options
    predict_model_menu = ctk.CTkOptionMenu(
        predict_model_frame, variable=predict_model_var, values=options, command=update_values)
    predict_model_menu.grid(row=0, column=1)  # OptionMenu在frame部件中的位置

    # 创建一个名为 '自动扳机' 的复选框
    automatic_Trigger_frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    automatic_Trigger_frame.grid(row=11, column=0, sticky='w', pady=5)
    automatic_Trigger_var = ctk.BooleanVar(value=automatic_Trigger)
    automatic_Trigger_check = ctk.CTkCheckBox(automatic_Trigger_frame, text='自动扳机', variable=automatic_Trigger_var,
                                              command=update_values)
    automatic_Trigger_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐

    # 创建一个名为 '辅助压枪' 的复选框
    recoil_frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    recoil_frame.grid(row=12, column=0, sticky='w', pady=5)
    recoil_var = ctk.BooleanVar(value=recoil_switch)
    recoil_check = ctk.CTkCheckBox(
        recoil_frame, text='辅助压枪', variable=recoil_var, command=update_values)
    recoil_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐

    # 辅助压枪参数配置按钮
    recoil_set_button = ctk.CTkButton(
        recoil_frame, width=50, image=None, command=show_recoil_window, text="配置参数")
    recoil_set_button.grid(row=0, column=2, sticky="n",
                           padx=(130, 0), pady=(0, 0))

    # 创建一个名为 '平滑瞄准' 的复选框
    smooth_aiming_frame = ctk.CTkLabel(tab_view.tab("基础设置"))
    smooth_aiming_frame.grid(row=13, column=0, sticky='w', pady=5)
    smooth_aiming_var = ctk.BooleanVar(value=mouse_movement_smoothing_switch)
    smooth_aiming_check = ctk.CTkCheckBox(
        smooth_aiming_frame, text='平滑瞄准', variable=smooth_aiming_var, command=update_values)
    smooth_aiming_check.grid(row=0, column=0)  # 使用grid布局并靠左对齐

    # 平滑瞄准参数配置按钮
    smooth_aiming_set_button = ctk.CTkButton(
        smooth_aiming_frame, width=50, image=None, command=show_recoil_window, text="配置参数")
    smooth_aiming_set_button.grid(
        row=0, column=2, sticky="n", padx=(130, 0), pady=(0, 0))

    # 2创建一个Frame来包含OptionMenu和其左边的Label-
    message_text_frame = ctk.CTkFrame(tab_view.tab("基础设置"))
    message_text_frame.grid(row=14, column=0, sticky='w',
                            pady=2)  # 使用grid布局并靠左对齐
    # 创建Label
    message_text_Label = ctk.CTkLabel(message_text_frame, text="更新公告")
    message_text_Label.grid(row=0, column=1)
    # 创建文本框
    message_text_box = ctk.CTkTextbox(
        message_text_frame, width=305, height=200, corner_radius=5)
    message_text_box.grid(row=1, column=1, sticky="nsew")
    message_text_box.insert("0.0", readme_content)

    # 目标选择框
    # 创建一个Frame来包含OptionMenu和其左边的Label
    target_selection_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    target_selection_frame.grid(
        row=1, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个标签文本并将其插入frame中
    target_selection_label = ctk.CTkLabel(
        target_selection_frame, text="当前检测目标为:")
    target_selection_label.grid(row=0, column=0)  # 标签在frame部件中的位置
    # 创建一个可变的字符串变量以用于OptionMenu的选项值
    target_selection_var = ctk.StringVar()
    target_selection_var.set('敌人')  # 设置选项菜单初始值为'敌人'
    # 定义可用选项的列表
    options = list(target_mapping.keys())
    # 创建选择框
    target_selection_option = ctk.CTkOptionMenu(target_selection_frame, variable=target_selection_var, values=options,
                                                command=update_values)
    target_selection_option.grid(row=0, column=1)

    # 置信度调整
    # 创建一个 StringVar 对象以保存 lockSpeed_scale 的值
    confidence_variable = tk.StringVar()
    confidence_variable.set(str(confidence))
    # 置信度调整滑块：创建一个名为 'Confidence' 的滑动条;置信度调整模块
    # 创建一个Frame来包含OptionMenu和其左边的Label
    confidence_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    confidence_frame.grid(row=2, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    confidence_label = ctk.CTkLabel(confidence_frame, text="置信度:")
    confidence_label.grid(row=0, column=1, sticky='w')
    # 置信度调整滑块：创建一个名为 'Confidence' 的滑动条;置信度调整模块
    confidence_scale = ctk.CTkSlider(
        confidence_frame, from_=0, to=1, number_of_steps=100, command=update_values)
    confidence_scale.set(confidence)
    confidence_scale.grid(row=0, column=2, padx=(25, 0))
    # 使用 textvariable 而非 text
    confidence_label_text = ctk.CTkLabel(
        confidence_frame, textvariable=confidence_variable)
    confidence_label_text.grid(row=0, column=3)

    # 倍率预测调整
    # 创建一个 StringVar 对象以保存 prediction_factor 的值
    prediction_factor_variable = tk.StringVar()
    prediction_factor_variable.set(str(prediction_factor))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    prediction_factor_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    prediction_factor_frame.grid(
        row=3, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    prediction_factor_label = ctk.CTkLabel(
        prediction_factor_frame, text="瞄准加速:")
    prediction_factor_label.grid(row=0, column=1, sticky='w')
    # 预测因子调整
    prediction_factor_scale = ctk.CTkSlider(prediction_factor_frame, from_=0, to=1, number_of_steps=100,
                                            command=update_values)
    prediction_factor_scale.set(prediction_factor)
    prediction_factor_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    prediction_factor_text = ctk.CTkLabel(
        prediction_factor_frame, textvariable=prediction_factor_variable)
    prediction_factor_text.grid(row=0, column=3)

    # 瞄准偏移X
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    aimOffset_variable_x = tk.StringVar()
    aimOffset_variable_x.set(str(aimOffset_x))
    # 3创建一个Frame来包含滑块和其左边的Label文字
    aimOffset_x_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    aimOffset_x_frame.grid(row=6, column=0, sticky='w',
                           pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    aimOffset_x_label = ctk.CTkLabel(aimOffset_x_frame, text="瞄准偏移X:")
    aimOffset_x_label.grid(row=0, column=0, sticky='w')
    # 一个名为 'Lock Speed' 的滑动条；瞄准速度模块
    aimOffset_x_scale = ctk.CTkSlider(
        aimOffset_x_frame, from_=1, to=-1, number_of_steps=100, command=update_values, width=150)
    aimOffset_x_scale.set(aimOffset_x)
    aimOffset_x_scale.grid(row=0, column=1, padx=(54, 0))
    # 使用 textvariable 而非 text
    aimOffset_x_label_text = ctk.CTkLabel(
        aimOffset_x_frame, textvariable=aimOffset_variable_x)
    aimOffset_x_label_text.grid(row=0, column=2)

    # 瞄准偏移Y
    # 创建一个 StringVar 对象以保存 closest_mouse_dist 的值
    aimOffset_variable = tk.StringVar()
    aimOffset_variable.set(str(aimOffset))
    # 3创建一个Frame来包含滑块和其左边的Label文字
    aimOffset_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    aimOffset_frame.grid(row=7, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="瞄准偏移Y:")
    aimOffset_label.grid(row=0, column=1, sticky='w')
    # 瞄准偏移（数值越大越靠上）
    aimOffset_scale = ctk.CTkSlider(aimOffset_frame, from_=0, to=1, number_of_steps=100, command=update_values,
                                    orientation="vertical")
    aimOffset_scale.set(aimOffset)
    aimOffset_scale.grid(row=0, column=2, padx=(12, 0))
    # 添加一个Label显示瞄准位置：腰部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="胯下")
    aimOffset_label.grid(row=0, column=3, pady=(170, 0))
    # 添加一个Label显示瞄准位置：腹部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="腹部")
    aimOffset_label.grid(row=0, column=3, pady=(80, 0))
    # 添加一个Label显示瞄准位置：胸口
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="胸口")
    aimOffset_label.grid(row=0, column=3, pady=(0, 5))
    # 添加一个Label显示瞄准位置：头部
    aimOffset_label = ctk.CTkLabel(aimOffset_frame, text="头部")
    aimOffset_label.grid(row=0, column=3, pady=(0, 170))
    # 添加一个Label显示人体图片
    aimOffset_label = ctk.CTkLabel(
        aimOffset_frame, image=ctk.CTkImage(img, size=(150, 200)), text="")
    aimOffset_label.grid(row=0, column=4)
    # 使用 textvariable 而非 text
    aimOffset_text = ctk.CTkLabel(
        aimOffset_frame, textvariable=aimOffset_variable)
    aimOffset_text.grid(row=0, column=5, pady=(0, 0))

    # 屏幕宽度
    # 创建一个 StringVar 对象以保存 screen_width_scale 的值
    screen_width_scale_variable = tk.StringVar()
    screen_width_scale_variable.set(str(screen_width))
    # 4创建一个Frame来包含滑块和其左边的Label文字
    screen_width_scale_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    screen_width_scale_frame.grid(
        row=8, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_width_scale_label = ctk.CTkLabel(
        screen_width_scale_frame, text="截图宽度:")
    screen_width_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕宽度滑块
    screen_width_scale = ctk.CTkSlider(screen_width_scale_frame, from_=100, to=2000, number_of_steps=190,
                                       command=update_values)
    screen_width_scale.set(screen_width)  # 初始值
    screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 使用 textvariable 而非 text
    screen_width_scale_text = ctk.CTkLabel(
        screen_width_scale_frame, textvariable=screen_width_scale_variable)
    screen_width_scale_text.grid(row=0, column=3)
    # 如果启用DXcam则停用截图宽度/高度调整滑块
    if screenshot_mode:
        ban_screen_width_scale = ctk.CTkLabel(
            screen_width_scale_frame, text="由于DXcam启用，该选项已禁用", width=200)
        ban_screen_width_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_screen_width_scale_text = ctk.CTkLabel(
            screen_width_scale_frame, text="####", width=30)
        ban_screen_width_scale_text.grid(row=0, column=3)  # 行号

    # 屏幕高度
    # 创建一个 StringVar 对象以保存 screen_height_scale 的值
    screen_height_scale_variable = tk.StringVar()
    screen_height_scale_variable.set(str(screen_height))
    # 5创建一个Frame来包含滑块和其左边的Label文字
    screen_height_scale_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    screen_height_scale_frame.grid(
        row=9, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    screen_height_scale_label = ctk.CTkLabel(
        screen_height_scale_frame, text="截图高度:")
    screen_height_scale_label.grid(row=0, column=1, sticky='w')
    # 创建一个屏幕高度滑块
    screen_height_scale = ctk.CTkSlider(screen_height_scale_frame, from_=100, to=2000, number_of_steps=190,
                                        command=update_values)
    screen_height_scale.set(screen_height)  # 初始值
    screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
    # 如果启用DXcam则停用截图宽度/高度调整滑块
    # 使用 textvariable 而非 text
    screen_height_scale_text = ctk.CTkLabel(
        screen_height_scale_frame, textvariable=screen_height_scale_variable)
    screen_height_scale_text.grid(row=0, column=3)
    if screenshot_mode:
        ban_screen_height_scale = ctk.CTkLabel(
            screen_height_scale_frame, text="由于DXcam启用，该选项已禁用", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_screen_height_scale_text = ctk.CTkLabel(
            screen_height_scale_frame, text="####", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)  # 行号

    # 截图模式选择
    # 创建一个Frame来包含OptionMenu和其左边的Label
    screenshot_mode_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    screenshot_mode_frame.grid(
        row=10, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 '启用DXcam模式' 的复选框
    screenshot_mode_var = ctk.BooleanVar(value=screenshot_mode)
    screenshot_mode_check = ctk.CTkCheckBox(screenshot_mode_frame, text='启用DXcam截图模式(保存后重启生效)',
                                            variable=screenshot_mode_var,
                                            command=update_values)
    screenshot_mode_check.grid(row=0, column=1)  # 使用grid布局并靠左对齐

    # 随机瞄准部位
    # 创建一个Frame来包含OptionMenu和其左边的Label
    random_offset_mode_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    random_offset_mode_frame.grid(
        row=11, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 '启用随机瞄准偏移' 的复选框
    random_offset_mode_var = ctk.BooleanVar(value=enable_random_offset)
    random_offset_mode_check = ctk.CTkCheckBox(random_offset_mode_frame, text='启用随机瞄准偏移',
                                               variable=random_offset_mode_var,
                                               command=update_values)
    random_offset_mode_check.grid(row=0, column=1)  # 使用grid布局并靠左对齐
    # 参数配置按钮
    random_offset_set_button = ctk.CTkButton(
        random_offset_mode_frame, width=50, image=None, command=show_random_offset_window, text="配置参数")  # 加上按钮图像
    random_offset_set_button.grid(
        row=0, column=2, sticky="n", padx=(100, 0), pady=(0, 0))

    # 瞄准模式选择
    # 创建一个Frame来包含OptionMenu和其左边的Label
    segmented_aiming_switch_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    segmented_aiming_switch_frame.grid(
        row=12, column=0, sticky='w', pady=5)  # 使用grid布局并靠左对齐
    # 创建一个名为 '启用DXcam模式' 的复选框
    segmented_aiming_switch_var = ctk.BooleanVar(value=segmented_aiming_switch)
    segmented_aiming_switch_check = ctk.CTkCheckBox(segmented_aiming_switch_frame,
                                                    text='启用分段瞄准模式(保存后重启生效)',
                                                    variable=segmented_aiming_switch_var,
                                                    command=update_values)
    segmented_aiming_switch_check.grid(row=0, column=1)  # 使用grid布局并靠左对齐

    # 分段自瞄范围调整（强锁范围）
    # 创建一个 StringVar 对象以保存 stage1_scope 的值
    stage1_scope_variable = tk.StringVar()
    stage1_scope_variable.set(str(stage1_scope))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    stage1_scope_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    stage1_scope_frame.grid(row=13, column=0, sticky='w',
                            pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    stage1_scope_label = ctk.CTkLabel(stage1_scope_frame, text="强锁范围:")
    stage1_scope_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    stage1_scope_scale = ctk.CTkSlider(
        stage1_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage1_scope_scale.set(stage1_scope)
    stage1_scope_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    stage1_scope_text = ctk.CTkLabel(
        stage1_scope_frame, textvariable=stage1_scope_variable)
    stage1_scope_text.grid(row=0, column=3)
    # 分段瞄准未启用时停用调整
    if not segmented_aiming_switch:
        ban_screen_height_scale = ctk.CTkLabel(
            stage1_scope_frame, text="分段瞄准未启用，该选项已禁用", width=200)
        ban_screen_height_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_screen_height_scale_text = ctk.CTkLabel(
            stage1_scope_frame, text="####", width=30)
        ban_screen_height_scale_text.grid(row=0, column=3)  # 行号

    # 分段自瞄范围调整（强锁速度）
    # 创建一个 StringVar 对象以保存 stage1_intensity 的值
    stage1_intensity_variable = tk.StringVar()
    stage1_intensity_variable.set(str(stage1_intensity))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    stage1_intensity_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    stage1_intensity_frame.grid(
        row=14, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    stage1_intensity_label = ctk.CTkLabel(stage1_intensity_frame, text="强锁速度:")
    stage1_intensity_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    stage1_intensity_scale = ctk.CTkSlider(stage1_intensity_frame, from_=0, to=2, number_of_steps=100,
                                           command=update_values)
    stage1_intensity_scale.set(stage1_intensity)
    stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    stage1_intensity_text = ctk.CTkLabel(
        stage1_intensity_frame, textvariable=stage1_intensity_variable)
    stage1_intensity_text.grid(row=0, column=3)
    # 分段瞄准未启用时停用调整
    if not segmented_aiming_switch:
        ban_stage1_intensity_scale = ctk.CTkLabel(
            stage1_intensity_frame, text="分段瞄准未启用，该选项已禁用", width=200)
        ban_stage1_intensity_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_stage1_intensity_scale = ctk.CTkLabel(
            stage1_intensity_frame, text="####", width=30)
        ban_stage1_intensity_scale.grid(row=0, column=3)  # 行号

    # 分段自瞄范围调整（软锁范围）
    # 创建一个 StringVar 对象以保存 stage2_intensity 的值
    stage2_scope_variable = tk.StringVar()
    stage2_scope_variable.set(str(stage2_intensity))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    stage2_scope_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    stage2_scope_frame.grid(row=15, column=0, sticky='w',
                            pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    stage2_scope_label = ctk.CTkLabel(stage2_scope_frame, text="软锁范围:")
    stage2_scope_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    stage2_scope_scale = ctk.CTkSlider(
        stage2_scope_frame, from_=0, to=300, number_of_steps=300, command=update_values)
    stage2_scope_scale.set(stage2_scope)
    stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    stage2_scope_text = ctk.CTkLabel(
        stage2_scope_frame, textvariable=stage2_scope_variable)
    stage2_scope_text.grid(row=0, column=3)
    # 分段瞄准未启用时停用调整
    if not segmented_aiming_switch:
        ban_stage2_scope_scale = ctk.CTkLabel(
            stage2_scope_frame, text="分段瞄准未启用，该选项已禁用", width=200)
        ban_stage2_scope_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_stage2_scope_scale = ctk.CTkLabel(
            stage2_scope_frame, text="####", width=30)
        ban_stage2_scope_scale.grid(row=0, column=3)  # 行号

    # 分段自瞄范围调整（软锁速度）
    # 创建一个 StringVar 对象以保存 stage2_intensity 的值
    stage2_intensity_variable = tk.StringVar()
    stage2_intensity_variable.set(str(stage2_intensity))
    # 2创建一个Frame来包含OptionMenu和其左边的Label
    stage2_intensity_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    stage2_intensity_frame.grid(
        row=16, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    # 添加一个Label
    stage2_intensity_label = ctk.CTkLabel(stage2_intensity_frame, text="软锁速度:")
    stage2_intensity_label.grid(row=0, column=1, sticky='w')
    # 自瞄范围调整
    stage2_intensity_scale = ctk.CTkSlider(stage2_intensity_frame, from_=0, to=1, number_of_steps=100,
                                           command=update_values)
    stage2_intensity_scale.set(stage2_intensity)
    stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))
    # 使用 textvariable 而非 text
    stage2_intensity_text = ctk.CTkLabel(
        stage2_intensity_frame, textvariable=stage2_intensity_variable)
    stage2_intensity_text.grid(row=0, column=3)
    # 分段瞄准未启用时停用调整
    if not segmented_aiming_switch:
        ban_stage2_intensity_scale = ctk.CTkLabel(
            stage2_intensity_frame, text="分段瞄准未启用，该选项已禁用", width=200)
        ban_stage2_intensity_scale.grid(row=0, column=2, padx=(12, 0))  # 行号
        ban_stage2_intensity_scale = ctk.CTkLabel(
            stage2_intensity_frame, text="####", width=30)
        ban_stage2_intensity_scale.grid(row=0, column=3)  # 行号

    # 颜色忽略
    tolerance_variable = tk.StringVar()
    tolerance_variable.set(str(tolerance))
    tolerance_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    tolerance_frame.grid(row=17, column=0, sticky='w', pady=2)
    tolerance_label = ctk.CTkLabel(tolerance_frame, text="忽略宽容:")
    tolerance_label.grid(row=0, column=1, sticky='w')
    tolerance_scale = ctk.CTkSlider(
        tolerance_frame, from_=0, to=100, number_of_steps=100, command=update_values)
    tolerance_scale.set(tolerance)
    tolerance_scale.grid(row=0, column=2, padx=(12, 0))
    tolerance_label_text = ctk.CTkLabel(
        tolerance_frame, textvariable=tolerance_variable)
    tolerance_label_text.grid(row=0, column=3)

    ignore_colors_variable = tk.StringVar()
    ignore_colors_variable.set(str(ignore_colors))
    ignore_colors_frame = ctk.CTkFrame(tab_view.tab("高级设置"))
    ignore_colors_frame.grid(row=18, column=0, sticky='w', pady=2)
    ignore_colors_label = ctk.CTkLabel(ignore_colors_frame, text="忽略颜色:")
    ignore_colors_label.grid(row=0, column=1, sticky='w')
    ignore_colors_entry = ctk.CTkEntry(
        ignore_colors_frame, textvariable=ignore_colors_variable)
    ignore_colors_entry.delete(0, 'end')  # 清除当前输入框的内容
    ignore_colors_entry.grid(row=0, column=2, padx=(12, 0))
    # 应用颜色忽略参数
    ignore_colors_set_button = ctk.CTkButton(
        ignore_colors_frame, width=50, image=None, command=update_values, text="应用")  # 加上按钮图像
    ignore_colors_set_button.grid(
        row=0, column=3, sticky="n", padx=(10, 0), pady=(0, 0))

    # 6创建一个Frame来包其他设置
    setting_frame = ctk.CTkFrame(tab_view.tab("其他设置"), width=300, height=300)
    setting_frame.grid(row=9, column=0, sticky='w', pady=2)  # 使用grid布局并靠左对齐
    setting_frame.grid_propagate(False)  # 防止框架调整大小以适应其内容

    # 显示所选文件路径的标签
    model_file_label = tk.Label(
        setting_frame, text="还未选择模型文件", width=40, anchor='e')  # 初始化时显示的文本
    model_file_label.grid(row=0, column=0, sticky="w")  # 使用grid布局并靠左对齐

    # 用户选择模型文件的按钮
    model_file_button = ctk.CTkButton(setting_frame, text="选择模型文件(需重启)",
                                      command=choose_model)  # 点击此按钮时，将调用choose_model函数
    model_file_button.grid(row=1, column=0, padx=(
        0, 245), pady=(5, 0))  # 使用grid布局并靠左对齐

    # 创建一键打开配置文件的按钮
    config_file_button = ctk.CTkButton(setting_frame, text="打开配置文件(需重启)",
                                       command=open_settings_config)  # 点击此按钮时，将调用open_config函数
    config_file_button.grid(row=1, column=0, padx=(55, 0), pady=(5, 0))

    # 创建 '保存' 按钮
    save_button = ctk.CTkButton(
        setting_frame, text='保存设置', width=20, command=save_settings)
    save_button.grid(row=2, column=0, padx=(
        0, 320), pady=(10, 0))  # 根据你的需要调整行号

    # 创建 '加载' 按钮
    load_button = ctk.CTkButton(setting_frame, text='加载设置(未启用)', width=20, command=load_settings,
                                state="DISABLED")
    load_button.grid(row=2, column=0, padx=(0, 120), pady=(10, 0))

    # 创建"重启软件"按钮
    restart_button = ctk.CTkButton(
        setting_frame, text='重启软件', width=20, command=restart_program)
    restart_button.grid(row=3, column=0, padx=(0, 320), pady=(10, 0))

    # 版本号显示1
    version_number_text1 = ctk.CTkLabel(setting_frame, text="当前版本:", width=30)
    version_number_text1.bind("<Button-1>", command=open_web)
    version_number_text1.grid(row=3, column=0, padx=(10, 0), pady=(120, 0))
    # 版本号显示1
    version_number1 = ctk.CTkLabel(
        setting_frame, text=version_number, width=30)
    version_number1.bind("<Button-1>", command=open_web)
    version_number1.grid(row=3, column=0, padx=(120, 0), pady=(120, 0))
    # 版本号显示2
    version_number_text2 = ctk.CTkLabel(setting_frame, text="最新版本:", width=30)
    version_number_text2.bind("<Button-1>", command=open_web)
    version_number_text2.grid(row=4, column=0, padx=(10, 0), pady=(0, 0))
    # 版本号显示2
    version_number2 = ctk.CTkLabel(setting_frame, text=":(", width=30)
    version_number2.bind("<Button-1>", command=open_web)
    version_number2.grid(row=4, column=0, padx=(120, 0), pady=(0, 0))
    # # Fetch version number from GitHub
    if crawl_information:
        version = fetch_readme_version_number()
    else:
        version = "禁用获取"
    # # 更新version_number2的文本为从 Github 获取的版本号
    version_number2.configure(text=version)
    # 更新 version_number2 的文本并设置颜色（对比版本号）
    if version == version_number1.cget("text"):
        version_number2.configure(text=version, text_color="green")
    else:
        version_number2.configure(text=version, text_color="red")

    # 调试窗口标签栏
    image_label_frame = ctk.CTkFrame(
        tab_view.tab("测试窗口"), height=370, width=305)
    image_label_frame.grid(row=1, column=0, sticky='w')
    image_label_frame.grid_propagate(False)
    # 画面开关
    image_label_switch = ctk.CTkSwitch(image_label_frame, text="内部测试窗口(影响性能)", onvalue=True, offvalue=False,
                                       command=update_values)
    image_label_switch.grid(row=0, column=0, padx=(0, 0), sticky='w')
    # 画面显示
    image_label = tk.Label(image_label_frame)
    image_label.grid(row=1, column=0, padx=(0, 0))
    # 帧数显示
    image_label_FPSlabel = ctk.CTkLabel(
        image_label_frame, text="实时FPS：", width=40)  # 初始化时显示的文本
    image_label_FPSlabel.grid(row=2, column=0, padx=(
        0, 0), sticky='w')  # 使用grid布局并靠左对齐

    # 从文件加载设置
    load_settings()
    # 加载设置后更新变量,也是更新GUI上的显示
    update_values()

    # 主循环运行GUI
    root.mainloop()


def update_values(*args):
    global aimbot, lockSpeed, triggerType, arduinoMode, lockKey, lockKey_var, confidence, closest_mouse_dist, closest_mouse_dist_scale, screen_width, screen_height, model_file, aimOffset, draw_center, mouse_Side_Button_Witch, lockSpeed_text, LookSpeed_label_1, test_images_GUI, target_selection_str, prediction_factor_scale, prediction_factor, method_of_prediction, extra_offset_x, extra_offset_y, screenshot_mode, segmented_aiming_switch, stage1_scope, stage1_scope_scale, stage1_intensity, stage1_intensity_scale, stage2_scope, stage2_scope_scale, stage2_intensity, stage2_intensity_scale, aimOffset_Magnification_x, aimOffset_x, mouse_control, max_offset_entry, min_offset_entry, offset_range, enable_random_offset, time_interval, recoil_switch, recoil_interval, recoil_boosted_distance, recoil_boosted_distance_time, recoil_standard_distance, recoil_transition_time, tolerance, tolerance_variable, ignore_colors, automatic_Trigger, mouse_movement_smoothing_switch, predict_model

    # 数值合法判断
    # 1.随机瞄准部位瞄准参数合法性判断
    # 获取默认值
    default_max, default_min = Opt.get('offset_range')
    # 获取输入并转化为浮点数
    try:
        max_value = float(max_offset_entry.get())
        min_value = float(min_offset_entry.get())
    except ValueError:
        messagebox.showerror("错误", "请输入数值")
        max_offset_entry.delete(0, 'end')
        max_offset_entry.insert(0, str(default_max))
        min_offset_entry.delete(0, 'end')
        min_offset_entry.insert(0, str(default_min))
        return
    # 检查数值是否在0-1之间
    if not (0 <= max_value <= 1) or not (0 <= min_value <= 1):
        messagebox.showerror("错误", "数值应在0-1之间")
        max_offset_entry.delete(0, 'end')
        max_offset_entry.insert(0, str(default_max))
        min_offset_entry.delete(0, 'end')
        min_offset_entry.insert(0, str(default_min))
        return
    # 2.颜色忽略输入RGB值合法性
    try:
        ignore_colors = [list(map(int, color.strip('()').split(','))) for color in
                         ignore_colors_variable.get().strip('[]').split('), (')]
    except ValueError:
        Logger.error("颜色输入无效")
        messagebox.showerror("错误", "颜色输入无效，回到默认值")
        ignore_colors = 0, 0, 0  # valor padrão
        ignore_colors_string = ','.join(
            str(e) for e in ignore_colors)  # 变为 '62,203,236' 格式的字符串
        ignore_colors_variable.set(str(ignore_colors_string))  # 设置默认值

    # 数据应用
    Logger.debug("update_values function was called（配置已更新）")
    aimbot = aimbot_var.get()
    lockSpeed = lockSpeed_scale.get()
    triggerType = triggerType_var.get()
    arduinoMode = arduinoMode_var.get()
    lockKey = lockKey_var.get()
    target_selection_str = target_selection_var.get()
    mouse_Side_Button_Witch = mouse_Side_Button_Witch_var.get()
    confidence = confidence_scale.get()
    closest_mouse_dist = closest_mouse_dist_scale.get()
    screen_width = int(screen_width_scale.get())
    screen_height = int(screen_height_scale.get())
    aimOffset_Magnification_x = aimOffset_x_scale.get()
    aimOffset = aimOffset_scale.get()
    draw_center = draw_center_var.get()
    test_images_GUI = image_label_switch.get()
    prediction_factor = prediction_factor_scale.get()
    method_of_prediction = method_of_prediction_var.get()
    mouse_control = mouseMove_var.get()
    predict_model = predict_model_var.get()  # 获取预测模式选项
    stage1_scope = stage1_scope_scale.get()
    stage1_intensity = stage1_intensity_scale.get()
    stage2_scope = stage2_scope_scale.get()
    stage2_intensity = stage2_intensity_scale.get()
    offset_range = [min_value, max_value]  # 随机瞄准部位参数
    enable_random_offset = random_offset_mode_check.get()  # 随机瞄准部位开关
    time_interval = float(offset_time_entry.get())  # 随机瞄准部位切换时间
    automatic_Trigger = automatic_Trigger_var.get()  # 自动扳机开关
    recoil_switch = recoil_var.get()  # 辅助压枪开关
    recoil_interval = float(recoil_interval_entry.get())  # 压枪间隔
    recoil_boosted_distance = float(
        recoil_boosted_distance_entry.get())  # 一阶段单次距离
    recoil_boosted_distance_time = float(
        recoil_boosted_distance_time_entry.get())  # 一阶段时间
    recoil_standard_distance = float(
        recoil_standard_distance_entry.get())  # 二阶段时间
    recoil_transition_time = float(recoil_transition_time_entry.get())  # 缓冲时间
    tolerance = int(tolerance_scale.get())  # 颜色忽略(误差调整)
    mouse_movement_smoothing_switch = smooth_aiming_var.get()  # 平滑瞄准开关

    # 更新显示的数值
    # 更新 lockSpeed_variable
    lockSpeed = round(lockSpeed_scale.get(), 2)
    lockSpeed_variable.set(str(lockSpeed))
    # 更新 confidence_variable
    confidence = round(confidence_scale.get(), 2)
    confidence_variable.set(str(confidence))
    # 更新 closest_mouse_dist_variable
    closest_mouse_dist = int(closest_mouse_dist_scale.get())
    closest_mouse_dist_variable.set(str(closest_mouse_dist))
    # 更新prediction_factor_variable
    prediction_factor = round(prediction_factor_scale.get(), 2)
    prediction_factor_variable.set(str(prediction_factor))
    aimOffset = round(aimOffset_scale.get(), 2)  # 取两位小数
    aimOffset_variable.set(str(aimOffset))
    # 更新 aimOffset_variable_x
    aimOffset_x = round(aimOffset_x_scale.get(), 2)
    aimOffset_variable_x.set(str(aimOffset_x))
    # 更新 screen_width
    screen_width = int(screen_width_scale.get())
    screen_width_scale_variable.set(str(screen_width))
    # 更新 screen_width
    screen_height = int(screen_height_scale.get())
    screen_height_scale_variable.set(str(screen_height))
    # 更新 stage1_scope 显示的数值
    stage1_scope = int(stage1_scope_scale.get())
    stage1_scope_variable.set(str(stage1_scope))
    # 更新 stage1_intensity 显示的数值
    stage1_intensity = round(stage1_intensity_scale.get(), 2)
    stage1_intensity_variable.set(str(stage1_intensity))
    # 更新 stage2_scope 显示的数值
    stage2_scope = int(stage2_scope_scale.get())
    stage2_scope_variable.set(str(stage2_scope))
    # 更新 stage2_intensity 显示的数值
    stage2_intensity = round(stage2_intensity_scale.get(), 2)
    stage2_intensity_variable.set(str(stage2_intensity))
    # 更新颜色忽略显示数值
    tolerance_variable.set(str(tolerance))

    # 触发键值转换
    key = lockKey_var.get()
    lockKey = get_lock_key(key)

    if mouse_control == '飞易来USB':
        check_Ubox_startup()  # 检查飞易来盒子是否存在
    if mouse_control == 'Logitech（待开发）':
        check_Logitech_startup()  # 罗技开发中


def save_settings():  # 保存设置
    global model_file
    Opt.update('aimbot', aimbot_var.get())
    Opt.update('lockSpeed', lockSpeed_scale.get())
    Opt.update('triggerType', triggerType_var.get())
    Opt.update('arduinoMode', arduinoMode_var.get())
    Opt.update('lockKey', lockKey_var.get())
    Opt.update('mouse_Side_Button_Witch', mouse_Side_Button_Witch_var.get())
    Opt.update('confidence', confidence_scale.get())
    Opt.update('closest_mouse_dist', closest_mouse_dist_scale.get())
    Opt.update('screen_width', screen_width_scale.get())
    Opt.update('screen_height', screen_height_scale.get())
    Opt.update('screenshot_mode', screenshot_mode_var.get())
    Opt.update('segmented_aiming_switch', segmented_aiming_switch_var.get())
    Opt.update('aimOffset', aimOffset_scale.get())
    Opt.update('aimOffset_Magnification_x', aimOffset_x_scale.get())
    Opt.update('model_file', model_file)
    Opt.update('prediction_factor', prediction_factor_scale.get())
    Opt.update('method_of_prediction', method_of_prediction_var.get())
    Opt.update('mouse_control', mouseMove_var.get())
    Opt.update('predict_model', predict_model_var.get())  # 预测方法选项
    Opt.update('stage1_intensity', stage1_intensity_scale.get())
    Opt.update('stage1_scope', stage1_scope_scale.get())
    Opt.update('stage2_intensity', stage2_intensity_scale.get())
    Opt.update('stage2_scope', stage2_scope_scale.get())
    Opt.update('enable_random_offset', random_offset_mode_var.get())
    Opt.update('offset_range', [
               float(min_offset_entry.get()), float(max_offset_entry.get())])
    Opt.update('time_interval', float(offset_time_entry.get()))
    Opt.update('recoil_switch', recoil_var.get())
    Opt.update('aimbot', aimbot_var.get())
    Opt.update('lockSpeed', lockSpeed_scale.get())
    Opt.update('triggerType', triggerType_var.get())
    Opt.update('arduinoMode', arduinoMode_var.get())
    Opt.update('lockKey', lockKey_var.get())
    Opt.update('tolerance', tolerance_scale.get())
    ignore_colors_string = ignore_colors_entry.get()
    ignore_colors_list = string_to_list(ignore_colors_string)
    Opt.update('ignore_colors', [ignore_colors_list])
    Opt.save()


def load_prefix_variables():  # 加载前置参数
    global model_file, screenshot_mode, segmented_aiming_switch, crawl_information, offset_range, time_interval, enable_random_offset, deactivate_dxcam
    Logger.debug('Loading prefix variables...')
    try:
        deactivate_dxcam = Opt.get("deactivate_dxcam", False)  # 加载是否禁用加载dxcam
        screenshot_mode = Opt.get("screenshot_mode", False)  # 加载截图方式
        segmented_aiming_switch = Opt.get(
            "segmented_aiming_switch", False)  # 加载分段瞄准开关
        crawl_information = Opt.get("crawl_information", False)  # 加载公告获取开关

        Logger.debug("前置变量加载成功！")
    except Exception as e:
        Logger.error(f'[ERROR] 加载设置时出错: {e}')


def load_settings():  # 加载主程序参数设置
    global model_file, test_window_frame, screenshot_mode, crawl_information, DXcam_screenshot, dxcam_maxFPS, \
        loaded_successfully, stage1_scope, stage1_intensity, stage2_scope, stage2_intensity, segmented_aiming_switch, \
        recoil_interval, recoil_switch, recoil_boosted_distance_time, recoil_boosted_distance, recoil_standard_distance, \
        recoil_transition_time
    Logger.debug('Loading settings...')
    aimbot_var.set(Opt.get('aimbot', True))
    lockSpeed_scale.set(Opt.get('lockSpeed', 0.7))
    triggerType_var.set(Opt.get('triggerType', "\u6309\u4e0b"))
    arduinoMode_var.set(Opt.get('arduinoMode', False))
    lockKey_var.set(Opt.get('lockKey', "\u53f3\u952e"))
    mouse_Side_Button_Witch_var.set(
        Opt.get('mouse_Side_Button_Witch', True))
    method_of_prediction_var.set(Opt.get(
        'method_of_prediction', "\u500d\u7387\u9884\u6d4b"))
    confidence_scale.set(Opt.get('confidence', 0.5))
    predict_model_var.set(Opt.get('predict_model', "禁用预测"))  # 预测方法选项
    # 使用适当的默认值来替换default_value
    prediction_factor_scale.set(Opt.get('prediction_factor', 0.5))
    closest_mouse_dist_scale.set(Opt.get('closest_mouse_dist', 160))
    screen_width_scale.set(Opt.get('screen_width', 360))
    screen_height_scale.set(Opt.get('screen_height', 360))
    aimOffset_scale.set(Opt.get('aimOffset', 0.4))
    aimOffset_x_scale.set(Opt.get('aimOffset_Magnification_x', 0))
    model_file = Opt.get('model_file', None)  # 从文件中加载model_file
    # 更新标签上的文本为加载的文件路径或默认文本
    model_file_label.config(text=model_file or "还未选择模型文件")
    # 从文件中加载test_window_frame的值，如果没有就默认为False
    test_window_frame = Opt.get('test_window_frame', False)
    crawl_information = Opt.get("crawl_information", True)  # 是否联网加载公告
    screenshot_mode = Opt.get(
        "screenshot_mode", False)  # 是否启用DXcam截图模式
    DXcam_screenshot = Opt.get(
        "DXcam_screenshot", 360)  # DXcam截图方式的分辨率
    dxcam_maxFPS = Opt.get('dxcam_maxFPS', 30)  # DXcam截图最大帧率限制
    segmented_aiming_switch = Opt.get(
        'segmented_aiming_switch', False)  # 是否开启分段瞄准模式
    mouseMove_var.set(Opt.get('mouse_control', 'win32'))  # 加载鼠标移动库名称
    stage1_scope_scale.set(Opt.get('stage1_scope', 50))  # 强锁范围(分段瞄准)
    stage1_intensity_scale.set(Opt.get(
        'stage1_intensity', 0.8))  # 强锁力度(分段瞄准)
    stage2_scope_scale.set(Opt.get('stage2_scope', 170))  # 软锁范围(分段瞄准)
    stage2_intensity_scale.set(Opt.get(
        'stage2_intensity', 0.4))  # 软锁力度(分段瞄准)
    random_offset_mode_var.set(Opt.get(
        "enable_random_offset", False))  # 随机瞄准偏移开关
    offset_time_entry.insert(
        0, str(Opt.get("time_interval", 1)))  # 随即瞄准时间间隔
    offset_range = tuple(Opt.get(
        "offset_range", [0, 1]))  # 随机瞄准偏移范围（0-1）
    max_offset_entry.insert(0, str(offset_range[1]))  # 插入瞄准偏移最大值
    min_offset_entry.insert(0, str(offset_range[0]))  # 插入瞄准偏移最小值
    recoil_var.set(Opt.get("recoil_switch", False))  # 压枪模块开关
    recoil_interval_entry.insert(
        0, str(Opt.get("recoil_interval", 0.1)))  # 压枪间隔
    recoil_boosted_distance_entry.insert(
        0, str(Opt.get("recoil_boosted_distance", 5)))  # 一阶段单次距离
    recoil_boosted_distance_time_entry.insert(
        0, str(Opt.get("recoil_boosted_distance_time", 0.5)))  # 一阶段时间
    recoil_standard_distance_entry.insert(
        0, str(Opt.get("recoil_standard_distance", 1)))  # 二阶段单次距离
    recoil_transition_time_entry.insert(
        0, str(Opt.get("recoil_transition_time", 0.2)))  # 缓冲时间
    tolerance_scale.set(Opt.get("tolerance", 50))  # 颜色忽略宽容
    ignore_colors_nested_list = Opt.get(
        "ignore_colors", [[0, 0, 0]])  # 返回嵌套列表，例 [[62, 203, 88]]
    ignore_colors_list = ignore_colors_nested_list[0] if ignore_colors_nested_list else [
        0, 0, 0]  # 提取内部的子列表
    ignore_colors_string = ','.join(
        str(e) for e in ignore_colors_list)  # 转换为 '62, 203, 88' 格式的字符串
    # 颜色忽略指定颜色，将转换后格式的字符串写入ignore_colors_entry
    ignore_colors_entry.insert(0, ignore_colors_string)

    Logger.debug("设置加载成功！")
    loaded_successfully = True  # 加载成功标识符


def smooth_transition(current_value, target_value, progress):
    """
    使用非线性平滑方法实现从慢到快的过渡。
    current_value: 当前值
    target_value: 目标值
    progress: 当前的进度，取值范围在 [0, 1] 之间。值越大，接近目标值。
    """
    non_linear_progress = progress ** 2  # 进度的平方，开始时较慢，随后变快
    return current_value + (target_value - current_value) * non_linear_progress


def predict_aim_position(box_centerx, minBox_width, min_x1, min_x2, previous_centerx, direction, progress=0.6):
    """
    预判处理函数，根据目标移动方向调整目标框中心点的位置。

    参数:
    - box_centerx: 目标框的当前中心x坐标
    - minBox_width: 目标框的宽度
    - min_x1, min_x2: 目标框的左边界和右边界x坐标
    - previous_centerx: 前一帧的中心x坐标
    - direction: 目标移动方向 ("左", "右", "静止")
    - progress: 预测的平滑过渡进度，默认为0.6

    返回:
    - 更新后的box_centerx
    """
    # 定义可调整的预测偏移百分比
    left_offset_percentage = 0.5  # 向左预测偏移百分比(不可修改)
    right_offset_percentage = 0.5  # 向右预测偏移百分比(不可修改)
    prediction_shift = 0.15  # 预测移动的偏移量

    # 平滑处理: 检查方向变化并调整进度
    if (previous_direction == "左" and direction == "右") or (previous_direction == "右" and direction == "左"):
        # 如果检测到方向切换，则减少进度使过渡更平滑
        progress = 0.2  # 可以根据需要调整进度值

    if direction == "左":
        # print("向左预测")
        target_centerx = box_centerx - prediction_shift * minBox_width
        if min_x1 + right_offset_percentage * minBox_width <= target_centerx <= min_x2:
            box_centerx = smooth_transition(
                previous_centerx, target_centerx, progress)
        else:
            box_centerx = target_centerx  # 超出范围时直接使用预测点

    elif direction == "右":
        # print("向右预测")
        target_centerx = box_centerx + prediction_shift * minBox_width
        if min_x1 <= target_centerx <= min_x1 + left_offset_percentage * minBox_width:
            box_centerx = smooth_transition(
                previous_centerx, target_centerx, progress)
        else:
            box_centerx = target_centerx  # 超出范围时直接使用预测点

    elif direction == "静止":
        # print("无预测")
        box_centerx = smooth_transition(
            previous_centerx, box_centerx, progress)

    return box_centerx


def calculate_distances(
        monitor: dict,  # 包含显示器宽度和高度的字典
        results: list,  # 目标检测结果列表
        frame_: np.array,  # 当前处理的帧
        aimbot: bool,  # 是否启用自瞄
        lockSpeed: float,  # 鼠标移动速度
        arduinoMode: bool,  # 是否启用Arduino模式
        lockKey: int,  # 锁定键的代码
        triggerType: str,  # 触发类型
):  # 目标选择逻辑与标识
    global boxes, cWidth, cHeight, extra_offset_x, extra_offset_y, last_offset_time, aimOffset, enable_random_offset, last_recoil_time, counter_id, buffer_tracks, last_updated, locked_id, slow_aim_speed, stop_aim, stop_aim_variety, stop_aim_variety_state, previous_centerx, previous_centery

    minDist = float('inf')  # 初始最小距离设置为无限大
    minBox = None  # 初始最小框设置为None

    # 计算屏幕的中点
    cWidth = monitor["width"] / 2
    cHeight = monitor["height"] / 2

    # 绘制自瞄范围框
    if draw_center:
        if screenshot_mode:  # 如果采用DXcam截图模式则不使用mss的截图大小数据
            cWidth = DXcam_screenshot // 2
            cHeight = DXcam_screenshot // 2

        if segmented_aiming_switch:  # 如果分段瞄准开启，则绘制分段瞄准的范围，否则绘制默认模式范围
            cv2.circle(frame_, (int(cWidth), int(cHeight)),
                       int(stage2_scope), (0, 255, 0), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)),
                       int(stage1_scope), (0, 255, 255), 2)
            cv2.circle(frame_, (int(cWidth), int(cHeight)),
                       radius=5, color=(0, 0, 255), thickness=-1)
        else:
            cv2.circle(frame_, (int(cWidth), int(cHeight)),
                       int(closest_mouse_dist), (0, 255, 0), 2)
            # 在自瞄范围框的中心绘制一个中心点
            cv2.circle(frame_, (int(cWidth), int(cHeight)),
                       radius=5, color=(0, 0, 255), thickness=-1)

    # 压枪模块
    current_time = time.time()
    if current_time - last_recoil_time >= recoil_interval:  # 检查间隔是否已经过了0.01秒
        if recoil_switch:
            recoil()  # 触发 recoil 函数进行反后坐力动作
        last_recoil_time = current_time  # 更新 recoil 的触发时间

    for r in results:
        boxes = r.boxes.xyxy.cpu().numpy()  # 获取框坐标

    # 颜色忽略模块
    filtered_boxes = []
    for box in boxes:
        if filter_color_above_box(frame_, box, ignore_colors, tolerance=tolerance):
            # print("由于忽略了颜色过滤器，因此忽略了框")
            pass
        else:
            filtered_boxes.append(box)

    # 将过滤后的框用于后续处理
    for box in filtered_boxes:
        x1, y1, x2, y2 = box
        box_width = x2 - x1
        box_height = y2 - y1

        # 计算检测到的物体框（BoundingBox）的中心点。
        centerx = (x1 + x2) / 2
        centery = (y1 + y2) / 2

        # 绘制目标中心点
        cv2.circle(frame_, (int(centerx), int(centery)), 5, (0, 255, 255), -1)

        # 获取当前框的ID
        box_id = track_box_id(centerx, centery, box_width, box_height, monitor)
        cv2.putText(frame_, f'ID: {box_id}', (int(centerx), int(centery) - 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                    (255, 255, 0), 2)

        dist = sqrt((cWidth - centerx) ** 2 + (cHeight - centery) ** 2)
        dist = round(dist, 1)

        # 范围设置
        if segmented_aiming_switch:
            if dist < minDist and dist < stage2_scope:
                minDist = dist  # 更新最小距离
                minBox = box  # 更新对应最小距离的框
        else:
            # 比较当前距离和最小距离
            if dist < minDist and dist < closest_mouse_dist:
                minDist = dist  # 更新最小距离
                minBox = box  # 更新对应最小距离的框

        location = (int(centerx), int(centery))
        cv2.putText(frame_, f'dist: {dist}', location,
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # 检查最小距离和最小框是否已更新
    if minBox is not None:
        # 获取当前循环中的最小框的四个坐标
        min_x1, min_y1, min_x2, min_y2 = minBox
        minBox_width = min_x2 - min_x1
        minBox_height = min_y2 - min_y1

        cv2.rectangle(frame_, (int(minBox[0]), int(minBox[1])), (int(
            minBox[2]), int(minBox[3])), (0, 255, 0), 2)  # 最近的框为绿色
        center_text_x = int((minBox[0] + minBox[2]) / 2)
        center_text_y = int((minBox[1] + minBox[3]) / 2)
        location = (center_text_x, center_text_y)
        cv2.putText(frame_, f'dist: {minDist}', location,
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # 随机瞄准偏移
        # 检查是否需要更新aimOffset(随机瞄准偏移)
        if enable_random_offset:
            current_time = time.time()  # 计算时间
            if current_time - last_offset_time >= time_interval:
                aimOffset = random.uniform(*offset_range)
                last_offset_time = current_time
                # print("随机偏移:", aimOffset)

        # 重新计算目标框中点
        box_centerx = (min_x1 + min_x2) / 2
        box_centery = (min_y1 + min_y2) / 2

        # 调用预测函数(新：倍率预测 )
        if predict_model == "自动预测":
            box_centerx = predict_aim_position(
                box_centerx, minBox_width, min_x1, min_x2, previous_centerx, direction)
            previous_centerx = box_centerx
        elif predict_model == "手动预测":
            Logger.debug("开发中...")

        # 计算垂直瞄准偏移
        distance_to_top_border = box_centery - min_y1
        distance_to_left_border = box_centerx - min_x1

        # 最终偏移距离
        aimOffset_y = distance_to_top_border * aimOffset
        aimOffset_x = distance_to_left_border * aimOffset_Magnification_x

        # 绘制偏移后的点
        cv2.circle(frame_, (int(box_centerx - aimOffset_x),
                   int(box_centery - aimOffset_y)), 5, (255, 0, 0), -1)

        # 偏移后的目标位置
        offset_centerx = box_centerx - aimOffset_x
        offset_centery = box_centery - aimOffset_y

        screen_width_entire, screen_height_entire = pyautogui.size()  # 获取屏幕大小
        # 截图区域的宽度和高度
        capture_width = screen_width
        capture_height = screen_height
        # 计算截图区域的左上角坐标 (相对于整个屏幕)
        capture_left = (screen_width_entire - capture_width) // 2
        capture_top = (screen_height_entire - capture_height) // 2
        # 计算目标在整个屏幕中的绝对位置
        target_screen_x = offset_centerx + capture_left
        target_screen_y = offset_centery + capture_top

        # print(f"目标位置（截图区域中）: {offset_centerx}, {offset_centery}")
        # print(f"目标位置（整个屏幕中）: {target_screen_x}, {target_screen_y}")

        # 新的位置与屏幕中心的距离（原始位置）
        centerx = offset_centerx - cWidth
        centery = offset_centery - cHeight

        # 屏幕中心点与偏移后的目标中心点之间的距离
        offset_dist = sqrt((cWidth - offset_centerx) ** 2 +
                           (cHeight - offset_centery) ** 2)
        offset_dist = round(offset_dist, 1)
        # 在偏移后的目标中心点上方显示偏移距离
        offset_location = (int(offset_centerx), int(offset_centery))
        cv2.putText(frame_, f'offset_dist: {offset_dist}',
                    offset_location, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # 是否开启分段瞄准
        if segmented_aiming_switch:
            # 判断距离是否小于 stage1_scope（强锁范围）
            if offset_dist < stage1_scope:  # 强锁范围 stage1_scope
                lockSpeed = stage1_intensity  # 强锁力度 stage1_intensity

            # 判断距离是否在 stage1_scope 和 stage2_scope 之间（软锁范围）
            elif offset_dist < stage2_scope:  # 软锁范围 stage2_scope
                # 计算 lockSpeed，距离越近速度越快，距离越远速度越慢
                # 使用线性插值计算 lockSpeed
                t = (offset_dist - stage1_scope) / \
                    (stage2_scope - stage1_scope)
                lockSpeed = stage1_intensity + t * \
                    (stage2_intensity - stage1_intensity)

        if method_of_prediction == "禁用加速":
            # 计算光标应当从当前位置移动多大的距离以便到达目标位置(禁用预测)
            centerx_no_acceleration = centerx * lockSpeed
            centery_no_acceleration = centery * lockSpeed

            if mouse_movement_smoothing_switch:  # 是否开启鼠标平滑
                # 调用独立的处理函数
                centerx, centery = process_aiming(centerx_no_acceleration, centery_no_acceleration,
                                                  previous_centerx, previous_centery,
                                                  reverse_threshold_x, reverse_threshold_y, smoothing_factor,
                                                  lockSpeed, threshold, slowDownFactor)

                # 更新上一个位置
                previous_centerx = centerx_no_acceleration
                previous_centery = centery_no_acceleration
            else:
                centerx = centerx_no_acceleration
                centery = centery_no_acceleration

        elif method_of_prediction == "倍率加速":

            # 计算额外的加速
            centerx_extra = prediction_factor * abs(centerx)
            centery_extra = prediction_factor * abs(centery)

            # 预测新的瞄准点(预测后位置)
            centerx_predicted = (
                centerx + (centerx_extra if centerx > 0 else -centerx_extra)) * lockSpeed
            centery_predicted = (
                centery + (centery_extra if centery > 0 else -centery_extra)) * lockSpeed

            if mouse_movement_smoothing_switch:  # 是否开启鼠标平滑
                # 调用独立的处理函数
                centerx, centery = process_aiming(centerx_predicted, centery_predicted, previous_centerx, previous_centery,
                                                  reverse_threshold_x, reverse_threshold_y, smoothing_factor, lockSpeed,
                                                  threshold, slowDownFactor)

                # 更新上一个位置
                previous_centerx = centerx_predicted
                previous_centery = centery_predicted

            if not mouse_movement_smoothing_switch:
                centerx = centerx_predicted
                centery = centery_predicted

        # 检查锁定键、Shift 键和鼠标侧键是否按下
        lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
        shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
        xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000

        # 第一种：切换触发
        if triggerType == "切换":
            if aimbot and (win32api.GetKeyState(lockKey) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                match mouse_control:
                    case '飞易来USB':
                        dll.M_MoveR2(ctypes.c_uint64(hdl),
                                     int(centerx), int(centery))
                    case 'win32':
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx),
                                             int(centery), 0, 0)
                    case 'mouse':
                        mouse.move(int(centerx), int(centery), False)
                    case 'Logitech':
                        LG_driver.move_R(int(centerx), int(centery))
                if automatic_Trigger and offset_dist <= 30:
                    AFe.start()
                else:
                    AFe.stop()

        # 第二种：按下触发
        elif triggerType == "按下":
            if aimbot and (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                match mouse_control:
                    case '飞易来USB':
                        dll.M_MoveR2(ctypes.c_uint64(hdl),
                                     int(centerx), int(centery))
                    case 'win32':
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx),
                                             int(centery), 0, 0)
                    case 'mouse':
                        mouse.move(int(centerx), int(centery), False)
                    case 'Logitech':
                        LG_driver.move_R(int(centerx), int(centery))
                if automatic_Trigger and offset_dist <= 30:
                    AFe.start()
                else:
                    AFe.stop()
            elif not (lockKey_pressed or (mouse_Side_Button_Witch and xbutton2_pressed)):
                AFe.stop()

        # 第三种：shift+按下触发
        elif triggerType == "shift+按下":
            if aimbot and ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                match mouse_control:
                    case '飞易来USB':
                        # 如果距离小于15则绝对移动到坐标(一步到位)
                        if offset_dist < 15 and coordinate_movement_switch:
                            dll.M_MoveTo2_D(ctypes.c_uint64(hdl), int(
                                target_screen_x), int(target_screen_y))
                        else:
                            dll.M_MoveR2(ctypes.c_uint64(hdl),
                                         int(centerx), int(centery))
                    case 'win32':
                        win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(centerx),
                                             int(centery), 0, 0)
                    case 'mouse':
                        mouse.move(int(centerx), int(centery), False)
                    case 'Logitech':
                        LG_driver.move_R(int(centerx), int(centery))
                if automatic_Trigger and offset_dist <= 30:
                    AFe.start()
                else:
                    AFe.stop()
            elif not ((lockKey_pressed and shift_pressed) or (mouse_Side_Button_Witch and xbutton2_pressed)):
                AFe.stop()

    return frame_


def recoil():  # 反后坐力
    global recoil_start_time

    # 获取当前时间
    current_time = time.time()

    lockKey_pressed = win32api.GetKeyState(lockKey) & 0x8000
    shift_pressed = win32api.GetKeyState(win32con.VK_SHIFT) & 0x8000
    xbutton2_pressed = win32api.GetKeyState(0x05) & 0x8000
    lbutton_pressed = win32api.GetKeyState(
        win32con.VK_LBUTTON) & 0x8000  # 检查鼠标左键是否按下

    if not lbutton_pressed:
        # 如果鼠标左键没按下，则重置recoil_start_time为None
        recoil_start_time = None
        return

    if recoil_start_time is None:
        # 如果这是第一次反冲（recoil），设置开始时间
        recoil_start_time = current_time

    time_since_recoil_start = current_time - recoil_start_time

    # 判断反冲是在哪个阶段以及执行对应的操作
    if time_since_recoil_start < recoil_boosted_distance_time:
        single_distance = recoil_boosted_distance  # 在第一阶段，使用一阶段的距离（力度较大）
    elif recoil_boosted_distance_time <= time_since_recoil_start < recoil_boosted_distance_time + recoil_transition_time:
        # 在过渡阶段，使用线性插值计算当前的下压力度
        t = (time_since_recoil_start - recoil_boosted_distance_time) / \
            recoil_transition_time
        single_distance = recoil_boosted_distance * \
            (1 - t) + recoil_standard_distance * t
    else:
        single_distance = recoil_standard_distance  # 在第二阶段，使用二阶段的距离（力度较小）

    # 第一种：切换触发
    if triggerType == "切换" and lbutton_pressed:
        if win32api.GetKeyState(lockKey):
            match mouse_control:
                case '飞易来USB':
                    dll.M_MoveR2(ctypes.c_uint64(hdl),
                                 int(0), int(single_distance))
                case 'win32':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(
                        0), int(single_distance), 0, 0)
                case 'mouse':
                    mouse.move(int(0), int(single_distance), False)
                case 'Logitech':
                    LG_driver.move_R(int(0), int(single_distance))

    # 第二种：按下触发
    elif triggerType == "按下" and lbutton_pressed:
        if lockKey_pressed:
            match mouse_control:
                case '飞易来USB':
                    dll.M_MoveR2(ctypes.c_uint64(hdl),
                                 int(0), int(single_distance))
                case 'win32':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(
                        0), int(single_distance), 0, 0)
                case 'mouse':
                    mouse.move(int(0), int(single_distance), False)
                case 'Logitech':
                    LG_driver.move_R(int(0), int(single_distance))

        elif not lockKey_pressed:
            pass

    # 第三种：shift+按下触发
    elif triggerType == "shift+按下" and lbutton_pressed:
        if lockKey_pressed and shift_pressed:
            match mouse_control:
                case '飞易来USB':
                    dll.M_MoveR2(ctypes.c_uint64(hdl),
                                 int(0), int(single_distance))
                case 'win32':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, int(
                        0), int(single_distance), 0, 0)
                case 'mouse':
                    mouse.move(int(0), int(single_distance), False)
                case 'Logitech':
                    LG_driver.move_R(int(0), int(single_distance))

        elif not (lockKey_pressed and shift_pressed):
            pass


def sparse_optical_flow_inference(frame, prev_gray, prev_points, screen_width, screen_height, optical_flow_frame_counter):  # 稀疏流光推理函数
    global direction, direction_cache

    # 灰度化并直方图均衡化
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # 确保帧尺寸匹配
    if prev_gray is not None and prev_gray.shape != gray.shape:
        gray = cv2.resize(gray, (prev_gray.shape[1], prev_gray.shape[0]))

    # 仅每8帧进行一次稀疏光流推理
    if optical_flow_frame_counter % 1 == 0:
        if prev_gray is not None:
            # 检查是否需要重新检测特征点
            if prev_points is None or len(prev_points) < 10:
                prev_points = cv2.goodFeaturesToTrack(
                    prev_gray, maxCorners=300, qualityLevel=0.2, minDistance=5, blockSize=7)

            if prev_points is not None and len(prev_points) > 0:
                prev_points = np.float32(prev_points)

                # 获取截图区域的大小
                monitor = calculate_screen_monitor(screen_width, screen_height)
                width = monitor['width']
                height = monitor['height']

                # 定义中心区域的大小（相对于图像尺寸）
                center_margin_x = 0.4  # X轴方向中心区域的宽度比例
                center_margin_y = 0.4  # Y轴方向中心区域的高度比例

                # 计算中心区域的边界
                center_x_start = int(width * (0.5 - center_margin_x / 2))
                center_x_end = int(width * (0.5 + center_margin_x / 2))
                center_y_start = int(height * (0.5 - center_margin_y / 2))
                center_y_end = int(height * (0.5 + center_margin_y / 2))

                # 过滤掉位于中心区域的特征点
                filtered_points = []
                for point in prev_points:
                    x, y = point.ravel()
                    if not (center_x_start <= x <= center_x_end and center_y_start <= y <= center_y_end):
                        filtered_points.append(point)

                prev_points = np.array(filtered_points, dtype=np.float32)

                try:
                    # 计算稀疏光流
                    next_points, status, err = cv2.calcOpticalFlowPyrLK(
                        prev_gray, gray, prev_points, None)

                    # 检查光流计算结果
                    if next_points is None or status is None or len(next_points) < 10:
                        # 重新检测特征点
                        prev_points = cv2.goodFeaturesToTrack(
                            gray, maxCorners=300, qualityLevel=0.2, minDistance=5, blockSize=7)
                        next_points, status, err = cv2.calcOpticalFlowPyrLK(
                            prev_gray, gray, prev_points, None)

                    if next_points is not None and status is not None:
                        good_new = next_points[status == 1]
                        good_old = prev_points[status == 1]

                        if len(good_new) > 0:
                            movement = good_new - good_old
                            dx = np.mean(movement[:, 0])
                            dy = np.mean(movement[:, 1])

                            # 设置判定“静止”的阈值区间
                            stationary_threshold = 0.05  # 可以根据需要快速调整这个值
                            # 判定为“静止”的逻辑
                            if -stationary_threshold <= dx <= stationary_threshold and -stationary_threshold <= dy <= stationary_threshold:
                                result_direction = "静止"
                            else:
                                angle = np.arctan2(dy, dx) * 180 / np.pi
                                if -90 <= angle < 90:
                                    result_direction = "左"
                                else:
                                    result_direction = "右"

                            # 将结果存入缓存
                            direction_cache.append(result_direction)
                            if len(direction_cache) > 5:
                                direction_cache.pop(0)
                                # 打印缓存内容
                                # print(f"当前缓存内容: {direction_cache}")

                            # 计算出现次数最多的方向
                            direction = max(set(direction_cache),
                                            key=direction_cache.count)
                            # 打印出现次数最多的方向
                            # print(f"出现次数最多的方向: {direction}")

                            # print(f"预测人物的移动方向: {direction}")

                        prev_points = good_new.reshape(-1, 1, 2)

                except cv2.error as e:
                    # 处理cv2.calcOpticalFlowPyrLK中发生的错误
                    Logger.error(f"光流计算错误: {e}")
                    prev_points = cv2.goodFeaturesToTrack(
                        gray, maxCorners=300, qualityLevel=0.2, minDistance=5, blockSize=7)

    return gray, prev_points


def main_program_loop(model):  # 主程序流程代码
    global start_time, gc_time, closest_mouse_dist, lockSpeed, triggerType, arduinoMode, lockKey, confidence, run_threads, aimbot, image_label, test_images_GUI, target_selection, target_selection_str, target_mapping, target_selection_var, prediction_factor, should_break, readme_content, last_screenshot_mode_update, optical_flow_frame_counter

    # 初始化帧数计时器（帧数计算）
    frame_counter = 0
    start_time = time.time()

    prev_gray = None  # 存储前一帧的灰度图像
    prev_points = None  # 存储前一帧的特征点
    optical_flow_frame_counter = 0  # 光流帧计数器

    # 等待加载完成再开启DXcam截图确保DXcam接收的参数正确
    while True:
        time.sleep(2)
        Logger.debug("正在等待加载完成")
        if loaded_successfully:
            if deactivate_dxcam:
                Logger.info("已禁用DXcam")
                break
            if not deactivate_dxcam:
                Logger.debug("尝试开启DXcam...")
                DXcam()
                break

    # 如果选择mss截图则关闭DXcam
    if deactivate_dxcam is False:
        if not screenshot_mode:
            Logger.info("已选择MSS截图，关闭dxcam")
            camera.stop()

    if test_window_frame:
        # 创建窗口并设置 flag 为 cv2.WINDOW_NORMAL（外部）
        cv2.namedWindow('frame', cv2.WINDOW_NORMAL)
        # 在主循环中显示图像之前，设置窗口属性，置顶
        cv2.setWindowProperty('frame', cv2.WND_PROP_TOPMOST, 1)

    # 循环捕捉屏幕
    while run_threads:

        # 截图区域大小
        monitor = calculate_screen_monitor(screen_width, screen_height)

        try:
            target_selection = target_mapping[target_selection_str]
        except KeyError:
            Logger.debug(
                f"Key {target_selection_str} not found in target_mapping.（加载中）")

        # 截图方式选择
        if not screenshot_mode:
            # 每2秒打印一次当前截图模式
            current_time = time.time()
            if current_time - last_screenshot_mode_update > 10:
                Logger.debug("当前截图模式：mss")
                last_screenshot_mode_update = current_time
            frame = capture_screen(monitor, sct)  # mss截图方式
        elif screenshot_mode:
            # 每2秒打印一次当前截图模式
            current_time = time.time()
            if current_time - last_screenshot_mode_update > 10:
                Logger.debug("当前截图模式：dxcam")
                last_screenshot_mode_update = current_time
            frame = camera.get_latest_frame()  # DXcam截图方式

        # 调用稀疏流光推理函数
        prev_gray, prev_points = sparse_optical_flow_inference(
            frame, prev_gray, prev_points, screen_width, screen_height, optical_flow_frame_counter)

        # 增加光流帧计数器
        optical_flow_frame_counter += 1

        # ---------------------------------------------------------------------------
        # 检测和跟踪对象（推理部分）
        results = model.predict(frame, save=False, conf=confidence, half=half_precision_model, agnostic_nms=True, iou=0.7, classes=[
            target_selection], device="cuda:0", verbose=False, save_txt=False)
        # ---------------------------------------------------------------------------
        # 绘制结果
        frame_ = results[0].plot()

        # 计算距离 并 将最近的目标绘制为绿色边框
        try:
            frame_ = calculate_distances(
                monitor, results, frame_, aimbot, lockSpeed, arduinoMode, lockKey, triggerType)
        except TypeError as e:
            # 当 TypeError 出现时
            Logger.error('[ERROR]未知数值错误')
            Logger.error(handle_exception(e))

        # 获取并显示帧率
        try:
            end_time = time.time()
            frame_, frame_counter, start_time = update_and_display_fps(
                frame_, frame_counter, start_time, end_time)
        except NameError:
            Logger.error("帧率显示失败(加载中)")

        if test_window_frame:
            # 图像调试窗口（外部cv2.imshow）
            should_break = display_debug_window(frame_)

        if test_images_GUI:
            # 图像调试窗口（内部GUI）
            screen_width_1, screen_height_1 = pyautogui.size()
            desired_size = get_desired_size(screen_width_1, screen_height_1)
            img = cv2.cvtColor(frame_, cv2.COLOR_BGR2RGB)
            im = Image.fromarray(img)
            im_resized = im.resize(desired_size)
            imgtk = ImageTk.PhotoImage(image=im_resized)
            image_label.config(image=imgtk)
            image_label.image = imgtk

        if test_window_frame:
            if should_break:
                break

        # 每30秒进行一次gc
        if time.time() - gc_time >= 30:
            gc.collect()
            gc_time = time.time()

    pass


def stop_program():  # 停止子线程
    global run_threads, Thread_to_join, root
    camera.stop()
    run_threads = False
    if Thread_to_join:
        Thread_to_join.join()  # 等待子线程结束
    if root is not None:
        root.quit()
        root.destroy()  # 销毁窗口
    try:
        Logger.info("关闭端口:" + str(dll.M_Close(ctypes.c_uint64(hdl)) == 0))  # 关闭端口
    except OSError as e:
        if 'access violation reading' in str(e):
            Logger.warn("关闭U盘端口错误")
        else:
            Logger.error("未知错误类型：", e)  # 输出未知错误类型的提示
            Logger.error(handle_exception(e))
            raise e  # 如果不是我们期望的错误类型，重新引发异常

    os._exit(0)  # 强制结束进程


def restart_program():  # 重启软件
    python = sys.executable
    os.execl(python, python, *sys.argv)


def Initialization_parameters():  # 初始化参数

    model = load_model_file()
    aimbot = True
    lockSpeed = 1
    arduinoMode = False
    triggerType = "按下"
    lockKey = 0x02
    aimOffset = 25
    screen_width = 640
    screen_height = 640

    return (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width,
            screen_height)


# ---------------------------------------main-------------------------------------------------------------------------
if __name__ == "__main__":
    load_DLL()  # 加载控制盒DLL文件，并开启端口
    time.sleep(0.3)
    load_lg_dll()  # 加载罗技DLL文件，并测试

    # 优先级设置
    p = psutil.Process(os.getpid())
    p.nice(psutil.REALTIME_PRIORITY_CLASS)

    # 加载前置变量
    load_prefix_variables()

    # 爬取版本号与公告
    crawl_information_by_github()

    # 初始化参数
    (model, aimbot, lockSpeed, arduinoMode, triggerType, lockKey, aimOffset, screen_width, screen_height
     ) \
        = Initialization_parameters()

    freeze_support()

    # 创建并启动子线程1用于运行main_program_loop
    thread1 = threading.Thread(target=main_program_loop, args=(model,))
    thread1.start()

    # 启动 GUI(运行主程序)
    create_gui_tkinter()

    # 等待main_program_loop线程结束后再完全退出。
    thread1.join()
