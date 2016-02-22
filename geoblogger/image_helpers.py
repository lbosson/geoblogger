import os
import iptcinfo
import logging


logging.getLogger("iptcinfo").setLevel(logging.ERROR)


def relative_url_from_name(name, size):
    return "images/%s/%s" % (size, name.replace(" ", "_"))


def get_iptc_info(path):
    with open(path, "rb") as f:
        return iptcinfo.IPTCInfo(f)


def is_featured(tags):
    return ("Featured" in tags.keywords) if tags else False


def get_caption(tags):
    caption = tags.data['caption/abstract']
    if caption and caption != 'OLYMPUS DIGITAL CAMERA':
        return caption.decode('utf8')
    return None
