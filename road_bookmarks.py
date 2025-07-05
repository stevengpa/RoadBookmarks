import sublime, sublime_plugin
import os, re
import threading

from . import road_bookmarks_db
from . import road_bookmarks_watcher

# Bookmarks Watcher
bookmarks_watcher = road_bookmarks_watcher.RoadBookmarksWatcher()


class RoadBookmarksPanelCommand(sublime_plugin.WindowCommand):
    bookmark_locations = []

    def run(self):
        db = road_bookmarks_db.shared_db
        items = []
        self.bookmark_locations = []

        bookmarks = db.load()
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
                line_content = "(open file...)"
                if view and not view.is_loading():
                    try:
                        line_content = view.substr(view.line(pos)).strip()
                    except Exception:
                        pass

                label = "{}:{}".format(file_name, row + 1)
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

        encoded_location = "{}:{}:{}".format(file_path, row + 1, col + 1)
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
    db = road_bookmarks_db.shared_db
    db.start_auto_cleaner()
    bookmarks_watcher.start()

def plugin_unloaded():
    db = road_bookmarks_db.shared_db
    db.stop_auto_cleaner()
    bookmarks_watcher.stop()
