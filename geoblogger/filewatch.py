import os
import json
import logging
import re


log = logging.getLogger("filewatch")


class Filewatch(object):
    def __init__(self, source_dir, backup_file_path, skiplist=None, fresh=False, reverse=False, recursive_level=None):
        self.backup_file_path = backup_file_path
        self.source_dir = source_dir
        self.files_to_backup = []
        self.skiplist = skiplist or []
        self.fresh = fresh
        self.recursive_level = recursive_level

        self.walk_directory(self.source_dir, "", self.files_to_backup)
        log.info("Found %s files to check.", len(self.files_to_backup))
        if reverse:
            self.files_to_backup.reverse()

        self.database = self.load_db()

    def get_source(self, name):
        return os.path.join(self.source_dir, name)

    def mark_uptodate(self, name):
        if name in self.files_to_backup:
            source = os.path.join(self.source_dir, name)
            stats_s = self.get_stats(source)
            self.database[name] = stats_s
            self.save_db()

    def mark_deleted(self, name):
        if name in self.database:
            del self.database[name]
            self.save_db()

    def is_changed(self, name):
        source = os.path.join(self.source_dir, name)
        stats_s = self.get_stats(source)
        stats_db = self.database.get(name)

        return stats_s != stats_db

    def is_deleted(self, name):
        source = os.path.join(self.source_dir, name)
        return not os.path.exists(source)

    def changed(self, only_changed=False):
        retval = []
        for name in self.files_to_backup:
            source = os.path.join(self.source_dir, name)
            stats_s = self.get_stats(source)
            stats_db = self.database.get(name)

            if only_changed and stats_s == stats_db:
                continue

            retval.append((name, source, stats_s != stats_db, stats_db is None))
        return retval

    def changedi(self, only_changed=False, incremental_save=True):
        try:
            for name in self.files_to_backup:
                source = os.path.join(self.source_dir, name)
                stats_s = self.get_stats(source)
                stats_db = self.database.get(name)

                if only_changed and stats_s == stats_db:
                    continue

                yield name, source, stats_s != stats_db, stats_db is None
                if stats_s != stats_db:
                    self.database[name] = stats_s
                    if incremental_save:
                        self.save_db()
        finally:
            self.save_db()

    def deleted(self):
        dirs_to_remove = []
        files_to_remove = []
        for name in self.database.keys():
            source = os.path.join(self.source_dir, name)
            if os.path.exists(source):
                continue

            if os.path.isdir(source):
                dirs_to_remove.append((name, source))
            else:
                files_to_remove.append((name, source))

        return dirs_to_remove, files_to_remove

    def deletedi(self, incremental_save=True):
        dirs_to_remove = []
        files_to_remove = []
        for name in self.database.keys():
            source = os.path.join(self.source_dir, name)
            if os.path.exists(source):
                continue

            if os.path.isdir(source):
                dirs_to_remove.append((name, source))
            else:
                files_to_remove.append((name, source))

        try:
            for name, source in files_to_remove:
                yield name, source, False
                del self.database[name]
                if incremental_save:
                    self.save_db()

            for name, source in dirs_to_remove:
                yield name, source, True
                del self.database[name]
                if incremental_save:
                    self.save_db()
        finally:
            self.save_db()

    def load_db(self):
        log.info("Loading database (%s).", self.backup_file_path)
        database = {}
        if not self.fresh:
            try:
                if os.path.exists(self.backup_file_path):
                    with open(self.backup_file_path) as f:
                        database = json.load(f)
            except Exception:
                log.exception("Could not load Database!")
        return database or {}

    def save_db(self):
        log.info("Saving database.")
        if not os.path.exists(os.path.dirname(self.backup_file_path)):
            os.makedirs(os.path.dirname(self.backup_file_path))
        try:
            with open(self.backup_file_path, 'w') as f:
                json.dump(self.database, f, indent=4, sort_keys=True)
        except Exception:
            log.exception("Could not save Database!")
            raise

    def walk_directory(self, base_path, path, files, recursive_level=0):
        for name in os.listdir(os.path.join(base_path, path)):
            if name.startswith("."):
                continue
            rel_path = os.path.join(path, name)
            full_path = os.path.join(base_path, path, name)

            skip = False
            for s in self.skiplist:
                if re.match(s, rel_path):
                    skip = True
                    break
            if skip:
                continue
            if not os.path.isdir(full_path):
                files.append(rel_path)
            elif self.recursive_level is None or self.recursive_level > recursive_level:
                files.append(rel_path)
                self.walk_directory(base_path, os.path.join(path, name), files, recursive_level + 1)

    @staticmethod
    def get_stats(path):
        stats = list(os.stat(path))
        stats.pop(7)  # Remove access time
        stats.pop(2)  # Remove device
        return stats
