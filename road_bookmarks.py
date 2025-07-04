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

		if change:
			self._write(bookmarks)

		sublime.set_timeout_async(self._bookmarks_cleaner, int(self.interval * 1000))

	def save(self, view):
		file_name = view.file_name()
		if not file_name:
			return

		# Read view bookmarks
		view_bookmarks = [region.a for region in view.get_regions("bookmarks")]
		# Load disk bookmarks
		bookmarks = self.load()
		# Assign file bookmarks
		bookmarks[file_name] = view_bookmarks
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
		regions = [sublime.Region(pos, pos) for pos in file_bookmarks]
		view.add_regions("bookmarks", regions, "bookmark", "bookmark", sublime.HIDDEN)

	def has_bookmarks_change(self, view):
		file_name = view.file_name()	
		if not file_name:
			return

		bookmarks = self.load()
		if file_name not in bookmarks:
			return

		file_bookmarks = bookmarks[file_name]
		view_bookmarks = [region.a for region in view.get_regions("bookmarks")]

		return file_bookmarks != view_bookmarks

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

		all_files = list(filter(None, map(lambda f : f.file_name(), sublime.active_window().views())))
		self.debug("all_files", all_files)

		common_prefix = os.path.commonprefix(all_files)
		self.debug("common_prefix", common_prefix)

		for view in sublime.active_window().views():
			prefix = ""
			if view.name():
				prefix=view.name()+":"
			elif view.file_name():
				prefix=view.name()+":"
				if prefix.startswith(common_prefix):
					prefix = prefix[len(common_prefix)]

			for region in view.get_regions("bookmarks"):
				row,_=view.rowcol(region.a)
				line=re.sub('/\\s+', ' ', view.substr(view.line(region))).strip()
				items.append([prefix+str(row+1), line])
				self.bookmark_locations.append((view, region))

			if len(items) > 0:
				sublime.active_window().show_quick_panel(items, self.go_there, sublime.MONOSPACE_FONT)
			else:
				sublime.active_window().show_quick_panel(["Empty bookmarks"], None, sublime.MONOSPACE_FONT)

	def go_there(self, i):
		if i < 0 or i >= len(self.bookmark_locations):
			return

		view, region = self.bookmark_locations[i]
		sublime.active_window().focus_view(view)
		view.show_at_center(region)
		view.sel().clear()
		view.sel().add(region)

	def debug(self, title, obj):
		if self.debugger:
			print("-------- " + title + " ---------")
			print(obj)
			print("----- End of " + title + " -----")

def plugin_loaded():
	road_bookmarks_watcher.start()
	road_bookmarks_db.start_auto_cleaner()

def plugin_unloaded():
	road_bookmarks_watcher.stop()
	road_bookmarks_db.stop_auto_cleaner()
