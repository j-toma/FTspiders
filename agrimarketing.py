# -*- coding: utf-8 -*-
from data_fetchers.spider import Spider


class WesternFarmPress(Spider):
    name = 'agrimarketing'
    source_crawler = "agrimarketing_events"
    crawl_type = "news"
    version = 0
    allowed_domains = ['http://www.agrimarketing.com/']
    start_urls = ["http://www.agrimarketing.com/arsg.php"]
    all_urls = set()

    def parse(self, response):

        if len(response.xpath(
                "//table[@cellpadding='3']//td[@valign='top']")) > 0:
            events = response.xpath(
                "//table[@cellpadding='3']//td[@valign='top']")
            for event in events:
                item = self.get_new_item(response)
                html = event.extract()
                item['html'] = html
                source_url = "http://www.agrimarketing.com/arsg.php"
                item['source_url'] = source_url
                item["htmls_path"] = {source_url: html}

                # reqd fields
                item['thumb_urls'] = []
                item['image_urls'] = []
                item['json'] = {}
                if event.xpath(".//b/text()") > 0:
                    item['json']['name'] = event.xpath(".//b/text()").extract()[0]
                descs = event.xpath(".//text()")
                for desc in descs:
                    info = desc.extract()
                    if info[-2:].isupper() and 'location' not in item['json'].keys():
                        location = info
                        item['json']['location'] = location
                        continue
                    if info[:6] == 'Phone:':
                        tel = info[8:]
                        tel = tel.replace('-', '')
                        tel = tel.replace('/', '')
                        item['json']['tel'] = tel
                        continue
                    if info[:9] == 'Toll-free':
                        toll = info[-12:]
                        toll = toll.replace('-', '')
                        toll = toll.replace('/', '')
                        item['json']['toll'] = toll
                        continue
                    if info[:3] == 'Fax':
                        fax = info[-12:]
                        fax = fax.replace('-', '')
                        fax = fax.replace('/', '')
                        item['json']['fax'] = fax
                        continue
                    if '@' in info:
                        email = info
                        item['json']['email'] = email
                        continue
                    if 'www.' in info and 'website' not in item['json']:
                        website = info
                        item['json']['website'] = website
                        continue
                    if 'facebook.com' in info:
                        facebook = info
                        item['json']['facebook'] = facebook
                        continue
                    if 'twitter.com' in info:
                        twitter = info
                        item['json']['twitter'] = twitter
                        continue
                    if 'Show: ' in info:
                        year = info[:4]
                        get_month = info.find(':')
                        month = info[(get_month + 2):(get_month + 5)]
                        get_days = info.find(',')
                        days = info[get_month + 6:get_days]
                        start = days.split('-')[0]
                        if len(days.split('-')) > 1:
                            end = days.split('-')[1]
                        else:
                            end = start
                        start_date = year + ' ' + month + ' ' + start
                        end_date = year + ' ' + month + ' ' + end
                        item['json']['start_date'] = start_date
                        item['json']['end_date'] = end_date
                        yield item
