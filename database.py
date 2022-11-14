from gi.repository import GLib
from enums import DRow, LRow
import datetime as dt
import mutagen.easyid3
import mutagen
import sqlite3
import pathlib
import logging


def connect():
    """ Return a sqlite3.Connection to the pytag db "~/.cache/pytag/songs.db"
    Create the database if it doesn't exist.
    """
    cache_dir = pathlib.Path(GLib.get_user_cache_dir()).joinpath("pytag")
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)
    db = cache_dir.joinpath("songs.db")
    try:
        if not db.exists():
            conn = sqlite3.connect(db)
            setup(conn.cursor())
        else:
            conn = sqlite3.connect(db)
    except sqlite3.Error as err:
        logging.error("Error in seting up the database")
        raise err
    return conn


def setup(cur):
    """ Setup the database with the needed tables:
    types, performers, persons, groups, albums, rolas, and in_group.
    """
    # Tables
    cur.execute("""
    CREATE TABLE types (
    id_type		INTEGER PRIMARY KEY,
    description		TEXT
    );
    """)
    cur.execute("INSERT INTO types VALUES(0, 'Person')")
    cur.execute("INSERT INTO types VALUES(1, 'Group')")
    cur.execute("INSERT INTO types VALUES(2, 'Unknown')")

    cur.execute("""
    CREATE TABLE performers (
    id_performer	INTEGER PRIMARY KEY,
    id_type		INTEGER,
    name 		TEXT,
    FOREIGN KEY 	(id_type) REFERENCES types(id_type)
    );
    """)

    cur.execute("""
    CREATE TABLE persons (
    id_person		INTEGER PRIMARY KEY,
    stage_name 		TEXT,
    real_name 		TEXT,
    birth_date 		TEXT,
    death_date 		TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE groups (
    id_group		INTEGER PRIMARY KEY,
    name		TEXT,
    start_date 		TEXT,
    end_date 		TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE albums (
    id_album		INTEGER PRIMARY KEY,
    path		TEXT,
    name 		TEXT,
    year		INTEGER
    );
    """)

    cur.execute("""
    CREATE TABLE rolas (
    id_rola		INTEGER PRIMARY KEY,
    id_performer	INTEGER,
    id_album 		INTEGER,
    path		TEXT,
    title		TEXT,
    track		TEXT,
    year		INTEGER,
    genre		TEXT,
    FOREIGN KEY         (id_performer) REFERENCES performers(id_performer),
    FOREIGN KEY         (id_album) REFERENCES albums(id_album)
    );
    """)

    cur.execute("""
    CREATE TABLE in_group (
    id_person		INTEGER,
    id_group		INTEGER,
    PRIMARY KEY		(id_person, id_group),
    FOREIGN KEY		(id_person) REFERENCES persons(id_person),
    FOREIGN KEY		(id_group) REFERENCES groups(id_group)
    );
    """)

    # Triggers
    cur.execute("""
    CREATE TRIGGER performers_on_delete AFTER DELETE on rolas
    WHEN NOT EXISTS(SELECT 1 from rolas WHERE id_performer = OLD.id_performer)
    BEGIN
    DELETE from performers WHERE id_performer = OLD.id_performer;
    END;""")
    cur.execute("""
    CREATE TRIGGER performers_on_update AFTER UPDATE of id_performer on rolas
    WHEN NOT EXISTS(SELECT 1 from rolas WHERE id_performer = OLD.id_performer)
    BEGIN
    DELETE from performers WHERE id_performer = OLD.id_performer;
    END;""")

    cur.execute("""
    CREATE TRIGGER albums_on_delete AFTER DELETE on rolas
    WHEN NOT EXISTS(SELECT 1 from rolas WHERE id_album = OLD.id_album)
    BEGIN
    DELETE from albums WHERE id_album = OLD.id_album;
    END;""")
    cur.execute("""
    CREATE TRIGGER albums_on_update AFTER UPDATE of id_album on rolas
    WHEN NOT EXISTS(SELECT 1 from rolas WHERE id_album = OLD.id_album)
    BEGIN
    DELETE from albums WHERE id_album = OLD.id_album;
    END;""")

    cur.connection.commit()


def add_performer(cur, performer):
    """ Adds a performer to table performers, and returns
    its primary key. If performer already exists it only returns the
    primary key. Expects a sqlite3.Cursor and a list with the name
    of the performer. Returns a list with the primary key.
    """
    id_performer = cur.execute(
        "SELECT id_performer from performers WHERE name = ?;",
        performer).fetchone()
    if not id_performer:
        cur.execute(
            "INSERT into performers(id_type, name) VALUES(2, ?)",
            performer)
        cur.connection.commit()
        id_performer = cur.execute(
            "SELECT id_performer from performers WHERE name = ?;",
            performer).fetchone()
    return list(id_performer)


def add_album(cur, album, year):
    """ Adds an album to albums table, and returns
    its primary key. If album already exists it only returns the
    primary key. Expects a sqlite3.Cursor and a list with the name
    of the album and another list with its year.
    Returns a list with the primary key as its only element.
    """
    id_album = cur.execute(
        "SELECT id_album from albums WHERE"
        "(name = ?) AND (year = ?);",
        album + year).fetchone()
    if not id_album:
        cur.execute(
            "INSERT into albums(name, year) VALUES(?, ?)",
            album + year)
        cur.connection.commit()
        id_album = cur.execute(
            "SELECT id_album from albums WHERE"
            "(name = ?) AND (year = ?);",
            album + year).fetchone()
    return list(id_album)


def add_song(cur, file):
    """ Adds a song to the database, any tag that is empty will have
    the corresponding column assigned to "Unknown" or 0 in the case of
    track number. Expects a sqlite3.Cursor and a valid audio file.
    """
    song = mutagen.easyid3.EasyID3(file)
    path = [str(file)]
    title = info if (info := song.get("title")) is not None else ["Unknown"]
    genre = info if (info := song.get("genre")) is not None else ["Unknown"]
    track = (info if (info := song.get("tracknumber")) is not None
             else ['0'])
    year = ([int(info[0])] if (info := song.get("date")) is not None
            else [dt.date.today().year])

    if (performer := song.get("artist")) is not None:
        id_performer = add_performer(cur, performer)
    else:
        performer = ["Unknown"]
        id_performer = [None]

    if (album := song.get("album")) is not None:
        id_album = add_album(cur, album, year)
    else:
        album = ["Unknown"]
        id_album = [None]

    if not cur.execute("SELECT 1 from rolas WHERE path = ?;", path).fetchone():
        cur.execute("""
        INSERT into rolas(
        id_performer,
        id_album,
        path,
        title,
        track,
        year,
        genre
        ) VALUES(?, ?, ?, ?, ?, ?, ?)
        """, id_performer + id_album + path + title + track + year + genre)
        cur.connection.commit()


def add_songs(cur, files=pathlib.Path.home().joinpath("Music").rglob("*")):
    """  Add songs to the database by calling add_song on each valid file.
    Expects a sqlite3.Cursor object and a list of pathlib.Path objects.
    """
    for file in files:
        if file.is_file() and mutagen.File(file) is not None:
            add_song(cur, file)


def rola_to_list(cur, drow):
    """ Takes a sqlite3.Cursor and a tuple representing a row in table
    rolas. Returns a list representing a row for the liststore model
    (id_rola, id_performer, id_album, path, title, track, year, genre)
    -> [id_rola, title, performer, album, track, year, genre]
    """
    lrow = []
    lrow.insert(LRow.id_rola, drow[DRow.id_rola])
    lrow.insert(LRow.title, drow[DRow.title])
    lrow.insert(LRow.track, drow[DRow.track])
    lrow.insert(LRow.year, drow[DRow.year])
    lrow.insert(LRow.genre, drow[DRow.genre])

    performer, album = get_performer_album(cur, drow)
    lrow.insert(LRow.performer, performer)
    lrow.insert(LRow.album, album)
    return lrow


def delete_rola(cur, id_rola):
    """ Deletes a row from rolas based on id_rola.
    """
    cur.execute("DELETE from rolas WHERE id_rola = ?;", (id_rola,))
    cur.connection.commit()


def update_field(cur, id_rola, column, value):
    """ Updates column in row based on id_rola.
    Expects a sqlite3.Cursor and the new value.
    """
    if column == LRow.performer:
        column = "id_performer"
        value = add_performer(cur, (value,))[0]
    elif column == LRow.album:
        column = "id_album"
        year = cur.execute("SELECT year from rolas where id_rola = ?;",
                           (id_rola,)).fetchone()
        value = add_album(cur, (value,), year)[0]
    else:
        column = LRow(column).name
    query = "UPDATE rolas SET " + column + " = ? WHERE id_rola = ?;"
    cur.execute(query, (value, id_rola))
    cur.connection.commit()


def get_performer_album(cur, row):
    performer = cur.execute(
        "SELECT name from performers WHERE id_performer = ?",
        (row[DRow.id_performer],)).fetchone()[0]
    album = cur.execute("SELECT name from albums WHERE id_album = ?",
                        (row[DRow.id_album],)).fetchone()[0]
    return performer, album


def update_tags(cur, id_rola, column):
    """ Updates a file's tags based on the corresponding
    column and row in rolas. Expects a sqlite3.Cursor, id_rola and
    column number.
    """
    row = cur.execute("SELECT * from rolas WHERE id_rola = ?",
                      (id_rola,)).fetchone()
    song = mutagen.easyid3.EasyID3(pathlib.Path(row[DRow.path]))
    if column == LRow.title:
        song['title'] = row[DRow.title]
    elif column == LRow.track:
        song['tracknumber'] = row[DRow.track]
    elif column == LRow.year:
        song['date'] = str(row[DRow.year])
    elif column == LRow.genre:
        song['genre'] = row[DRow.genre]
    else:
        performer, album = get_performer_album(cur, row)
        if column == LRow.performer:
            song['artist'] = performer
        elif column == LRow.album:
            song['album'] = album
    song.save()


if __name__ == '__main__':
    conn = connect()
    add_songs(conn.cursor())
