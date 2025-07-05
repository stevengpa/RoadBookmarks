import sublime
from . import road_bookmarks_db

class RoadBookmarksWatcher():
	def __init__(self):
		self.running = False
		self.interval = 1 # second

	def start(self):
		self.running = True
		self._start_bookmarks_watch()

	def stop(self):
		self.running = False

	def _start_bookmarks_watch(self):
		if not self.running:
			return

		for window in sublime.windows():
			for view in window.views():
				try:
					if road_bookmarks_db.shared_db.has_bookmarks_change(view):
						road_bookmarks_db.shared_db.save(view)
				except Exception as e:
					print("Error checking bookmarks in view:", e)

		sublime.set_timeout_async(self._start_bookmarks_watch, int(self.interval * 1000))
