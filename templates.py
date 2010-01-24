import os
import jinja2 as jinja

DEFAULT_THEME = 'default'

def create_env():
    path = os.path.abspath('.')
    loader = jinja.FileSystemLoader(path)
    env = jinja.Environment(loader=loader)
    return env
    
def render(theme, item, context=None):
    reldir = 'themes/%s' % theme
    absdir = os.path.abspath(reldir)
    cssdir = 'file:///%s' % absdir.replace('\\', '/')
    context = context or {}
    context['item'] = item
    context['feed'] = item.feed
    context['reldir'] = reldir
    context['absdir'] = absdir
    context['cssdir'] = cssdir
    try:
        template = 'themes/%s/index.html' % theme
        template = env.get_template(template)
        return template.render(context)
    except Exception:
        if theme == DEFAULT_THEME:
            raise
        return render(DEFAULT_THEME, item, context)
        
env = create_env()
