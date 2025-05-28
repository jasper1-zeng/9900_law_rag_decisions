# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class SatscraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class SATItem(scrapy.Item):
    case_url = scrapy.Field()
    case_title = scrapy.Field()
    citation_number= scrapy.Field()
    case_year = scrapy.Field()
    case_act = scrapy.Field()
    case_topic = scrapy.Field()
    member = scrapy.Field()
    heard_date = scrapy.Field()
    delivery_date = scrapy.Field()
    file_no = scrapy.Field()
    case_between = scrapy.Field()
    catchwords = scrapy.Field()
    legislations = scrapy.Field()
    result = scrapy.Field()
    category= scrapy.Field()
    representation = scrapy.Field()
    referred_cases = scrapy.Field()
    reasons = scrapy.Field()