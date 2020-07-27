# -*- coding: utf-8 -*-
import scrapy, io, os, re
from typhoonscraper.items import TyphoonscraperItem as TCItem
from datetime import datetime, timedelta


class JtwcSpider(scrapy.Spider):
    name = 'jtwc'
    ktstokmh = 1.852
    wind_unit = u'KMH'

    def __init__(self, **kwargs):
        try:
            self.proxy = os.environ['JTWC_PROXY']
        except KeyError:
            self.proxy = ''
        self.allowed_domains = [ "metoc.navy.mil", self.proxy ]
        if re.search('[a-z]', self.proxy):
            url = 'https://%s/www.metoc.navy.mil/jtwc/rss/jtwc.rss' % self.proxy
        else:
            url = 'https://www.metoc.navy.mil/jtwc/rss/jtwc.rss'
        self.start_urls = [ url ]

    def conv_reporttime(self, report_time):
        # Convert Report Time to Time in ISO Format
        now = datetime.now()
        if len(report_time) != 6:
            report_time = re.split('\W+',report_time)[2]
        try:
            report_time_new = u"%s%s%s%s" % (now.year, now.month, report_time, 'UTC')
            report_time_new = datetime.strptime(report_time_new, '%Y%m%d%H%M%Z')+timedelta(hours=8)
        except ValueError:
            report_time_new = u"%s%s%s%s" % (now.year, now.month - 1, report_time, 'UTC')
            report_time_new = datetime.strptime(report_time_new, '%Y%m%d%H%M%Z') + timedelta(hours=8)
        return report_time_new.isoformat()

    def parse(self, response):
        items = []
        if self.proxy == '':
            prefix = 'https://'
        else:
            prefix = 'https://%s/' % self.proxy
        # Checking overview reports
        items += [ scrapy.Request(url='%s%s'%(prefix,
                                              'www.metoc.navy.mil/jtwc/products/abpwweb.txt'),
                                  callback=self.parse_overview),
                   scrapy.Request(url='%s%s'%(prefix,
                                              'www.metoc.navy.mil/jtwc/products/abioweb.txt'),
                                  callback=self.parse_overview)]
        # Checking for Tropical Cyclone reports found in over reports
        rss_items = response.xpath('//rss/channel/item/description/text()').extract()
        for i in rss_items:
            rss_item = scrapy.Selector(text=i)
            url = rss_item.xpath('//ul/li/a/@href').extract()
            for j in url:
                if re.search('[ew]p\d{4}web.txt', j):
                    new_url = re.sub('www.metoc.navy.mil', '%s/www.metoc.navy.mil' % self.proxy, j)
                    items += [ scrapy.Request(url=new_url,
                                              callback=self.parse_tc) ]
        return items

    def parse_tc(self, response):
        tc_items = []
        code = ''
        name = ''
        report_time = ''
        forecast = False
        report = io.BytesIO(response.body)
        lines = report.readlines()
        for line in lines:
            line = str(line, encoding='utf-8')
            if re.search('^WTPN', line):
                report_time = self.conv_reporttime(line)
            # ### Analyse TC Report ###
            # Tropical Cyclone Basic Information
            if re.search('^1\. ', line):
                if re.search(u'\(', line):
                    name = re.split('\(',line)[1]
                    name = re.split('\)',name)[0]
                    name = u"%s"%name.upper()
                for i in re.split(' ', line):
                    if re.search('\d{2}[EW]', i):
                        code = u"%s"%i
            # Getting current warning position
            elif re.search(u'^\s*FORECASTS:',line):
                forecast = True
            elif re.search(u'Z --- ', line):
                tc = TCItem()
                tc['agency'] = self.name
                tc['code'] = code
                tc['name'] = name
                tc['report_time'] = report_time
                if forecast:
                    tc['position_type'] = u"F"
                else:
                    tc['position_type'] = u"C"
                for i in re.split(' ', line):
                    if re.search(u'\d{6}Z', i):
                        # Getting position time
                        tc['position_time'] = self.conv_reporttime(i[:6])
                    if re.search(u'\dN', i):
                        tc['latitude'] = round(float(re.sub('N','',i)), 2)
                    if re.search(u'\dS', i):
                        tc['latitude'] = 0 - round(float(re.sub('S','',i)), 2)
                    if re.search(u'\dE', i):
                        tc['longitude'] = round(float(re.sub('E.*','',i)), 2)
                    if re.search(u'\dW', i):
                        tc['longitude'] = 0 - round(float(re.sub('W.*','',i)), 2)
            elif re.search('MAX SUSTAINED WINDS - ', line):
                line = re.sub(u'.*WINDS - ','',line)
                line = re.split(' ', line)
                wind_speed = int(round(int(line[0])*self.ktstokmh, 0))
                tc['wind_speed'] = wind_speed
                tc['gust_speed'] = int(round(int(line[3])*self.ktstokmh, 0))
                if tc['wind_speed'] < 62:
                    tc['cyclone_type'] = u"TD"
                elif tc['wind_speed'] < 118:
                    tc['cyclone_type'] = u"TS"
                elif tc['wind_speed'] < 240:
                    tc['cyclone_type'] = u"TY"
                else:
                    tc['cyclone_type'] = u"STY"
                tc['wind_unit'] = self.wind_unit
                tc_items.append(tc)
        return tc_items

    def parse_overview(self, response):
        nwarea = False
        tdarea = False
        m = '' # Message Paragraph
        tc = [] # List of Tropical Cyclones
        td = [] # List of Tropical Disturbances
        report_time = ''
        item_list = []
        report = io.BytesIO(response.body)
        lines = report.readlines()
        rl = str(lines[0])
        rl = re.sub('\r', '', rl)
        for line in lines:
            line = str(line)
            if re.search(u'^ABPW10',line):
                report_time = self.conv_reporttime(line)
            if re.search(u'B. TROPICAL DISTURBANCE SUMMARY:',line):
                if len(tc) > 0:
                    if not(re.search(u'NO OTHER SUSPECT AREA',m) or re.search(u'NO OTHER TROPICAL CYCLONE',m)):
                        tc = tc + [m]
                m = ""
                tdarea = True
            elif re.search(u'^\s*\([0-9]*\)',line) and len(m) > 0:
                if tdarea == False:
                    # add to Tropical Cyclone line
                    tc = tc + [m]
                elif not(re.search(u'IS NOW THE SUBJECT OF A TROPICAL CYCLONE WARNING',m)):
                    # add to Tropical Disturbance list
                    td = td + [m]
                m = ""
            if not(re.search(u'A. TROPICAL CYCLONE SUMMARY:',line) or \
                    re.search(u'B. TROPICAL DISTURBANCE SUMMARY:',line)):
                m = m + line

        # Analyse Tropical Disturbance Information
        num = 0
        print(len(td))
        for d in td:
            d = re.sub("\r\n"," ",d)
            d = re.sub("\n"," ",d)
            d = re.sub("  *"," ",d)
            if re.search(u'HAS PERSISTED NEAR', d):
                item = TCItem()
                item['report_time'] = report_time
                item['position_time'] = report_time
                item['position_type'] = u'C'
                item['cyclone_type'] = u'LPA'
                item['agency'] = self.name
                item['name'] = u''
                item['code'] = u'%sW'%(99-num)
                d = re.sub(".*HAS PERSISTED NEAR ","",d)
                if re.search(u'\dN', d):
                    item['latitude'] = round(float(re.sub("N.*","",d)), 2)
                elif re.search(u'\dS', d):
                    item['latitude'] = 0 - round(float(re.sub("S.*", "", d)), 2)
                if re.search(u'\dE', d):
                    item['longitude'] = round(float(re.sub("E.*","",re.sub(".*[0-9][NS] ","",d))), 2)
                elif re.search(u'\dW', d):
                    item['longitude'] = 0 - round(float(re.sub("W.*","",re.sub(".*[0-9][NS] ","",d))), 2)
                item_list.append(item)
                num += 1
        return item_list

