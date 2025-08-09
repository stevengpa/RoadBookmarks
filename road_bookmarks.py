import sublime, sublime_plugin
import os
import sqlite3

class RoadBookmarksDB():
    def __init__(self):
        self.ROAD_BOOKMARKS_FOLDER = None
        self.ROAD_BOOKMARKS_FILE = None

    def start(self):
        self.create_bookmarks_table()

    def create_bookmarks_table(self):
        if not self.ROAD_BOOKMARKS_FILE:
            return

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                conn.cursor().execute('''
                    CREATE TABLE IF NOT EXISTS bookmarks (
                        file_path TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        pos INT NOT NULL,
                        row INT NOT NULL,
                        col INT NOT NULL,
                        UNIQUE(file_path, row)
                    )
                ''')
        except Exception as e:
            print('[create_bookmarks_table] Error:', e)

    def bookmarks(self):
        if not self.ROAD_BOOKMARKS_FILE:
            return []

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookmarks')
                return cursor.fetchall()
        except Exception as e:
            print('[bookmarks] Error:', e)
            return []

    def bookmarksByFilePath(self, file_path: str):
        if not self.ROAD_BOOKMARKS_FILE:
            return []

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM bookmarks WHERE file_path = ?', (file_path,))
                return cursor.fetchall()
        except Exception as e:
            print('[bookmarks by file_path] Error:', e)
            return []

    def store(self, file_path: str, file_name: str, pos: int, row: int, col: int):
        if not self.ROAD_BOOKMARKS_FILE:
            return

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                conn.cursor().execute(
                    'INSERT INTO bookmarks (file_path, file_name, pos, row, col) VALUES (?, ?, ?, ?, ?)',
                    (file_path, file_name, pos, row, col)
                )
                conn.commit()
            return True
        except Exception as e:
            print('[store bookmark] Error:', e)
            return False

    def exists(self, file_path: str, row: int):
        if not self.ROAD_BOOKMARKS_FILE:
            return

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM bookmarks WHERE file_path = ? AND row = ?', (file_path, row))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            print('[exists bookmark] Error:', e)
            return False

    def delete(self, file_path: str, row: str):
        if not self.ROAD_BOOKMARKS_FILE:
            return

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                conn.cursor().execute(
                    'DELETE FROM bookmarks WHERE file_path = ? AND row = ?',
                    (file_path, row)
                )
                conn.commit()
            return True
        except Exception as e:
            print('[delete bookmark] Error:', e)
            return False

    def deleteByFilePath(self, file_path: str):
        if not self.ROAD_BOOKMARKS_FILE:
            return

        try:
            with sqlite3.connect(self.ROAD_BOOKMARKS_FILE) as conn:
                conn.cursor().execute(
                    'DELETE FROM bookmarks WHERE file_path = ?', (file_path,)
                )
                conn.commit()
            return True
        except Exception as e:
            print('[delete bookmarks by file_path] Error:', e)
            return False


# Shared DB Instance
shared_db = RoadBookmarksDB()


class RoadBookmarksEventListener(sublime_plugin.EventListener):
    def on_pre_close(self, view):
        if not view.file_name():
            return

        try:
            shared_db.deleteByFilePath(view.file_name())
            bookmarks = self.view_bookmarks(view)
            self.store_bookmarks(bookmarks)
        except Exception as e:
            print("[on_pre_close] Error:", e)

    def on_load_async(self, view):
        if not view.file_name():
            return

        try:
            bookmarks = shared_db.bookmarksByFilePath(view.file_name())
            self.add_bookmarks(view, bookmarks)
        except Exception as e:
            print("[on_load_async] Error:", e)

    def on_post_save_async(self, view):
        if not view.file_name():
            return

        try:
            shared_db.deleteByFilePath(view.file_name())
            bookmarks = self.view_bookmarks(view)
            self.store_bookmarks(bookmarks)
        except Exception as e:
            print("[on_post_save_async] Error:", e)

    def on_post_text_command(self, view, command_name, args):
        if command_name in ("toggle_bookmark", "clear_bookmarks"):
            if not view.file_name():
                return

            try:
                shared_db.deleteByFilePath(view.file_name())
                bookmarks = self.view_bookmarks(view)
                self.store_bookmarks(bookmarks)
            except Exception as e:
                print("[on_post_text_command] Error:", e)

    def add_bookmarks(self, view, bookmarks):
        regions = []

        for bookmark in bookmarks:
            pos = bookmark[2]
            regions.append(sublime.Region(pos, pos))

        view.add_regions("bookmarks", regions, "bookmark", "bookmark", sublime.HIDDEN)

    def store_bookmarks(self, bookmarks):
        for bookmark in bookmarks:
            shared_db.store(
                bookmark['file_path'],
                bookmark['file_name'],
                bookmark['pos'],
                bookmark['row'],
                bookmark['col'],
            )

    def view_bookmarks(self, view):
        file_name = view.file_name()
        if not file_name:
            return []

        regions = view.get_regions("bookmarks")
        view_enriched_bookmarks = []

        for region in regions:
            pos = region.a
            row, col = view.rowcol(pos)
            view_enriched_bookmarks.append({
                "file_path": file_name,
                "file_name": os.path.basename(view.file_name()),
                "pos": pos,
                "row": row,
                "col": col
            })

        return view_enriched_bookmarks

class RoadBookmarksBasePanelCommand(sublime_plugin.WindowCommand):
    bookmark_locations = []

    def get_bookmarks(self):
        return []

    def run(self):
        items = []
        self.bookmark_locations = []

        bookmarks = self.get_bookmarks()
        for bookmark in bookmarks:
            file_path = bookmark[0]
            file_name = bookmark[1]
            pos = bookmark[2]
            row = bookmark[3]
            col = bookmark[4]

            if not os.path.exists(file_path):
                continue

            view = self.window.find_open_file(file_path)

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

class RoadBookmarksPanelCommand(RoadBookmarksBasePanelCommand):
    def get_bookmarks(self):
        return shared_db.bookmarks()


def plugin_loaded():
    shared_db.ROAD_BOOKMARKS_FOLDER = os.path.join(
      sublime.packages_path(), "User", "RoadBookmarks"
    )
    shared_db.ROAD_BOOKMARKS_FILE = os.path.join(
        shared_db.ROAD_BOOKMARKS_FOLDER, "road_bookmarks_data.db"
    )
    shared_db.start()

def plugin_unloaded():
    pass
