from lxml import etree
from pykml.factory import KML_ElementMaker as KML


def relative_url_from_name(name):
    return "kml/%s.kml" % name.replace(" ", "_")


def kml_to_string(kml):
    return etree.tostring(etree.ElementTree(kml), pretty_print=True)


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
