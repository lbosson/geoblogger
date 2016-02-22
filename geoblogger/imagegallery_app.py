import image_helpers


class ImageGalleryApp(object):
    def __init__(self, autobloggerapp):
        self._autobloggerapp = autobloggerapp

    def create_image_gallery(self):
        page = self._autobloggerapp._blogger_manager.get_page(self._autobloggerapp.config.image_gallery_page_id)
        if not page:
            print "\tImage Gallery Page %s Not Found!" % self._autobloggerapp.config.image_gallery_page_id
            exit(-1)

        photos = self._autobloggerapp._s3_manager.get_all_images_list("s")
        if not photos:
            print "\tCould not find any images!"
            exit(-2)

        photos.sort(reverse=True)

        gallery = self._autobloggerapp.env.get_template('gallery.html')
        slideshow = self._autobloggerapp.env.get_template('slideshow.html')
        links = [("%s/%s" % (self._autobloggerapp.config.s3_website_prefix, image_helpers.relative_url_from_name(photo, "m")),
                  "%s/%s" % (self._autobloggerapp.config.s3_website_prefix, image_helpers.relative_url_from_name(photo, "s")),
                  None) for photo in photos]

        print "\tUpdating Image Gallery Page..."
        response = self._autobloggerapp._blogger_manager.update_page(
            page_id=self._autobloggerapp.config.image_gallery_page_id,
            title=self._autobloggerapp.config.image_gallery_page_title,
            content=gallery.render(
                photos=links,
                include_jquery=True,
                config=self._autobloggerapp.config
            )
        )

        if response.status_code != 200:
            print "\tUnable to update image gallery page! %s" % response.reason
        else:
            response = response.json()
            print "\tImage Gallery Blogger Page - %s" % response.get("url")

        print "\tUploading Image Gallery and Slideshow Pages to S3..."
        self._autobloggerapp._s3_manager.add_file(
            "gallery.html",
            gallery.render(
                photos=links,
                include_jquery=True,
                config=self._autobloggerapp.config
            )
        )
        print "\tImage Gallery HTML Page - %s/gallery.html" % self._autobloggerapp.config.s3_website_prefix

        # self._autobloggerapp._s3_manager.add_file(
        #     "slideshow_medium.html",
        #     slideshow.render(
        #         photos=links,
        #         config=self._autobloggerapp.config
        #     )
        # )
        # print "\tImage Slidshow HTML Page - %s/slideshow_medium.html" % self._autobloggerapp.config.s3_website_prefix
