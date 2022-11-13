from gi.repository import GLib
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


if __name__ == '__main__':
    connect()
