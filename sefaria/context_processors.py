"""
Djagno Context Processors, for decorating all HTTP request with common data.
"""

from django.utils import simplejson as json

from texts import get_text_titles_json
from notifications import NotificationSet
from summaries import get_toc
from settings import *

def offline(request):
	return {"OFFLINE": OFFLINE}


def google_analytics(request):
	return {"GOOGLE_ANALYTICS_CODE": GOOGLE_ANALYTICS_CODE}


def search_url(request):
	return {"SEARCH_URL": SEARCH_HOST}


def titles_json(request):
	return {"titlesJSON": get_text_titles_json()}


def toc(request):
	return {"toc": get_toc()}


def embed_page(request):
	return {"EMBED": "embed" in request.GET}


def notifications(request):
	if not request.user.is_authenticated():
		return {}
	notifications = NotificationSet().unread_for_user(request.user.id)
	return {"notifications": notifications.notifications, "notifications_count": notifications.count() }