import collections
import json
import logging
import oauth2client.client
import oauth2client.file
import oauth2client.tools
import oauthlib.oauth2
import requests
import requests_oauthlib


BLOGGER_API_PREFIX = 'https://www.googleapis.com/blogger/v3/blogs/'


class cmd_flags(object):
    def __init__(self):
        self.short_url = True
        self.noauth_local_webserver = False
        self.logging_level = 'ERROR'
        self.auth_host_name = 'localhost'
        self.auth_host_port = [8080, 9090]


class BloggerManager(object):
    def __init__(self, blog_id=None, client_id=None, client_secret=None):
        self.blog_id = blog_id
        self.client_id = client_id
        self.client_secret = client_secret

        self._auth = None

    def do_auth(self, force=False):
        flow = oauth2client.client.OAuth2WebServerFlow(
            client_id=self.client_id,
            client_secret=self.client_secret,
            scope='https://www.googleapis.com/auth/blogger',
            redirect_uri='http://localhost:8080')
        storage = oauth2client.file.Storage("googleapiauth.txt")
        credentials = storage.get()

        if force or not credentials or credentials.access_token_expired or credentials.invalid:
            level = logging.getLogger().level
            credentials = oauth2client.tools.run_flow(flow, storage, cmd_flags())
            logging.getLogger().setLevel(level)

        self._auth = requests_oauthlib.OAuth2(
            client=oauthlib.oauth2.BackendApplicationClient(
                client_id=credentials.client_id,
                access_token=credentials.access_token
            )
        )

    def _parse_posts(self, posts, page_token=None):
        response = requests.get(
            BLOGGER_API_PREFIX + self.blog_id + "/posts",
            auth=self._auth,
            params={
                "maxResults": 100,
                "pageToken": page_token
            }
        )
        result = response.json()
        if result.get("items"):
            for post in result.get("items"):
                posts[post.get("title")] = post
        return result.get("nextPageToken")

    def get_posts(self):
        posts = {}

        page_token = self._parse_posts(posts)
        while page_token:
            page_token = self._parse_posts(posts, page_token=page_token)

        return posts

    def get_post_by_name(self, name):
        """
        ***Unreliable***
        Not using until I can figure out why you can't search for a post
        by name here or on blogger.
        :param name:
        :return:
        """
        response = requests.get(
            BLOGGER_API_PREFIX + self.blog_id + "/posts/search",
            auth=self._auth,
            params={
                "maxResults": 100,
                "q": name
            }
        )
        result = response.json()
        if result.get("items"):
            for post in result.get("items"):
                if post.get("title") == name:
                    return post
        return result.get("nextPageToken")

    def get_posts_from_file(self, filename):
        with open(filename) as f:
            return json.load(f)

    def save_posts_to_file(self, posts, filename):
        with open(filename, "w") as f:
            json.dump(posts, f)

    def get_page(self, page_id):
        response = requests.get(
            BLOGGER_API_PREFIX + self.blog_id + "/pages/" + page_id,
            auth=self._auth
        )
        return response.json()

    def create_blog(self, title, datetime, content, labels=None, draft=False):
        response = requests.post(
            BLOGGER_API_PREFIX + self.blog_id + "/posts",
            auth=self._auth,
            params={"isDraft": draft},
            json={
                "title": title,
                "published": datetime.isoformat() + "+00:00",
                "content": content,
                "labels": labels or []
            }
        )
        return response

    def update_blog(self, blog_id, title, datetime, content, labels=None):
        response = requests.put(
            BLOGGER_API_PREFIX + self.blog_id + "/posts/" + blog_id,
            auth=self._auth,
            json={
                "title": title,
                "published": datetime.isoformat() + "+00:00",
                "content": content,
                "labels": labels or []
            }
        )
        return response

    def update_page(self, page_id, **kwargs):
        response = requests.put(
            BLOGGER_API_PREFIX + self.blog_id + "/pages/" + page_id,
            auth=self._auth,
            json=kwargs
        )
        return response