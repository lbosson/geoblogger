import time

import itertools

import geoblogger.kml_helpers
import image_helpers
import parse_gpx
import logging
from lxml import etree
from pykml.factory import KML_ElementMaker as KML


log = logging.getLogger("interactivemap_app")


class InteractiveMapApp(object):
    def __init__(self, autobloggerapp):
        self._autobloggerapp = autobloggerapp

        self._tracks = []

        self._kml_full = KML.kml(
            KML.Document(
            )
        )

        self._kml_light = KML.kml(
            KML.Document(
            )
        )

        self._total_distance = 0
        self._riding_days = 0
        self._max_elevation = 0

        self._chart = None
        self._center = None

        self._images = None

    @property
    def kml_full(self):
        return self._kml_full

    @property
    def kml_light(self):
        return self._kml_light

    @property
    def center(self):
        return self._center

    @property
    def stats(self):
        return self._total_distance, self._riding_days, self._max_elevation

    @property
    def chart(self):
        return self._chart

    @property
    def images(self):
        if self._images is None:
            self._images = self._autobloggerapp.get_all_images()
        return self._images

    def get_images_for_blog(self, name):
        img_urls = []
        imgs = self.images.get(name.replace(" ", "_"))
        if imgs:
            for img in imgs:
                img_urls.append("%s/%s" % (
                self._autobloggerapp.config.s3_website_prefix, image_helpers.relative_url_from_name(img, 'm')))
        return img_urls

    def _process(self):
        posts = self._autobloggerapp.find_posts()

        points = 0
        for i, post in enumerate(posts):
            name, filename, up_to_date = self._autobloggerapp.find_gpx(post[0])

            print "\tParsing %s (%s of %s)" % (filename, i + 1, len(posts))

            gpx = parse_gpx.parse_gpx(filename)
            new_tracks = parse_gpx.Track.parse_tracks_from_gpx(gpx)
            new_waypoints = parse_gpx.Waypoint.parse_waypoints_from_gpx(gpx)

            self._tracks.append((name, new_tracks, new_waypoints))

            points += sum([len(t.points) for t in new_tracks])

            for track in new_tracks:
                if track.max_elevation > self._max_elevation:
                    self._max_elevation = track.max_elevation
                self._total_distance += track.distance
                self._riding_days += 1

        sample = int(points / 45000) or 1
        sample_light = int(points / 15000) or 1

        if self._tracks:
            print "\tCreating KML..."
            self._kml_full.Document.append(self.create_tracks_folder(sample))
            self._kml_light.Document.append(self.create_tracks_folder(sample_light))
            print "\tCreating Chart..."
            self._chart = self.generate_elevation_chart(10000)

        last_name, last_tracks, last_waypoints = self._tracks[-1]
        if last_tracks:
            self._center = last_tracks[-1].points[-1].latitude, last_tracks[-1].points[-1].longitude
        elif last_waypoints:
            self._center = last_waypoints[-1].lat, last_waypoints[-1].long
        else:
            print "Error: unable to center interactive map!"

    def create_tracks_folder(self, sample):
        template = self._autobloggerapp.env.get_template("interactive_map_blog.html")
        tracks_folder = KML.Folder(KML.name("Tracks"))
        for name, tracks, waypoints in self._tracks:
            description = "<br /><br />".join(
                [t.description.replace("\n", "<br />") for t in tracks + waypoints if t.description])

            variables = {
                "blog_link": self._autobloggerapp.posts.get(name).get("url") if self._autobloggerapp.posts.get(
                    name) else None,
                "photos": self.get_images_for_blog(name),
                "description": description or "Nothing here yet.",
                "config": self._autobloggerapp.config
            }

            if tracks:
                variables["distance"] = str(int(sum([t.distance for t in tracks]) / 1000.0))
                variables["distance_m"] = str(int(sum([t.distance for t in tracks]) / 1000.0 * 0.621371192))
                variables["max_altitude"] = str(int(max([t.max_elevation for t in tracks])))
                variables["max_altitude_f"] = str(int(max([t.max_elevation for t in tracks]) * 3.281))
                variables["min_altitude"] = str(int(min([t.min_elevation for t in tracks])))
                variables["min_altitude_f"] = str(int(min([t.min_elevation for t in tracks]) * 3.281))
                variables["ascent"] = str(int(sum([t.ascent for t in tracks])))
                variables["ascent_f"] = str(int(sum([t.ascent for t in tracks]) * 3.281))
                variables["descent"] = str(int(sum([t.descent for t in tracks])))
                variables["descent_f"] = str(int(sum([t.descent for t in tracks]) * 3.281))

            tracks_folder.extend(
                geoblogger.kml_helpers.create_kml_placemarks_for_tracks_and_waypoints(
                    tracks,
                    waypoints,
                    sample=sample,
                    description=template.render(**variables),
                    name=name
                )
            )

        last_name, last_tracks, last_waypoints = self._tracks[-1]
        if last_tracks:
            coordinates = "%s,%s" % (last_tracks[-1].points[-1].longitude, last_tracks[-1].points[-1].latitude)
        else:
            coordinates = "%s,%s" % (last_waypoints[-1].long, last_waypoints[-1].lat)

        tracks_folder.append(
            KML.Placemark(
                KML.name("I AM HERE"),
                KML.Style(
                    KML.IconStyle(
                        KML.color("ff00ffff"),
                        KML.scale(1.0),
                        KML.Icon(
                            KML.href("http://maps.google.com/mapfiles/kml/pal4/icon47.png")
                        ),
                    ),
                    KML.LabelStyle(
                        KML.scale(0.0)
                    )
                ),
                KML.Point(
                    KML.coordinates(coordinates)
                )
            )
        )
        return tracks_folder

    def generate_elevation_chart(self, limit=10000):
        return parse_gpx.Track.combine_altitude_chart_data(list(itertools.chain(*[t for n, t, w in self._tracks])), limit)

    def create_map(self):
        print "Starting creation of interactive map (this may take a while)..."
        self._process()

        print "\tUploading KML files..."
        version = int(time.time())
        self._autobloggerapp._s3_manager.add_file("kml/interactivemap_%s.kml" % version,
                                                  etree.tostring(etree.ElementTree(self.kml_full), pretty_print=True))
        self._autobloggerapp._s3_manager.add_file("kml/interactivemaplight_%s.kml" % version,
                                                  etree.tostring(etree.ElementTree(self.kml_light), pretty_print=True))

        print "\tUploading HTML files..."
        map_template = self._autobloggerapp.env.get_template("interactive_map.html")
        chart_template = self._autobloggerapp.env.get_template("interactive_chart.html")
        self._autobloggerapp._s3_manager.add_file(
            "maps/interactivemap.html",
            map_template.render(
                zoom=4,
                lat=self.center[0],
                long=self.center[1],
                kml_url="%s/kml/interactivemap_%s.kml" % (self._autobloggerapp.config.s3_website_prefix, version),
                preserve_viewport=False,
                config=self._autobloggerapp.config
            )
        )
        self._autobloggerapp._s3_manager.add_file(
            "maps/interactivemaplight.html",
            map_template.render(
                zoom=5,
                lat=self.center[0],
                long=self.center[1],
                kml_url="%s/kml/interactivemaplight_%s.kml" % (self._autobloggerapp.config.s3_website_prefix, version),
                preserve_viewport=True,
                config=self._autobloggerapp.config
            )
        )
        self._autobloggerapp._s3_manager.add_file(
            "charts/interactivechart.html",
            chart_template.render(
                title="Elevation Chart",
                chart_data=self.chart,
                config=self._autobloggerapp.config
            )
        )

        print "\tDeleting old maps..."
        self._autobloggerapp._s3_manager.cleanup_old_interactive_maps()

        print "\tUpdating Interactive Map blogger page..."
        track_template = self._autobloggerapp.env.get_template("track.html")
        track_html = track_template.render(
            distance=str(int(self._total_distance / 1000.0)),
            distance_m=str(int(self._total_distance / 1000.0 * 0.621371192)),
            max_altitude=str(int(self._max_elevation)),
            max_altitude_f=str(int(self._max_elevation * 3.281)),
            days_riding=str(int(self._riding_days)),
            config=self._autobloggerapp.config
        )

        if not self._autobloggerapp.config.interactive_map_page_id:
            log.error("Unable to update interactive map page because it's not set in the config. "
                      "Please create a page on your blog and add the id to the config for 'interactive_map_page_id'.")
            print "\tUnable to update interactive map page because it's not set in the config. " \
                  "Please create a page on your blog and add the id to the config for 'interactive_map_page_id'."
            return

        response = self._autobloggerapp._blogger_manager.update_page(
            page_id=self._autobloggerapp.config.interactive_map_page_id,
            title=self._autobloggerapp.config.interactive_map_title,
            content=track_html
        )

        if response.status_code is not 200:
            print "\tUnable to update map page on blogger - %s" % response.reason
        else:
            response = response.json()

        print "\tInteractive Map Full - %s/maps/interactivemap.html" % self._autobloggerapp.config.s3_website_prefix
        print "\tInteractive Map Light - %s/maps/interactivemaplight.html" % self._autobloggerapp.config.s3_website_prefix
        print "\tElevation Chart - %s/charts/interactivechart.html" % self._autobloggerapp.config.s3_website_prefix
        print "\tMap Page - %s" % response.get("url")
        print "\tFinished!"
