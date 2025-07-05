import sublime_plugin
from . import road_bookmarks_db

class RoadBookmarksEventListener(sublime_plugin.EventListener):
	def on_pre_close(self, view):
		if not view.file_name():
			return

		try:
			road_bookmarks_db.shared_db.save(view)
		except Exception as e:
			print("RoadBookmarksEventListener on_pre_close error:", e)

	def on_load_async(self, view):
		if not view.file_name():
			return

		try:
			road_bookmarks_db.shared_db.restore(view)
		except Exception as e:
			print("RoadBookmarksEventListener on_load_async error:", e)

	def on_post_save_async(self, view):
		if not view.file_name():
			return

		try:
			road_bookmarks_db.shared_db.save(view)
		except Exception as e:
			print("RoadBookmarksEventListener on_post_save_async error:", e)
