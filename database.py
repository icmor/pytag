from gi.repository import GLib
import datetime as dt
import sqlite3
import pathlib
import logging
import mutagen


def connect():
    """ Return a sqlite3.Connection to the pytag db "~/.cache/pytag/songs.db"
    Create the database if it doesn't exist.
    """
    cache_dir = pathlib.Path(GLib.get_user_cache_dir()).joinpath("pytag")
    if not cache_dir.exists():
        cache_dir.mkdir(parents=True)
    db = cache_dir.joinpath("songs.db")
    try:
        conn = setup(sqlite3.connect(db)) if not db.exists() \
            else sqlite3.connect(db)
    except sqlite3.Error as err:
        logging.error("Error in seting up the database")
        raise err
    return conn


def setup(conn):
    """ Setup the database with the needed tables:
    types, performers, persons, groups, albums, rolas, and in_group.
    """
    cur = conn.cursor()

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
    track		INTEGER,
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

    conn.commit()
    return conn


def add_performer(conn, cur, performer):
    """ Adds a performer to table performers, and returns
    its primary key. If performer already exists it only returns the
    primary key. Expects a sqlite3.Connection, sqlite3.Cursor and a
    list with the name of the performer as its only element.
    Returns a list with the primary key as its only element.
    """
    id_performer = cur.execute(
        "SELECT id_performer from performers WHERE name = ?;",
        performer).fetchone()
    if not id_performer:
        cur.execute(
            "INSERT into performers(id_type, name) VALUES(2, ?)",
            performer)
        conn.commit()
        id_performer = cur.execute(
            "SELECT id_performer from performers WHERE name = ?;",
            performer).fetchone()
    return list(id_performer)


def add_album(conn, cur, album, year):
    """ Adds an album to albums table, and returns
    its primary key. If album already exists it only returns the
    primary key. Expects a sqlite3.Connection, sqlite3.Cursor and a
    list with the name of the album and another list with its year.
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
        conn.commit()
        id_album = cur.execute(
            "SELECT id_album from albums WHERE"
            "(name = ?) AND (year = ?);",
            album + year).fetchone()
    return list(id_album)


def add_song(conn, cur, file):
    """ Adds a song to the database, any tag that is empty will have
    the corresponding column assigned to "Unknown" or 0 in the case of
    track number. Expects a sqlite3.Connection, sqlite3.Cursor and
    a valid audio file.
    """
    song = mutagen.easyid3.EasyID3(file)
    path = [str(file)]
    title = info if (info := song.get("title")) is not None else ["Unknown"]
    genre = info if (info := song.get("genre")) is not None else ["Unknown"]
    track = ([int(info[0])] if (info := song.get("tracknumber")) is not None
             else [0])
    year = ([int(info[0])] if (info := song.get("date")) is not None
            else [dt.date.today().year])

    if (performer := song.get("artist")) is not None:
        id_performer = add_performer(conn, cur, performer)
    else:
        performer = ["Unknown"]
        id_performer = [None]

    if (album := song.get("album")) is not None:
        id_album = add_album(conn, cur, album, year)
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
        conn.commit()


def add_songs(conn, files=pathlib.Path.home().joinpath("Music").rglob("*")):
    """  Add songs to the database by calling add_song on each valid file.
    Expects a sqlite3.Connection object and a list of pathlib.Path objects.
    """
    cur = conn.cursor()
    for file in files:
        if file.is_file() and mutagen.File(file) is not None:
            add_song(conn, cur, file)


if __name__ == '__main__':
    connect()
