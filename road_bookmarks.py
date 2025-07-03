import sublime
import sublime_plugin


def plugin_loaded():
	print("Version:      " + sublime.version())
	print("Platform:     " + sublime.platform())
	print("Architecture: " + sublime.arch())
	print("Channel:      " + sublime.channel())
	print("U. Packages:  " + sublime.packages_path())
	print("I. Packages:  " + sublime.installed_packages_path())
	print('My plugin just loaded')

def plugin_unloaded():
	print('My plugin just unloaded')

class RoadBookmarsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		self.view.insert(edit, 0, "Hello, World!")
