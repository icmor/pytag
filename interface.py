from enums import LRow
import database
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


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

        for title, idx in zip(
                ["Title", "Artist/Band", "Album", "Track", "Year", "Genre"],
                [LRow.title, LRow.performer, LRow.album, LRow.track,
                 LRow.year, LRow.genre]
        ):
            renderer = Gtk.CellRendererText(editable=True)
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_resizable(True)
            column.set_sort_column_id(idx)
            self.view.append_column(column)

        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.grid.attach(self.scrollable_treelist, 0, 0, 8, 10)
        self.scrollable_treelist.add(self.view)

        self.show_all()


    def filter_func(self, model, treeiter, data):
        if self.current_filter is None:
            return True


def start():
    win = PytagWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
