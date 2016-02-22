import os


def validate_config(cfg):
    if not cfg.blog_folder:
        cfg.addMapping("blog_folder", os.path.dirname(os.path.abspath(cfg.config_path)), "default", True)

    if not cfg.log_level:
        return "Config missing required value 'log_level'."

    return ""
