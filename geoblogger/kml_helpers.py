import random

from lxml import etree
from pykml.factory import KML_ElementMaker as KML


def relative_url_from_name(name):
    return "kml/%s.kml" % name.replace(" ", "_")


def kml_to_string(kml):
    return etree.tostring(etree.ElementTree(kml), pretty_print=True)


def create_kml_placemarks_for_tracks_and_waypoints(tracks, waypoints, sample=1, description=None, color=None, name=None):
    placemarks = []
    tracks = tracks or []
    waypoints = waypoints or []

    for track in tracks:
        coordinates = ["%s,%s" % (p.longitude, p.latitude) for i, p in enumerate(track.points) if
                       i % sample == 0 or len(track.points) < 100]
        placemarks.append(
            KML.Placemark(
                KML.name(name or track.name),
                KML.description(description or track.description or ""),
                KML.Style(
                    KML.LineStyle(
                        KML.color(color) if color else get_random_color(),
                        KML.width(3)
                    )
                ),
                KML.MultiGeometry(
                    KML.LineString(
                        KML.coordinates(" ".join(coordinates))
                    )
                )
            )
        )

    for waypoint in waypoints:
        coordinates = "%s,%s" % (waypoint.long, waypoint.lat)
        placemarks.append(
            KML.Placemark(
                KML.name(name or waypoint.name),
                KML.description(description or waypoint.description or ""),
                KML.Style(
                    KML.IconStyle(
                        KML.color("ffffffff"),
                        KML.scale(1.0),
                        KML.Icon(
                            KML.href(
                                "http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
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
    return placemarks


def create_kml_from_tracks_and_waypoints(tracks, waypoints):
    return KML.kml(KML.document(create_kml_placemarks_for_tracks_and_waypoints(tracks, waypoints)))


def create_kml_from_track(track):
    coordinates = ["%s,%s" % (p.longitude, p.latitude) for p in track.points]
    doc = KML.kml(
        KML.Document(
            KML.Placemark(
                KML.name(track.name),
                KML.description(track.description if track.description else ""),
                KML.Style(
                    KML.LineStyle(
                        KML.color('ff78fff0'),
                        KML.width(3)
                    )
                ),
                KML.MultiGeometry(
                    KML.LineString(
                        KML.coordinates(" ".join(coordinates))
                    )
                )
            )
        )
    )
    return doc


def create_kml_from_waypoint(waypoint):
    coordinates = "%s,%s" % (waypoint.long, waypoint.lat)
    doc = KML.kml(
        KML.Document(
            KML.Placemark(
                KML.name(waypoint.name),
                KML.description(waypoint.description if waypoint.description else ""),
                KML.Style(
                    KML.IconStyle(
                        KML.color("ffffffff"),
                        KML.scale(1.0),
                        KML.Icon(
                            KML.href("http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png")
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
    )
    return doc


def get_random_color():
    return KML.color('ff%02X%02X%02X' % (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
