import gpxpy
import gpxpy.geo


def parse_gpx(filename):
    with open(filename, 'r') as f:
        return gpxpy.parse(f)


class Waypoint(object):
    def __init__(self):
        self.name = None
        self.description = None
        self.lat = None
        self.long = None

    @classmethod
    def parse_waypoints_from_gpx(cls, gpx):
        waypoints = []
        for waypoint in gpx.waypoints:
            w = Waypoint()
            waypoints.append(w)
            w.name = waypoint.name
            w.description = waypoint.description
            w.lat = waypoint.latitude
            w.long = waypoint.longitude
        return waypoints


class Track(object):
    def __init__(self):
        self.name = None
        self.description = None
        self.distance = 0
        self.max_elevation = 0
        self.min_elevation = 0
        self.ascent = 0
        self.descent = 0
        self.points = []
        self.altitude_chart = []

    @classmethod
    def parse_tracks_from_gpx(cls, gpx):
        tracks = []
        for track in gpx.tracks:
            t = Track()
            tracks.append(t)
            t.name = track.name
            t.description = track.description
            for segment in track.segments:
                last = None
                for p in segment.points:
                    if not last:
                        t.points.append(p)
                        last = p
                        t.max_elevation = p.elevation or 0
                        t.min_elevation = p.elevation or 0
                        continue

                    t.distance += gpxpy.geo.distance(
                        p.latitude,
                        p.longitude,
                        p.elevation,
                        last.latitude,
                        last.longitude,
                        last.elevation
                    )
                    if p.elevation is not None:
                        t.altitude_chart.append([int(t.distance / 10) / 100.0, p.elevation])
                        if p.elevation > t.max_elevation:
                            t.max_elevation = p.elevation
                        if p.elevation < t.min_elevation:
                            t.min_elevation = p.elevation

                    if abs(last.longitude - p.longitude) > .0001 or abs(last.latitude - p.latitude) > .0001:
                        t.points.append(p)
                        last = p

                t.ascent, t.descent = gpxpy.geo.calculate_uphill_downhill([p.elevation for p in t.points])
        return tracks

    def get_altitude_chart_data(self, limit=1000):
        return self._get_altitude_chart_data(self.altitude_chart, limit=limit)

    @staticmethod
    def _get_altitude_chart_data(data, limit):
        sample = int(len(data) / limit) if limit and len(data) > limit else 1
        return [p for i, p in enumerate(data) if data is not None and i % sample == 0]

    @staticmethod
    def combine_altitude_chart_data(tracks, limit=1000):
        if not tracks:
            return None
        data = tracks[0].altitude_chart
        for track in tracks[1:]:
            last_d = data[-1][0]
            for d, e in track.altitude_chart:
                data.append([d + last_d, e])
        return Track._get_altitude_chart_data(data, limit)
