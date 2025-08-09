# Road Bookmarks

Sublimet Text plugin that enhance the native Sublime Text bookmarks feature by persisting the information and making them accesible in a global scope through a Window Panel for easy navigation.

You can find the storage of the bookmarks positions in the following path `...\Packages\User\RoadBookmarks\road_bookmarks_db.json`

### Usage
You can access the plugin by pression on Mac `cmd+p` or Win/Linux `ctrl+p`, then type `Road Bookmarks: Open Panel`

```json
[
  {
    "caption": "Road Bookmarks: Open Panel",
    "command": "road_bookmarks_panel"
  }
]
```

### Key Bindings
Add the follwing key binding to your configuration:

```json
[
    { "keys": ["ctrl+shift+b", "a"], "command": "road_bookmarks_global_panel" }
]
```