import sublime
import os
import json


class RoadBookmarksDB():
	ROAD_BOOKMARKS_FILE = os.path.join(sublime.packages_path(), "User", "road_bookmarks_data.json")

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
		if not os.path.exists(self.ROAD_BOOKMARKS_FILE):
			return {}

		try:
			with open(self.ROAD_BOOKMARKS_FILE, "r", encoding="utf-8") as file_bookmarks:
				return json.load(file_bookmarks)
		except Exception as e:
			print("RoadBookmarksDB.load() error reading JSON:", e)
			return {}

	def _write(self, bookmarks):
		try:
			with open(self.ROAD_BOOKMARKS_FILE, "w", encoding="utf-8") as file_bookmarks:
				json.dump(bookmarks, file_bookmarks, indent=2)
		except Exception as e:
			print("RoadBookmarksDB._write() error writing JSON:", e)

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
		file_name = view.file_name()	
		if not file_name:
			return False

		bookmarks = self.load().get(file_name)
		if not bookmarks:
			return False

		saved_pos = [b["pos"] for b in bookmarks]
		view_pos = [r.a for r in view.get_regions("bookmarks")]

		return saved_pos != view_pos

# Shared DB Instance
shared_db = RoadBookmarksDB()
