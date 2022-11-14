from enums import LRow
import database
import gi
import json

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import Gdk


class PytagWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Pytag")
        self.set_border_width(10)

        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.add(self.grid)

        self.conn = database.connect()

        # Model - (id_rola, title, performer, album, track, year, genre)
        self.liststore = Gtk.ListStore(int, str, str, str, str, int, str)
        cur = self.conn.cursor()
        for row in self.conn.cursor().execute("SELECT * from rolas"):
            self.liststore.append(database.rola_to_list(cur, row))

        self.filter = self.liststore.filter_new()
        self.filter.set_visible_func(self.filter_func)
        self.current_filter = None

        self.sort = Gtk.TreeModelSort(model=self.filter)
        self.view = Gtk.TreeView(model=self.sort)
        self.view.connect("key-release-event", self.on_key_release)

        for title, idx in zip(
                ["Title", "Artist/Band", "Album", "Track", "Year"],
                [LRow.title, LRow.performer, LRow.album, LRow.track, LRow.year]
        ):
            renderer = Gtk.CellRendererText(editable=True)
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_resizable(True)
            column.set_sort_column_id(idx)
            self.view.append_column(column)

        # genres.json was retrieved with mid3v2 -L (included with mutagen)
        with open("genres.json") as f:
            genre_list = json.load(f)
        genre_model = Gtk.ListStore(str)
        for genre in genre_list:
            genre_model.append([genre])

        renderer = Gtk.CellRendererCombo(model=genre_model, editable=True,
                                         text_column=0)
        column = Gtk.TreeViewColumn("Genre", renderer, text=LRow.genre)
        column.set_sort_column_id(LRow.genre)
        self.view.append_column(column)

        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.grid.attach(self.scrollable_treelist, 0, 0, 8, 10)
        self.scrollable_treelist.add(self.view)

        self.show_all()

    def sort_iter_to_list_iter(self, sort_iter):
        filter_iter = self.sort.convert_iter_to_child_iter(sort_iter)
        return self.filter.convert_iter_to_child_iter(filter_iter)

    def on_key_release(self, view, key):
        if key.keyval == Gdk.KEY_Delete:
            model, treeiter = view.get_selection().get_selected()
            if treeiter is not None:
                treeiter = self.sort_iter_to_list_iter(treeiter)
                database.delete_rola(self.conn.cursor(),
                                     self.liststore[treeiter][LRow.id_rola])
                self.liststore.remove(treeiter)

    def filter_func(self, model, treeiter, data):
        if self.current_filter is None:
            return True


def start():
    win = PytagWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
