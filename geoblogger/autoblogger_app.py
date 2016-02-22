import StringIO
import os
import datetime
import collections
import jinja2
import blogger_manager
import filewatch
import input_helpers
import kml_helpers
import image_helpers
import parse_gpx
import s3_manager
import PIL.Image
import logging
import video_helpers


log = logging.getLogger("blog_manager")


class AutoBloggerApp(object):
    def __init__(self, config):
        self._config = config

        self._s3_manager = s3_manager.S3Manager(self._config.s3_access_id, self._config.s3_secret, self._config.s3_bucket)
        self._blogger_manager = blogger_manager.BloggerManager(self._config.blogger_blog_id, self._config.blogger_client_id, self._config.blogger_secret)

        self._env = jinja2.Environment(loader=jinja2.PackageLoader('geoblogger', 'templates'))

        self._posts = None
        self._images = None
        self._prompt = self._config.prompt

    def do_auth(self):
        self._s3_manager.do_auth()
        self._blogger_manager.do_auth()

    @property
    def env(self):
        return self._env

    @property
    def config(self):
        return self._config

    @property
    def posts(self):
        if self._posts is None:
            self._posts = self._blogger_manager.get_posts()
        return self._posts

    def get_all_images(self, size="m"):
        return self._s3_manager.get_all_images(size)

    def get_post(self, name):
        return self.posts.get(name)

    def find_new_posts(self):
        return [name for name, up_to_date in self.find_posts() if not up_to_date]

    def find_posts(self):
        """
        Return a complete list of local blog posts in order old to new.
        :return: list of tuples like (name, up_to_date)
        """
        raise NotImplementedError()

    def find_images(self, post_name):
        """
        Implement this to find the images for a blog post.
        :return: list of tuples like (name, path, up_to_date, tags)
        """
        raise NotImplementedError()

    def find_deleted_images(self):
        """
        Implement this to find the deleted images.
        :return: list of tuples like (name, path)
        """
        raise NotImplementedError()

    def find_videos(self, post_name):
        """
        Implement this to find the videos for a blog post.
        :return: list of tuples like (name, path, up_to_date)
        """
        raise NotImplementedError()

    def find_gpx(self, post_name):
        """
        Implement this to find the gpx file for a blog post.
        :return: (name, path, up_to_date)
        """
        raise NotImplementedError()

    def process_blogpost(self, post_name):
        """
        This is the big guy that drives the work.
        :param post_name: name of the gpx file
        :return: None
        """
        print "Begin Processing %s..." % post_name

        print "\tProcessing images..."
        images = self.find_images(post_name)
        self.process_images(images)

        print "\tProcessing videos..."
        videos = self.find_videos(post_name)
        self.process_videos(videos)

        print "\tProcessing gpx file..."
        gpx_name, gpx_path, gpx_up_to_date = self.find_gpx(post_name)
        gpx = self.process_gpx(gpx_name, gpx_path, gpx_up_to_date)

        print "\tCreating blogpost..."
        self.create_blogpost(post_name, gpx, images, videos)

        print "Finished processing %s!" % post_name

    def before_process_image(self, image_info):
        pass

    def after_process_image(self, image_info):
        pass

    def process_images(self, images):
        print "\tFound %s new, modified or deleted images:" % len([i for i in images if not i.up_to_date])
        for image in images:
            if not image.up_to_date:
                print "\t\t%s" % image.name

        input_helpers.continue_or_exit(self._prompt, "\tContinue with images processing?")

        for image in images:
            if image.up_to_date:
                continue

            self.before_process_image(image)
            print "\tProcessing %s..." % image.name

            if image.deleted:
                print "\t\tFile has been removed, deleting."
                self._s3_manager.delete_key(image_helpers.relative_url_from_name(image.name, 's'))
                self._s3_manager.delete_key(image_helpers.relative_url_from_name(image.name, 'm'))
                self._s3_manager.delete_key(image_helpers.relative_url_from_name(image.name, 'f'))
                self.after_process_image(image)
                continue

            print "\t\tCreating small image..."
            pil_image = PIL.Image.open(image.source)
            timage = pil_image.copy()
            timage.thumbnail(self._config.image_size_small, PIL.Image.ANTIALIAS)
            buffer = StringIO.StringIO()
            timage.save(buffer, "JPEG", quality=80, optimize=True)
            buffer.seek(0)

            print "\t\tUploading small image..."
            n = image_helpers.relative_url_from_name(image.name, 's')
            self._s3_manager.add_file_from_file(n, buffer, content_type="image/jpeg")
            buffer = StringIO.StringIO()

            print "\t\tCreating medium image..."
            timage = pil_image.copy()
            timage.thumbnail(self._config.image_size_medium, PIL.Image.ANTIALIAS)
            timage.save(buffer, "JPEG", quality=80, optimize=True)
            buffer.seek(0)

            print "\t\tUploading medium image..."
            n = image_helpers.relative_url_from_name(image.name, 'm')
            self._s3_manager.add_file_from_file(n, buffer, content_type="image/jpeg")
            buffer = StringIO.StringIO()

            print "\t\tCreating large image..."
            if self._config.image_size_large:
                pil_image.thumbnail(self._config.image_size_large, PIL.Image.ANTIALIAS)
                pil_image.save(buffer, "JPEG", quality=90, optimize=True)
                buffer.seek(0)

            print "\t\tUploading large image..."
            n = image_helpers.relative_url_from_name(image.name, 'f')
            if self._config.image_size_large:
                self._s3_manager.add_file_from_file(n, buffer, content_type="image/jpeg")
            else:
                self._s3_manager.add_file_from_filename(n, image.source)

            self.after_process_image(image)

    def before_process_video(self, video):
        pass

    def after_process_video(self, video):
        pass

    def process_videos(self, videos):
        print "\tFound %s new, modified or deleted videos:" % len([v for v in videos if not v.up_to_date])
        for video in videos:
            if not video.up_to_date:
                print "\t\t%s" % video.name

        input_helpers.continue_or_exit(self._prompt, "\tContinue with video processing?")

        for video in videos:
            if video.up_to_date:
                continue
            self.before_process_video(video)
            print "\tProcessing %s..." % video.name

            if video.deleted:
                print "\t\tDeleting video..."
                self._s3_manager.delete_key(video_helpers.relative_url_from_name(video.name))
            else:
                print "\t\tUploading %s..." % video.name
                self._s3_manager.add_file_from_filename(
                    video_helpers.relative_url_from_name(video.name),
                    video.source
                )

            self.after_process_video(video)

    def process_gpx(self, name, path, up_to_date):
        print "\t\tParsing GPX file..."
        gpx = parse_gpx.parse_gpx(path)

        if up_to_date:
            print "\tGPX file has already been processed, skipping upload."
            return gpx

        print "\t\tUploading GPX file..."
        self._s3_manager.add_file_from_filename(
            "gpx/%s" % name.replace(" ", "_"),
            path
        )

        map_template = self._env.get_template("autoblog_map.html")
        chart_template = self._env.get_template("autoblog_chart.html")

        tracks = parse_gpx.Track.parse_tracks_from_gpx(gpx)
        waypoints = parse_gpx.Waypoint.parse_waypoints_from_gpx(gpx)
        if tracks:
            track = tracks[0]
            print "\t\tUploading KML file..."
            kml = kml_helpers.create_kml_from_track(track)
            self._s3_manager.add_file(
                kml_helpers.relative_url_from_name(name),
                kml_helpers.kml_to_string(kml),
                content_type="application/kml+xml"
            )

            print "\t\tUploading Map HTML file..."
            map_html = map_template.render(
                title=name,
                lat=track.points[-1].latitude,
                long=track.points[-1].longitude,
                kml_url="http://geoblogger.s3-website-us-east-1.amazonaws.com/kml/%s.kml" % name.replace(" ", "_"),
                track=bool(tracks),
                config=self._config
            )
            self._s3_manager.add_file("maps/%s.html" % name.replace(" ", "_"), map_html)

            print "\t\tUploading Chart HTML file..."
            chart_html = chart_template.render(
                title=name,
                chart_data=track.get_altitude_chart_data(),
                min_elevation=track.min_elevation,
                max_elevation=track.max_elevation,
                config=self._config
            )
            self._s3_manager.add_file("charts/%s.html" % name.replace(" ", "_"), chart_html)
        elif waypoints:
            waypoint = waypoints[0]
            kml = kml_helpers.create_kml_from_waypoint(waypoint)
            self._s3_manager.add_file(
                kml_helpers.relative_url_from_name(name),
                kml_helpers.kml_to_string(kml),
                content_type="application/kml+xml"
            )

            print "\t\tUploading Map HTML file..."
            map_html = map_template.render(
                title=name,
                lat=waypoint.lat,
                long=waypoint.long,
                kml_url="http://geoblogger.s3-website-us-east-1.amazonaws.com/kml/%s.kml" % name.replace(" ", "_"),
                track=bool(tracks),
                config=self._config
            )
            self._s3_manager.add_file("maps/%s.html" % name.replace(" ", "_"), map_html)
        else:
            print "\t\tNo tracks or waypoints found for %s" % name

        return gpx

    def create_blogpost(self, post_name, gpx, images, videos):
        template = self._env.get_template("autoblog.html")

        tracks = parse_gpx.Track.parse_tracks_from_gpx(gpx)
        waypoints = parse_gpx.Waypoint.parse_waypoints_from_gpx(gpx)
        if not tracks and not waypoints:
            log.error("Didn't find any waypoints or tracks in gpx file - %s" % post_name)
            print "Didn't find any waypoints or tracks in gpx file - %s" % post_name
            exit(-1)

        if tracks:
            if len(tracks) > 1:
                log.warn("GPX %s contains more than 1 track (%s)." % (post_name, len(tracks)))
            track = tracks[0]
            is_track = True
        else:
            if len(waypoints) > 1:
                log.warn("GPX %s contains more than 1 waypoint (%s)." % (post_name, len(waypoints)))
            track = waypoints[0]
            is_track = False

        existing_post = self.get_post(post_name)

        dt = datetime.datetime(*[int(s) for s in post_name.split(" ")[0].split("-")], hour=20)

        # Get AWS Links
        map_url = "%s/maps/%s.html" % (self._config.s3_website_prefix, post_name.replace(" ", "_"))
        gpx_url = "%s/gpx/%s.GPX" % (self._config.s3_website_prefix, post_name.replace(" ", "_"))
        chart_url = "%s/charts/%s.html" % (self._config.s3_website_prefix, post_name.replace(" ", "_"))

        # Get Video Links
        video_urls = []
        if videos:
            videos.sort(key=lambda k: k[0])
            video_urls = ["%s/%s" % (self._config.s3_website_prefix, video_helpers.relative_url_from_name(v[0])) for v in videos if not v.deleted]

        # Get Image Links
        featured_img = None
        img_urls = []
        if images:
            images.sort(key=lambda k: k[0])
            for image in images:
                if image.deleted:
                    continue

                if featured_img is None or image_helpers.is_featured(image.tags):
                    featured_img = "%s/%s" % (self._config.s3_website_prefix, image_helpers.relative_url_from_name(image.name, "m"))

                img_urls.append(
                    (
                        "%s/%s" % (self._config.s3_website_prefix, image_helpers.relative_url_from_name(image.name, "f")),
                        "%s/%s" % (self._config.s3_website_prefix, image_helpers.relative_url_from_name(image.name, "m")),
                        image_helpers.get_caption(image.tags)
                    )
                )
        else:
            log.warning("No pictures found for %s." % post_name)

        variables = {
            "featured_photo": featured_img,
            "description": track.description.replace("\n", "<br />") if track.description else "Nothing here yet.",
            "photos": img_urls,
            "videos": video_urls,
            "map_share_link": map_url,
            "config": self._config
        }

        if is_track:
            variables["map_download_link"] = gpx_url
            variables["chart_share_link"] = chart_url
            variables["distance"] = str(int(track.distance / 1000.0))
            variables["distance_m"] = str(int(track.distance / 1000.0 * 0.621371192))
            variables["max_altitude"] = str(int(track.max_elevation))
            variables["max_altitude_f"] = str(int(track.max_elevation * 3.281))
            variables["min_altitude"] = str(int(track.min_elevation))
            variables["min_altitude_f"] = str(int(track.min_elevation * 3.281))
            variables["ascent"] = str(int(track.ascent))
            variables["ascent_f"] = str(int(track.ascent * 3.281))
            variables["descent"] = str(int(track.descent))
            variables["descent_f"] = str(int(track.descent * 3.281))

        if existing_post:
            input_helpers.continue_or_exit(
                prompt=self._prompt,
                msg="\tAre you sure you want to update existing post?"
            )
            response = self._blogger_manager.update_blog(
                blog_id=existing_post.get("id"),
                title=post_name,
                datetime=dt,
                content=template.render(**variables),
                labels=[self._config.blog_tag]
            )
        else:
            input_helpers.continue_or_exit(
                prompt=self._prompt,
                msg="\tAre you sure you want to create a new post?"
            )
            response = self._blogger_manager.create_blog(
                title=post_name,
                datetime=dt,
                content=template.render(**variables),
                labels=[self._config.blog_tag]
            )

        if response.status_code != 200:
            print "Unable to process %s - %s" % (post_name, response.content)
            log.error("Unable to process %s - %s" % (post_name, response.content))
            exit(response.status_code)
        else:
            print "Processed %s - %s" % (post_name, response.json().get("url"))
            log.info("Processed %s - %s" % (post_name, response.json().get("url")))


PostInfo = collections.namedtuple('PostInfo', ['name', 'up_to_date'])
GPXInfo = collections.namedtuple('GPXInfo', ['name', 'source', 'up_to_date'])
ImageInfo = collections.namedtuple('ImageInfo', ['name', 'source', 'up_to_date', 'tags', 'deleted'])
VideoInfo = collections.namedtuple('VideoInfo', ['name', 'source', 'up_to_date', 'deleted'])


class AutoBloggerApp1(AutoBloggerApp):
    """
    The directory method of organizing blogs
    """

    def __init__(self, config):
        super(AutoBloggerApp1, self).__init__(config)

        self._post_watcher = filewatch.Filewatch(self._config.blog_folder, os.path.join(self._config.blog_folder, ".meta", "post"), fresh=False, reverse=False, recursive_level=1)

        self._images = collections.defaultdict(list)
        self._videos = collections.defaultdict(list)
        self._gpx = {}

    def find_images(self, post_name):
        return self._images.get(post_name, [])

    def find_videos(self, post_name):
        return self._videos.get(post_name, [])

    def find_posts(self):
        posts = []
        for name, source, changed, is_new in self._post_watcher.changed(only_changed=False):
            postname = os.path.dirname(name)
            basename = os.path.basename(name)
            filename, ext = os.path.splitext(basename)

            # If this is a toplevel directory than it's a blogpost
            if os.path.isdir(source):
                posts.append(
                    PostInfo(
                        name,
                        not changed
                    )
                )
                continue

            if os.path.isfile(source) and ext.lower() in self.config.image_extensions:
                self._images[postname].append(
                    ImageInfo(
                        name,
                        source,
                        not changed,
                        image_helpers.get_iptc_info(source),
                        False
                    )
                )
                continue

            if os.path.isfile(source) and ext.lower() in self.config.video_extensions:
                self._videos[postname].append(
                    VideoInfo(
                        name,
                        source,
                        not changed,
                        False
                    )
                )
                continue

            if os.path.isfile(source) and ext.lower() == ".gpx":
                self._gpx[postname] = GPXInfo(
                    name,
                    source,
                    not changed
                )
                continue

        _, deleted = self._post_watcher.deleted()
        for name, source in deleted:
            postname = os.path.dirname(name)
            basename = os.path.basename(name)
            filename, ext = os.path.splitext(basename)

            if ext.lower() in self.config.image_extensions:
                self._images[postname].append(
                    ImageInfo(
                        name,
                        source,
                        False,
                        None,
                        True
                    )
                )
                continue

            if ext.lower() in self.config.video_extensions:
                self._videos[postname].append(
                    VideoInfo(
                        name,
                        source,
                        False,
                        True
                    )
                )
                continue

        # Look for posts with updated media
        for i, post in enumerate(posts):
            gpx = self.find_gpx(post.name)
            if post.up_to_date and (not all([t.up_to_date for t in self.find_images(post.name)]) or
                                        not all([t.up_to_date for t in self.find_videos(post.name)]) or
                                        not gpx.up_to_date):
                posts[i] = PostInfo(post.name, False)

        return posts

    def find_gpx(self, post_name):
        return self._gpx.get(post_name)

    def after_process_image(self, image):
        if image.deleted:
            self._post_watcher.mark_deleted(image.name)
        else:
            self._post_watcher.mark_uptodate(image.name)

    def after_process_video(self, video):
        if video.deleted:
            self._post_watcher.mark_deleted(video.name)
        else:
            self._post_watcher.mark_uptodate(video.name)

    def process_gpx(self, name, path, up_to_date):
        gpx = super(AutoBloggerApp1, self).process_gpx(name, path, up_to_date)
        self._post_watcher.mark_uptodate(name)
        return gpx

    def create_blogpost(self, post_name, gpx, images, videos):
        retval = super(AutoBloggerApp1, self).create_blogpost(post_name, gpx, images, videos)
        self._post_watcher.mark_uptodate(post_name)
        return retval


class AutoBloggerApp2(AutoBloggerApp):
    """
    The media method of organizing blogs
    """

    def __init__(self, config):
        super(AutoBloggerApp2, self).__init__(config)

        self._post_watcher = filewatch.Filewatch(os.path.join(self._config.blog_folder, "gpx"), os.path.join(self._config.blog_folder, ".meta", "post"), fresh=False, reverse=False, recursive_level=0)
        self._gpx_watcher = filewatch.Filewatch(os.path.join(self._config.blog_folder, "gpx"), os.path.join(self._config.blog_folder, ".meta", "gpx"), fresh=False, reverse=False, recursive_level=0)
        self._image_watcher = filewatch.Filewatch(os.path.join(self._config.blog_folder, "images"), os.path.join(self._config.blog_folder, ".meta", "image"), fresh=False, reverse=False, recursive_level=0)
        self._video_watcher = filewatch.Filewatch(os.path.join(self._config.blog_folder, "videos"), os.path.join(self._config.blog_folder, ".meta", "video"), fresh=False, reverse=False, recursive_level=0)

        self._name_map = {}

        self._images = {}
        self._videos = {}

    def find_images(self, post_name):
        images = self._images.get(post_name)
        if images is None:
            basename = os.path.splitext(post_name)[0]
            images = []
            for name, source, changed, is_new in self._image_watcher.changed(only_changed=False):
                if name.startswith(basename):
                    images.append(
                        ImageInfo(
                            name,
                            source,
                            not changed,
                            image_helpers.get_iptc_info(source),
                            False
                        )
                    )
            _, deleted = self._image_watcher.deleted()
            for name, source in deleted:
                if name.startswith(basename):
                    images.append(
                        ImageInfo(
                            name,
                            source,
                            False,
                            None,
                            True
                        )
                    )
            self._images[post_name] = images
        return images

    def find_videos(self, post_name):
        videos = self._videos.get(post_name)
        if videos is None:
            basename = os.path.splitext(post_name)[0]
            videos = []
            for name, source, changed, is_new in self._video_watcher.changed(only_changed=False):
                if name.startswith(basename):
                    videos.append(
                        VideoInfo(
                            name,
                            source,
                            not changed,
                            False
                        )
                    )
            _, deleted = self._video_watcher.deleted()
            for name, source in deleted:
                if name.startswith(basename):
                    videos.append(
                        VideoInfo(
                            name,
                            source,
                            False,
                            True
                        )
                    )
            self._videos[post_name] = videos
        return videos

    def find_posts(self):
        posts = []
        for filename, source, changed, is_new in self._post_watcher.changed(only_changed=False):
            name = os.path.splitext(filename)[0]
            self._name_map[name] = filename
            posts.append(
                PostInfo(
                    name,
                    not changed
                )
            )

        # Look for posts with updated media
        for i, post in enumerate(posts):
            if post.up_to_date and (not all([t.up_to_date for t in self.find_images(post.name)]) or
                                        not all([t.up_to_date for t in self.find_videos(post.name)])):
                posts[i] = PostInfo(post.name, False)

        return posts

    def find_gpx(self, post_name):
        filename = self._name_map[post_name]
        return GPXInfo(post_name, self._gpx_watcher.get_source(filename), not self._gpx_watcher.is_changed(filename))

    def after_process_image(self, image):
        if image.deleted:
            self._image_watcher.mark_deleted(image.name)
        else:
            self._image_watcher.mark_uptodate(image.name)

    def after_process_video(self, video):
        if video.deleted:
            self._video_watcher.mark_deleted(video.name)
        else:
            self._video_watcher.mark_uptodate(video.name)

    def process_gpx(self, name, path, up_to_date):
        gpx = super(AutoBloggerApp2, self).process_gpx(name, path, up_to_date)
        self._gpx_watcher.mark_uptodate(name)
        return gpx

    def create_blogpost(self, post_name, gpx, images, videos):
        retval = super(AutoBloggerApp2, self).create_blogpost(post_name, gpx, images, videos)
        self._post_watcher.mark_uptodate(self._name_map[post_name])
        return retval
