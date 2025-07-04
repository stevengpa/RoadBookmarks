import sublime, sublime_plugin
import threading
import os, re
import json

ROAD_BOOKMARKS_FILE = os.path.join(sublime.packages_path(), "User", "road_bookmarks_data.json")

class RoadBookmarksDB():
	def __init__(self):
		self.running = False
		self.interval = 300 # 5 minutes

	def start_auto_cleaner(self):
		self.running = True
		self._bookmarks_cleaner()

	def stop_auto_cleaner(self):
		self.running = False

	def _bookmarks_cleaner(self):
		if not self.running:
			return

		bookmarks = self.load()
		change = False

		for path in list(bookmarks.keys()):
			if not os.path.exists(path):
				del bookmarks[path]
				change = True

			if os.path.exists(path) and not bookmarks[path]:
				del bookmarks[path]
				change = True

		if change:
			self._write(bookmarks)

		sublime.set_timeout_async(self._bookmarks_cleaner, int(self.interval * 1000))

	def save(self, view):
		file_name = view.file_name()
		if not file_name:
			return

		# Read view bookmarks
		regions = view.get_regions("bookmarks")
		view_enriched_bookmarks = []
		for region in regions:
			pos = region.a
			row, col = view.rowcol(pos)
			view_enriched_bookmarks.append({
	        "pos": pos,
	        "row": row,
	        "col": col
	    })

		# Load disk bookmarks
		bookmarks = self.load()
		# Assign file bookmarks
		bookmarks[file_name] = view_enriched_bookmarks
		# Write file bookmarks
		self._write(bookmarks)

	def load(self):
		if not os.path.exists(ROAD_BOOKMARKS_FILE):
			return {}

		with open(ROAD_BOOKMARKS_FILE, "r", encoding="utf-8") as file_bookmarks:
			return json.load(file_bookmarks)

	def _write(self, bookmarks):
		with open(ROAD_BOOKMARKS_FILE, "w", encoding="utf-8") as file_bookmarks:
			json.dump(bookmarks, file_bookmarks, indent=2)

	def restore(self, view):
		file_name = view.file_name()	
		if not file_name:
			return

		bookmarks = self.load()
		if file_name not in bookmarks:
			return

		file_bookmarks = bookmarks[file_name]
		regions = [sublime.Region(b["pos"], b["pos"]) for b in file_bookmarks]
		view.add_regions("bookmarks", regions, "bookmark", "bookmark", sublime.HIDDEN)

	def has_bookmarks_change(self, view):
		file_name = view.file_name()	
		if not file_name:
			return False

		bookmarks = self.load().get(file_name)
		if not bookmarks:
			return False

		saved_pos = [b["pos"] for b in bookmarks]
		view_pos = [r.a for r in view.get_regions("bookmarks")]

		return saved_pos != view_pos

road_bookmarks_db = RoadBookmarksDB()

class RoadBookmarksEventListener(sublime_plugin.EventListener):
	def on_pre_close(self, view):
		road_bookmarks_db.save(view)

	def on_load_async(self, view):
		road_bookmarks_db.restore(view)

	def on_post_save_async(self, view):
		road_bookmarks_db.save(view)

class RoadBookmarksWatcher():
	def __init__(self):
		self.running = False
		self.interval = 1

	def start(self):
		self.running = True
		self.start_bookmarks_watch()

	def stop(self):
		self.running = False

	def start_bookmarks_watch(self):
		if not self.running:
			return

		for window in sublime.windows():
			for view in window.views():
				if road_bookmarks_db.has_bookmarks_change(view):
					road_bookmarks_db.save(view)
					# print(f"[RoadBookmarks] Bookmarks changed in: {view.file_name()}")

		sublime.set_timeout_async(self.start_bookmarks_watch, int(self.interval * 1000))

road_bookmarks_watcher = RoadBookmarksWatcher()

class RoadBookmarksPanelCommand(sublime_plugin.WindowCommand):
    bookmark_locations = []
    debugger = True

    def run(self):
        items = []
        self.bookmark_locations = []

        bookmarks = road_bookmarks_db.load()
        for file_path, entries in bookmarks.items():
            if not os.path.exists(file_path):
                continue

            file_name = os.path.basename(file_path)

            view = self.window.find_open_file(file_path)

            for entry in entries:
                pos = entry.get("pos")
                row = entry.get("row", 0)
                col = entry.get("col", 0)

                # Safe fallback for line content preview
                line_content = "(loading...)"
                if view and not view.is_loading():
                    try:
                        line_content = view.substr(view.line(pos)).strip()
                    except Exception:
                        pass

                label = f"{file_name}:{row + 1}"
                items.append([label, line_content])
                self.bookmark_locations.append((file_path, pos))

        if items:
            self.window.show_quick_panel(items, self.go_there, sublime.MONOSPACE_FONT)
        else:
            self.window.show_quick_panel(["No bookmarks found"], None, sublime.MONOSPACE_FONT)

    def go_there(self, index):
        if index < 0 or index >= len(self.bookmark_locations):
            return

        file_path, pos = self.bookmark_locations[index]

        def on_loaded(view):
            region = sublime.Region(pos, pos)
            view.sel().clear()
            view.sel().add(region)
            view.show_at_center(region)
            self.window.focus_view(view)

        # Try using encoded location to force full tab open + jump
        dummy_view = self.window.new_file()  # temp view to use rowcol safely
        dummy_view.set_scratch(True)         # won't prompt to save
        try:
            row, col = dummy_view.rowcol(pos)
        finally:
            self.window.focus_view(dummy_view)
            self.window.run_command("close_file")

        encoded_location = f"{file_path}:{row + 1}:{col + 1}"
        view = self.window.open_file(encoded_location, sublime.ENCODED_POSITION)
        sublime.set_timeout_async(lambda: self.wait_for_load(view, pos, on_loaded), 100)

    def wait_for_load(self, view, pos, callback, tries=10):
        if not view or tries <= 0:
            return
        if view.is_loading():
            sublime.set_timeout_async(lambda: self.wait_for_load(view, pos, callback, tries - 1), 100)
        else:
            callback(view)


def plugin_loaded():
	road_bookmarks_watcher.start()
	road_bookmarks_db.start_auto_cleaner()

def plugin_unloaded():
	road_bookmarks_watcher.stop()
	road_bookmarks_db.stop_auto_cleaner()
