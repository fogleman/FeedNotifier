import os
import jinja2 as jinja

DEFAULT_THEME = 'default'

def create_env():
    path = os.path.abspath('.')
    loader = jinja.FileSystemLoader(path)
    env = jinja.Environment(loader=loader)
    return env
    
def render(theme, item, context=None):
    feed = item.feed
    reldir = 'themes/%s' % theme
    absdir = os.path.abspath(reldir)
    absdir = 'file:///%s' % absdir.replace('\\', '/')
    if feed.has_favicon:
        icon = feed.favicon_path
    else:
        icon = os.path.abspath('icons/feed.png')
    context = context or {}
    context['item'] = item
    context['feed'] = feed
    context['icon'] = icon
    context['reldir'] = reldir
    context['absdir'] = absdir
    try:
        template = 'themes/%s/index.html' % theme
        template = env.get_template(template)
        return template.render(context)
    except Exception:
        if theme == DEFAULT_THEME:
            raise
        return render(DEFAULT_THEME, item, context)
        
env = create_env()
