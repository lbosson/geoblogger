import logging
import os
import shutil
import filewatch
import input_helpers
import hashlib


log = logging.getLogger("folderbackup_app")


class FolderBackupApp(object):
    def __init__(self, config):
        self._config = config

    def backup(self):
        for bak_source, bak_dest, skip in self._config.folders_to_backup:
            db_loc = os.path.join(self._config.blog_folder, ".meta", hashlib.md5(bak_source + bak_dest).hexdigest())
            watcher = filewatch.Filewatch(bak_source, db_loc, skiplist=skip)

            print "About to backup %s to %s found %s file changes..." % (bak_source, bak_dest, len(watcher.files_to_backup))
            if not input_helpers.continue_or_skip(self._config.prompt):
                print "Skipping."
                return

            try:
                if not os.path.exists(bak_dest):
                    os.mkdir(bak_dest)
            except Exception, err:
                print "WARNING - Could not perform backup - %s" % err
                continue

            for name, source, changed, new in watcher.changedi(only_changed=True, incremental_save=False):
                dest = os.path.join(bak_dest, name)
                if os.path.isdir(source):
                    if not os.path.exists(dest):
                        os.mkdir(dest)
                        print "Making directory %s" % name
                    continue

                print "Copying %s" % name
                with open(source) as fr:
                    with open(dest, 'w') as fw:
                        buff = fr.read()
                        while buff:
                            fw.write(buff)
                            buff = fr.read()

            for name, source, dir in watcher.deletedi(incremental_save=False):
                dest = os.path.join(bak_dest, name)
                if not os.path.exists(dest):
                    continue
                if dir:
                    print "Deleting %s" % name
                    shutil.rmtree(dest)
                else:
                    print "Deleting %s" % name
                    os.remove(dest)

            print "Finished!!!"