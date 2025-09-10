from vercel_wsgi import handle
from enatjobs.wsgi import application  # replace 'enatjobs' with your Django project name

def handler(event, context):
    return handle(event, context, application)
