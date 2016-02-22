import boto.s3.connection
import boto.s3.key
from collections import defaultdict


class S3Manager(object):
    def __init__(self, access_id, secret, bucket):
        self._access_id = access_id
        self._secret = secret
        self._bucket_name = bucket

        self._client = None
        self._bucket = None

    def do_auth(self):
        self._client = boto.s3.connection.S3Connection(
            self._access_id,
            self._secret
        )
        self._bucket = self._client.get_bucket(self._bucket_name)

    def add_file(self, name, contents, content_type="text/html"):
        k = boto.s3.key.Key(self._bucket, name)
        if content_type:
            k.set_metadata("content-type", content_type)
        k.set_contents_from_string(contents)

    def add_file_from_file(self, name, fp, content_type="text/html"):
        k = boto.s3.key.Key(self._bucket, name)
        if content_type:
            k.set_metadata("content-type", content_type)
        k.set_contents_from_file(fp)

    def add_file_from_filename(self, name, filename):
        k = boto.s3.key.Key(self._bucket, name)
        k.set_contents_from_filename(filename)

    def get_all_images(self, size="m"):
        result_set = defaultdict(list)
        for key in self._bucket.list("images/%s/" % size):
            name = key.key[9:-7].rsplit("_", 1)[0]
            result_set[name].append(key.key[9:])
        return result_set

    def get_all_images_list(self, size="m"):
        result = []
        for key in self._bucket.list("images/%s/" % size):
            result.append(key.key[9:])
        return result

    def get_all_videos(self):
        result_set = defaultdict(list)
        for key in self._bucket.list("videos/"):
            name = key.key[7:-7].rsplit("_", 1)[0]
            result_set[name].append(key.key[7:])
        return result_set

    def delete_key(self, name):
        k = boto.s3.key.Key(self._bucket, name)
        k.delete()

    def cleanup_old_interactive_maps(self):
        interactivemaps = []
        interactivemapslight = []

        for key in self._bucket.list("kml/"):
            if key.key.startswith("kml/interactivemap_"):
                interactivemaps.append(key)
            elif key.key.startswith("kml/interactivemaplight_"):
                interactivemapslight.append(key)

        interactivemaps.sort(key=lambda k: k.key, reverse=True)
        interactivemapslight.sort(key=lambda k: k.key, reverse=True)

        for m in interactivemaps[1:]:
            m.delete()

        for m in interactivemapslight[1:]:
            m.delete()
