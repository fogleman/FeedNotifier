import os
import jinja2 as jinja

def create_env():
    path = os.path.abspath('.')
    loader = jinja.FileSystemLoader(path)
    env = jinja.Environment(loader=loader)
    return env
    
def render(theme, item, context=None):
    relative_dir = 'themes/%s' % theme
    dir = os.path.abspath(relative_dir)
    path = 'themes/%s/index.html' % theme
    template = env.get_template(path)
    context = context or {}
    context['item'] = item
    context['feed'] = item.feed
    context['dir'] = dir
    context['relative_dir'] = relative_dir
    return template.render(context)
    
env = create_env()
