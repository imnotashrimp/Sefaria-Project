"""
topic.py
"""
from collections import defaultdict

from . import abstract as abst
from sefaria.system.database import db
from sefaria.sheets import sheet_to_dict, get_sheets_by_tag
from sefaria.model.text import Ref


class Topic(abst.AbstractMongoRecord):
    """
    Data for a topic
        - sources
        - related topics
    """
    MAX_SOURCES = 50
    MAX_RELATED = 26

    collection   = 'topics'
    history_noun = 'topic'

    required_attrs = [
        "topic",
        "related_topics",
        "sources",
        "sheets"
    ]
    optional_attrs = []

    def __init__(self, topic, sources_dict=None, related_topics_dict=None):
        self.topic               = topic
        self.related_topics      = None
        self.sources             = None
        self.sheets              = None
        self.sources_dict        = sources_dict
        self.related_topics_dict = related_topics_dict
        self._filtered           = False
        self.make_data_from_sheets()


    def contents(self):
        return {
            "topic": self.topic,
            "related_topics": self.related_topics[0:self.MAX_RELATED],
            "sources": self.sources[0:self.MAX_SOURCES],
            #"sheets": self.sheets,
        }

    def make_data_from_sheets(self):
        if self.sources_dict and self.related_topics_dict:
            # If count data was already passed down, use it
            sources_dict        = self.sources_dict
            related_topics_dict = self.related_topics_dict
        else:
            # Otherwise, grab all relavant sheets and make a count
            sheets              = get_sheets_by_tag(self.topic)
            sheets_serialized   = []
            sources_dict        = defaultdict(int)
            related_topics_dict = defaultdict(int)
            for sheet in sheets:
                sheets_serialized.append(sheet_to_dict(sheet))
                for source in sheet.get("sources", []):
                    if "ref" in source:
                        sources_dict[source["ref"]] += 1
                for tag in sheet.get("tags", []):
                    if tag != self.topic: 
                        related_topics_dict[tag] += 1
         
        self.sources = sorted(sources_dict.iteritems(), key=lambda (k,v): v, reverse=True)
        self.related_topics = sorted(related_topics_dict.iteritems(), key=lambda (k,v): v, reverse=True)
        #self.sheets = sheets_serialized

    def filter(self, topics):
        """Perform all filtering that may depend on a complete TopicList (related topics),
        or that may require computation to be delyed (Ref validation)"""
        if self._filtered:
            return self
        self.filter_sources()
        self.filter_invalid_sources()
        self.filter_related_topics(topics)
        self._filtered = True
        return self

    def filter_sources(self):
        """ Filters sources that don't have at least X cooccurrences """
        self.sources = [source for source in self.sources if source[1] > 1]
      
    def filter_invalid_sources(self):
        """ Remove any sources that don't validate """
        sources = []
        for source in self.sources:
            try:
                sources.append((Ref(source[0]).normal(), source[1]))
            except:
                pass
        self.sources = sources

    def filter_related_topics(self, topics):
        """ Only allow tags that are present in global `topics` """
        self.related_topics = [topic for topic in self.related_topics if topic[0] in topics]


class TopicsManager(object):
    """
    Interface and cache for all topics data
    """
    def __init__(self):
        self.topics = {}
        self.sorted_topics = {}
        self.make_data_from_sheets()

    def make_data_from_sheets(self):
        """
        Processes all public source sheets to create topic data.
        """
        tags = {}
        results = []
        projection = {"tags": 1, "sources.ref": 1}

        sheet_list = db.sheets.find({"status": "public"}, projection)
        for sheet in sheet_list:
            sheet_tags = sheet.get("tags", [])
            for tag in sheet_tags:
                if tag not in tags:
                    tags[tag] = {
                                    "tag": tag, 
                                    "sources_dict": defaultdict(int),
                                    "related_topics_dict": defaultdict(int)
                                }
                for source in sheet.get("sources", []):
                    if "ref" in source: 
                        tags[tag]["sources_dict"][source["ref"]] += 1
                for related_tag in sheet_tags:
                    if tag != related_tag: 
                        tags[tag]["related_topics_dict"][related_tag] += 1

        for tag in tags:
            topic = Topic(tag, sources_dict=tags[tag]["sources_dict"], related_topics_dict=tags[tag]["related_topics_dict"])
            topic.filter_sources()
            if len(topic.sources) > 0:
                self.topics[tag] = topic

    def get(self, topic):
        if topic in self.topics:
            return self.topics[topic].filter(self.topics)
        else:
            return Topic(topic)

    def is_included(self, topic):
        return topic in self.topics

    def list(self, sort_by="alpha"):
        """ Returns a list of all available topics """
        if sort_by in self.sorted_topics:
            return self.sorted_topics[sort_by]
        else:
            return self._sort_list(sort_by=sort_by)

    def _sort_list(self, sort_by="alpha"):
        sort_keys =  {
            "alpha": lambda x: x["tag"],
            "count": lambda x: -x["count"],
        }
        results = []
        for topic in self.topics.keys():
            results.append({"tag": topic, "count": len(self.topics[topic].sources)})
        results = sorted(results, key=sort_keys[sort_by])

        self.sorted_topics[sort_by] = results

        return results


class TopicSet(abst.AbstractMongoSet):
    recordClass = Topic


topics = TopicsManager()