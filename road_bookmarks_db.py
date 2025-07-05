import sublime
import os
import json


class RoadBookmarksDB():
	ROAD_BOOKMARKS_FOLDER = os.path.join(sublime.packages_path(), "User", "RoadBookmarks")
	ROAD_BOOKMARKS_FILE = os.path.join(ROAD_BOOKMARKS_FOLDER, "road_bookmarks_data.json")

	def __init__(self):
		self.running = False
		self.interval = 300  # 5 minutes
		self._last_known_positions = {}  # buffer_id -> [positions]

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

		sublime.set_timeout(self._bookmarks_cleaner, int(self.interval * 1000))

	def save(self, view):
		file_name = view.file_name()
		if not file_name:
			return

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

		bookmarks = self.load()
		bookmarks[file_name] = view_enriched_bookmarks
		self._write(bookmarks)

	def load(self):
		if not os.path.exists(self.ROAD_BOOKMARKS_FILE):
			return {}

		try:
			with open(self.ROAD_BOOKMARKS_FILE, "r", encoding="utf-8") as file_bookmarks:
				return json.load(file_bookmarks)
		except Exception as e:
			print("RoadBookmarksDB.load() error reading JSON:", e)
			return {}

	def _write(self, bookmarks):
		self._init_db_folder()
		try:
			with open(self.ROAD_BOOKMARKS_FILE, "w", encoding="utf-8") as file_bookmarks:
				json.dump(bookmarks, file_bookmarks, indent=2)
		except Exception as e:
			print("RoadBookmarksDB._write() error writing JSON:", e)

	def _init_db_folder(self):
		try:
			if not os.path.exists(self.ROAD_BOOKMARKS_FOLDER):
				os.makedirs(self.ROAD_BOOKMARKS_FOLDER)
		except Exception as e:
			print("RoadBookmarksDB._write() error creating RoadBookmarks folder:", e)

	def restore(self, view):
		file_name = view.file_name()
		if not file_name:
			return

		bookmarks = self.load()
		if file_name not in bookmarks:
			return

		file_bookmarks = bookmarks[file_name]
		if not file_bookmarks:
			return

		regions = [sublime.Region(b["pos"], b["pos"]) for b in file_bookmarks]
		view.add_regions("bookmarks", regions, "bookmark", "bookmark", sublime.HIDDEN)

	def has_bookmarks_change(self, view):
		buffer_id = view.buffer_id()
		current_pos = [r.a for r in view.get_regions("bookmarks")]

		if buffer_id not in self._last_known_positions:
			self._last_known_positions[buffer_id] = current_pos
			return bool(current_pos)  # treat new bookmarks as a change

		last_pos = self._last_known_positions[buffer_id]
		if last_pos != current_pos:
			self._last_known_positions[buffer_id] = current_pos
			return True

		return False

	# Optional: call this in watcher loop to avoid memory leaks
	def cleanup_closed_views(self):
		open_buffer_ids = [v.buffer_id() for w in sublime.windows() for v in w.views()]
		for bid in list(self._last_known_positions.keys()):
			if bid not in open_buffer_ids:
				del self._last_known_positions[bid]


# Shared DB Instance
shared_db = RoadBookmarksDB()
