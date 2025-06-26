import tkinter as tk
from tkinter.scrolledtext import ScrolledText
import threading
import os
import psutil
import pystray
from PIL import Image, ImageDraw
import winpty as pywinpty

class PMHQTrayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("llonebot.exe 控制台输出")
        self.text = ScrolledText(root, width=80, height=30, state='disabled', font=("Consolas", 10))
        self.text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.proc = None
        self.thread = None
        self.start_button = tk.Button(root, text="启动 llonebot.exe", command=self.start_process)
        self.start_button.pack(pady=(0,10))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.tray_icon = None
        self.is_tray = False
        self.root.bind('<Unmap>', self.on_minimize)
        self.create_tray_icon()

    def start_process(self):
        if self.proc is not None:
            return  # 已经启动
        exe_path = os.path.join(os.getcwd(), "llonebot.exe")
        if not os.path.exists(exe_path):
            self.append_text("未找到 llonebot.exe\n")
            return
        try:
            # 使用 pywinpty.PtyProcess 启动伪终端
            self.pty = pywinpty.PtyProcess.spawn([exe_path])
            self.encoding = "utf-8"
        except Exception as e:
            self.append_text(f"启动进程时出错: {e}\n")
            self.pty = None
            return
        self.thread = threading.Thread(target=self.read_output, daemon=True)
        self.thread.start()
        self.start_button.config(state=tk.DISABLED)
        self.append_text("llonebot.exe 已启动...\n")

    def read_output(self):
        try:
            while True:
                data = self.pty.read(1024)
                if not data:
                    break
                self.append_text(data)
        except Exception as e:
            self.append_text(f"\n读取输出时发生错误: {e}\n")
        # 进程结束后，重置状态
        self.append_text("\nllonebot.exe 进程已结束。\n")
        self.pty = None
        if self.start_button.winfo_exists():
            self.start_button.config(state=tk.NORMAL)


    def append_text(self, text):
        if not self.text.winfo_exists():
            return
        self.text.config(state='normal')
        self.text.insert(tk.END, text)
        self.text.see(tk.END)
        self.text.config(state='disabled')

    def on_close(self):
        # 隐藏窗口而非直接关闭，交由 exit_app 处理
        self.hide_window()

    def create_tray_icon(self):
        # 创建一个五角星图标
        image = Image.new('RGB', (64, 64), color=(0, 128, 255))
        d = ImageDraw.Draw(image)
        # 五角星顶点坐标
        from math import sin, cos, pi
        cx, cy, r1, r2 = 32, 32, 24, 10
        points = []
        for i in range(10):
            angle = pi/2 + i * pi/5
            r = r1 if i % 2 == 0 else r2
            x = cx + r * cos(angle)
            y = cy - r * sin(angle)
            points.append((x, y))
        d.polygon(points, fill=(255,255,255))
        
        # --- 主要修改在这里 ---
        menu = (
            # 设置'显示'为默认操作，这样左键单击托盘图标就会执行它
            pystray.MenuItem('显示', self.show_window, default=True),
            pystray.MenuItem('退出', self.exit_app)
        )
        # ---------------------

        self.tray_icon = pystray.Icon('llonebot', image, 'llonebot 托盘', pystray.Menu(*menu))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def on_minimize(self, event):
        # 当窗口最小化时，也隐藏到托盘
        if self.root.state() == 'iconic' and not self.is_tray:
            self.hide_window()

    def hide_window(self):
        self.is_tray = True
        self.root.withdraw()
        if self.tray_icon is None or not self.tray_icon.visible:
            self.create_tray_icon()

    def show_window(self, icon=None, item=None):
        self.is_tray = False
        self.root.after(0, self.root.deiconify)

    def exit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        if self.proc is not None and self.proc.poll() is None:
            try:
                parent = psutil.Process(self.proc.pid)
                children = parent.children(recursive=True)
                for child in children:
                    try:
                        child.terminate()
                    except psutil.NoSuchProcess:
                        pass
                gone, alive = psutil.wait_procs(children, timeout=3)
                try:
                    parent.terminate()
                    parent.wait(3)
                except psutil.NoSuchProcess:
                    pass
            except psutil.NoSuchProcess:
                pass # 进程可能已经自己退出了
            except Exception as e:
                print(f"关闭进程时出错: {e}")
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = PMHQTrayApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
