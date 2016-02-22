from setuptools import setup, find_packages


setup(
    name="geoblogger",
    version="0.0.1",
    author="Lewis Bosson",
    description="Geo Blogger App.",
    packages=find_packages(),
    scripts=[
        'scripts/geobloggerapp',
    ],
    install_requires=[
        "jinja2==2.8",
        "gpxpy==1.0.0",
        "config==0.3.9",
        "boto==2.38.0",
        "Pillow==3.0.0",
        "pykml==0.1.0",
        "requests==2.9.1",
        "requests-oauthlib==0.6.0",
        "oauth2client==1.5.2",
        "IPTCInfo==1.9.5-6"
    ],
    zip_safe=False,
    include_package_data=True
)
