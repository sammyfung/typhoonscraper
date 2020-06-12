# -*- coding: utf-8 -*-
import scrapy


class TyphoonscraperItem(scrapy.Item):
    report_time = scrapy.Field()
    position_time = scrapy.Field()
    position_type = scrapy.Field()
    cyclone_type = scrapy.Field()
    agency = scrapy.Field()
    name = scrapy.Field()
    code = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()
    wind_unit = scrapy.Field()
    wind_speed = scrapy.Field()
    gust_speed = scrapy.Field()
    pressure = scrapy.Field()
