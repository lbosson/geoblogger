import os


def relative_url_from_name(name):
    return "videos/%s" % name.replace(" ", "_")
