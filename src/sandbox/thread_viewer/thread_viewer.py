import dearpygui.dearpygui as dpg
from typing import Dict, List, Tuple, Optional, Callable
import threading
import time
import random
from collections import deque
from enum import Enum
import contextlib

class ThreadState(Enum):
    CREATED = 1
    RUNNING = 2
    WAITING = 3
    TERMINATED = 4

class ManagedThread:
    def __init__(self, name: str, target: Callable, args: Tuple = (), kwargs: Dict = None):
        self.name = name
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.thread = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.state = ThreadState.CREATED
        self.last_state = None
        self.lock = threading.Lock()

    def start(self):
        with self.lock:
            if self.thread is None or not self.thread.is_alive():
                self.stop_event.clear()
                self.pause_event.set()
                self.thread = threading.Thread(
                    target=self._thread_wrapper,
                    name=self.name,
                    daemon=True
                )
                self.thread.start()
                return self.thread
            return None

    def _thread_wrapper(self):
        try:
            self._update_state(ThreadState.RUNNING)
            self.target(self.stop_event, self.pause_event, *self.args, **self.kwargs)
        finally:
            self._update_state(ThreadState.TERMINATED)

    def _update_state(self, new_state: ThreadState):
        with self.lock:
            if self.state != new_state:
                self.last_state = self.state
                self.state = new_state

    def pause(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                self._update_state(ThreadState.WAITING)
                self.pause_event.clear()

    def resume(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                self._update_state(ThreadState.RUNNING)
                self.pause_event.set()

    def stop(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                self.stop_event.set()
                self.pause_event.set()

class ThreadMonitor:
    def __init__(self, max_history=500) -> None:
        self.thread_data: Dict[int, Tuple[str, deque]] = {}
        self.managed_threads: Dict[str, ManagedThread] = {}
        self.lock = threading.RLock()
        self.max_history = max_history

    def add_thread(self, thread: threading.Thread) -> None:
        with self.lock:
            self.thread_data[thread.ident] = (
                thread.name,
                deque(maxlen=self.max_history)
            )
            self._append_state(thread.ident, ThreadState.CREATED)

    def _append_state(self, thread_id: int, state: ThreadState):
        if thread_id in self.thread_data:
            history = self.thread_data[thread_id][1]
            if not history or history[-1][1] != state:
                history.append((time.time(), state))

    def update_state(self, thread_id: int, state: ThreadState) -> None:
        with self.lock:
            self._append_state(thread_id, state)

    def create_managed_thread(self, name: str, target: Callable, args: Tuple = (), kwargs: Dict = None) -> ManagedThread:
        with self.lock:
            managed_thread = ManagedThread(name, target, args, kwargs)
            self.managed_threads[name] = managed_thread
            return managed_thread

    def get_thread_snapshot(self):
        with self.lock:
            return {
                tid: (data[0], list(data[1]))
                for tid, data in self.thread_data.items()
            }

    def get_active_threads(self):
        with self.lock:
            return [
                (name, mt) 
                for name, mt in self.managed_threads.items()
                if mt.thread and mt.thread.is_alive()
            ]

class ThreadVisualizer:
    def __init__(self, max_threads=20):
        self.max_threads = max_threads
        self.monitor = ThreadMonitor()
        self.ui_pool = []
        self.active_items = set()
        self.state_colors = {
            ThreadState.CREATED: (50, 200, 50),
            ThreadState.RUNNING: (50, 100, 255),
            ThreadState.WAITING: (255, 165, 0),
            ThreadState.TERMINATED: (255, 50, 50)
        }
        self.last_update = time.time()
        self.update_interval = 0.3
        self.timeline_range = 60.0
        self.vertical_scale = 40.0
        self.setup_ui()

    def setup_ui(self):
        dpg.create_context()
        self._create_themes()
        
        with dpg.window(label="Thread Monitor", width=1280, height=720):
            with dpg.group(horizontal=True):
                dpg.add_slider_float(
                    label="Time Range",
                    default_value=60.0,
                    min_value=10.0,
                    max_value=300.0,
                    callback=lambda s, a: setattr(self, 'timeline_range', a)
                )
                dpg.add_slider_float(
                    label="Row Height",
                    default_value=40.0,
                    min_value=20.0,
                    max_value=100.0,
                    callback=lambda s, a: setattr(self, 'vertical_scale', a)
                )
            
            with dpg.child_window(width=1260, height=500, tag="main_area"):
                dpg.add_text("Thread Timeline", tag="timeline_title")
                with dpg.drawlist(width=1240, height=400, tag="timeline_canvas"):
                    pass
                
            with dpg.group(horizontal=True):
                dpg.add_button(label="Create Simple", callback=self._create_simple_thread)
                dpg.add_button(label="Create Long", callback=self._create_long_thread)
                dpg.add_button(label="Create Random", callback=self._create_random_thread)
                dpg.add_button(label="Clear Terminated", callback=self._clear_terminated)

            with dpg.child_window(width=1260, height=200):
                dpg.add_text("Active Threads:")
                with dpg.table(tag="thread_table", header_row=True):
                    dpg.add_table_column(label="Thread Name")
                    dpg.add_table_column(label="State")
                    dpg.add_table_column(label="Controls")

        dpg.create_viewport(title='Thread Monitor', width=1280, height=720)
        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _create_themes(self):
        for state in ThreadState:
            with dpg.theme(tag=f"theme_{state.name}") as theme:
                with dpg.theme_component(dpg.mvButton):
                    dpg.add_theme_color(dpg.mvThemeCol_Button, self.state_colors[state] + (255,))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, self.state_colors[state] + (200,))
                    dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, self.state_colors[state] + (150,))

    def _recycle_ui_elements(self, required: int):
        while len(self.ui_pool) < required:
            with dpg.table_row(parent="thread_table", tag=f"row_{len(self.ui_pool)}") as row:
                dpg.add_text(f"thread_{len(self.ui_pool)}")
                dpg.add_button(label="State", tag=f"state_{len(self.ui_pool)}")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Pause", tag=f"pause_{len(self.ui_pool)}")
                    dpg.add_button(label="Resume", tag=f"resume_{len(self.ui_pool)}")
                    dpg.add_button(label="Stop", tag=f"stop_{len(self.ui_pool)}")
            self.ui_pool.append(row)

    def _update_controls(self):
        active_threads = self.monitor.get_active_threads()
        self._recycle_ui_elements(len(active_threads))

        for i, (name, mt) in enumerate(active_threads):
            row = self.ui_pool[i]
            dpg.configure_item(f"row_{i}", show=True)
            dpg.set_value(f"state_{i}", mt.state.name)
            dpg.bind_item_theme(f"state_{i}", f"theme_{mt.state.name}")

            def make_callback(func, name=name):
                return lambda: func(name)

            for btn in [f"pause_{i}", f"resume_{i}", f"stop_{i}"]:
                dpg.configure_item(btn, callback=make_callback(getattr(self, f"_{btn.split('_')[0]}_thread")))

        for i in range(len(active_threads), len(self.ui_pool)):
            dpg.configure_item(f"row_{i}", show=False)

    def _create_simple_thread(self):
        self._create_thread(
            target=self._simple_task,
            name=f"Simple_{time.time_ns()}"
        )

    def _create_long_thread(self):
        self._create_thread(
            target=self._long_task,
            name=f"Long_{time.time_ns()}"
        )

    def _create_random_thread(self):
        self._create_thread(
            target=self._random_task,
            name=f"Random_{time.time_ns()}"
        )

    def _create_thread(self, target: Callable, name: str):
        if len(self.monitor.get_active_threads()) >= self.max_threads:
            return

        def thread_wrapper(stop_event, pause_event):
            thread_id = threading.get_ident()
            self.monitor.add_thread(threading.current_thread())
            try:
                target(stop_event, pause_event)
            finally:
                self.monitor.update_state(thread_id, ThreadState.TERMINATED)

        mt = self.monitor.create_managed_thread(name, thread_wrapper)
        mt.start()

    def _simple_task(self, stop_event, pause_event):
        thread_id = threading.get_ident()
        for i in range(5):
            if stop_event.is_set():
                return
            self.monitor.update_state(thread_id, ThreadState.RUNNING)
            time.sleep(1)
            while not pause_event.is_set():
                self.monitor.update_state(thread_id, ThreadState.WAITING)
                time.sleep(0.1)

    def _long_task(self, stop_event, pause_event):
        thread_id = threading.get_ident()
        for i in range(20):
            if stop_event.is_set():
                return
            self.monitor.update_state(thread_id, ThreadState.RUNNING)
            time.sleep(1)
            while not pause_event.is_set():
                self.monitor.update_state(thread_id, ThreadState.WAITING)
                time.sleep(0.1)

    def _random_task(self, stop_event, pause_event):
        thread_id = threading.get_ident()
        for i in range(random.randint(5, 15)):
            if stop_event.is_set():
                return
            self.monitor.update_state(thread_id, ThreadState.RUNNING)
            time.sleep(random.uniform(0.5, 1.5))
            while not pause_event.is_set():
                self.monitor.update_state(thread_id, ThreadState.WAITING)
                time.sleep(0.1)

    def _pause_thread(self, name: str):
        with contextlib.suppress(KeyError):
            self.monitor.managed_threads[name].pause()

    def _resume_thread(self, name: str):
        with contextlib.suppress(KeyError):
            self.monitor.managed_threads[name].resume()

    def _stop_thread(self, name: str):
        with contextlib.suppress(KeyError):
            self.monitor.managed_threads[name].stop()

    def _clear_terminated(self):
        pass

    def render_loop(self):
        while dpg.is_dearpygui_running():
            current_time = time.time()
            if current_time - self.last_update >= self.update_interval:
                self._update_timeline()
                self._update_controls()
                self.last_update = current_time
            dpg.render_dearpygui_frame()

    def _update_timeline(self):
        dpg.delete_item("timeline_canvas", children_only=True)
        snapshot = self.monitor.get_thread_snapshot()
        current_time = time.time()
        time_start = current_time - self.timeline_range

        for row, (tid, (name, states)) in enumerate(snapshot.items()):
            y_base = 50 + row * self.vertical_scale
            dpg.draw_text((10, y_base - 10), name, size=15, parent="timeline_canvas")

            for (start, state), (end, _) in zip(states, states[1:] + [(current_time, None)]):
                if end < time_start or start > current_time:
                    continue

                x_start = max(start, time_start)
                x_end = min(end, current_time)
                
                x1 = 200 + (x_start - time_start) / self.timeline_range * 1000
                x2 = 200 + (x_end - time_start) / self.timeline_range * 1000
                width = x2 - x1

                if width > 1:
                    dpg.draw_rectangle(
                        (x1, y_base),
                        (x2, y_base + self.vertical_scale - 5),
                        fill=self.state_colors[state] + (64,),
                        color=self.state_colors[state] + (255,),
                        thickness=1,
                        parent="timeline_canvas"
                    )

if __name__ == "__main__":
    visualizer = ThreadVisualizer()
    visualizer.render_loop()
    dpg.destroy_context()
