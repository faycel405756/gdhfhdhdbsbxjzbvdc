# launcher_concurrent.py
import os
import sys
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Dict, Optional

# ======== اضبط هنا قائمة السكربتات ========
# يمكن لكل عنصر أن يكون:
# - مسار لملف .py (نسبي أو مطلق) مثل "scripts/main1.py"
# - أو dict: {"cmd": "main1.py", "cwd": "scripts/main1_dir", "python_exe": "/path/to/python"}
scripts = [
    
    
    "source2.py",
    "source3.py",
    "source4.py",
    "source5.py",
    "source6.py",
    "source7.py",
    "source8.py",
    "source9.py",
    "source10.py",
    "source11.py",
    "source12.py",
    "source13.py"
]
# =========================================

# اعدادات سلوكية
RESTART_ON_FAILURE = True
MAX_RESTARTS = 3   # عدد المحاولات القصوى لإعادة التشغيل لكل سكربت (0 = لا إعادة تشغيل)
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

class ManagedProcess:
    def __init__(self, entry):
        # Normalize entry
        if isinstance(entry, str):
            self.cmd = entry
            self.cwd = None
            self.python_exe = None
        else:
            self.cmd = entry.get("cmd")
            self.cwd = entry.get("cwd")
            self.python_exe = entry.get("python_exe")
        self.path = Path(self.cmd) if self.cmd else None
        if not self.path.is_absolute():
            # افتراض: إذا أعطيت اسم ملف فقط، فهو نسبي إلى cwd launcher
            self.path = Path.cwd() / self.path
        self.cwd = Path(self.cwd) if self.cwd else self.path.parent
        self.python_exe = self.python_exe or sys.executable
        self.proc: Optional[subprocess.Popen] = None
        self.restarts = 0
        self.stop_requested = False
        self.logfile = LOG_DIR / f"{self.path.stem}.log"

    def make_env(self):
        env = os.environ.copy()
        cwd_str = str(self.cwd.resolve())
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join([cwd_str, existing]) if existing else cwd_str
        env.setdefault("PYTHONUNBUFFERED", "1")
        return env

    def start(self):
        # command: نستخدم مفسر البايثون لملفات .py لضمان نفس البيئة
        if self.path.suffix == ".py":
            cmd_list = [self.python_exe, str(self.path.name)]
        else:
            # لو أعطيت أمر آخر، نفترض أنه سطر أوامر كامل
            cmd_list = self.cmd.split()
        # افتح العملية ضمن cwd المحدد
        self.proc = subprocess.Popen(
            cmd_list,
            cwd=str(self.cwd),
            env=self.make_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        self._start_reader_thread()
        print(f"[LAUNCHER] started {self.path.name} (pid={self.proc.pid}) in {self.cwd}")

    def _start_reader_thread(self):
        def reader():
            assert self.proc and self.proc.stdout
            with open(self.logfile, "a", encoding="utf-8") as f:
                while True:
                    line = self.proc.stdout.readline()
                    if line:
                        prefix = f"[{self.path.name}] "
                        # اطبع للترمينال واكتب في اللوق
                        print(prefix + line.rstrip())
                        f.write(line)
                        f.flush()
                    else:
                        # تحقق إذا انتهت العملية
                        if self.proc.poll() is not None:
                            # اقرأ المتبقي
                            rest = self.proc.stdout.read()
                            if rest:
                                for l in rest.splitlines():
                                    print(f"[{self.path.name}] {l}")
                                    f.write(l + "\n")
                            break
                        time.sleep(0.05)
        t = threading.Thread(target=reader, daemon=True)
        t.start()

    def stop(self):
        self.stop_requested = True
        if self.proc and self.proc.poll() is None:
            try:
                print(f"[LAUNCHER] terminating {self.path.name} (pid={self.proc.pid})")
                self.proc.terminate()
                # انتظر قليلاً ثم اجبر الإيقاف إن لزم
                try:
                    self.proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    print(f"[LAUNCHER] killing {self.path.name} (pid={self.proc.pid})")
                    self.proc.kill()
            except Exception as e:
                print(f"[LAUNCHER] خطأ عند إنهاء {self.path.name}: {e}")

def run_all(managed_entries: List[ManagedProcess]):
    # بدء كل العمليات الأولية
    for m in managed_entries:
        if not m.path.exists():
            print(f"[LAUNCHER] تحذير: لم يتم العثور على {m.path}")
            continue
        m.start()

    try:
        # حلقة مراقبة: نراقب حالات الانتهاء ونعيد تشغيل إذا مطلوب
        while True:
            all_dead = True
            for m in managed_entries:
                if m.proc is None:
                    continue
                rc = m.proc.poll()
                if rc is None:
                    all_dead = False
                    continue
                # العملية انتهت (rc != None)
                print(f"[LAUNCHER] {m.path.name} انتهى (exit={rc})")
                if m.stop_requested:
                    continue
                # قرار إعادة التشغيل
                if RESTART_ON_FAILURE and (MAX_RESTARTS == 0 or m.restarts < MAX_RESTARTS):
                    m.restarts += 1
                    print(f"[LAUNCHER] إعادة تشغيل {m.path.name} (attempt {m.restarts})")
                    m.start()
                    all_dead = False
                else:
                    print(f"[LAUNCHER] لن يعاد تشغيل {m.path.name} (restarts={m.restarts})")
            if all_dead:
                # كل العمليات انتهت نهائياً
                print("[LAUNCHER] كل العمليات انتهت. الخروج.")
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("[LAUNCHER] تم طلب الإيقاف بواسطة المستخدم. إنهاء كل العمليات...")
        for m in managed_entries:
            m.stop()

if __name__ == "__main__":
    managed = [ManagedProcess(s) for s in scripts]
    run_all(managed)
