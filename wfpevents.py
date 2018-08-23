# -*- coding: utf-8 -*-
import scrapy
import urlparse
import dateutil
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class WesternFarmPress(Spider):
    name = 'wfpevents'
    source_crawler = "wfpvents"
    crawl_type = "event"
    version = 0
    allowed_domains = ['http://westernfarmpress.com']
    start_urls = ["http://westernfarmpress.com/events"]
    all_urls = set()

    def parse(self, response):
        events = response.xpath(
            '//*[@id="pm-main-pdg"]/div\
            /div[not(contains(@class,"item-list"))]')
        for event in events:
            url = urlparse.urljoin(response.url, event.xpath(
                ".//h3/a/@href").extract()[0])
            title = event.xpath(".//h3/a/text()").extract()[0]
            time_loc = event.xpath(
                ".//div[@class='time-and-location']/text()").extract()[0]
            meta = {'source_url': url, 'title': title, 'time_loc': time_loc}
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=url,
                                        items_scraped=self.items_scraped)\
                    and url not in self.all_urls:
                self.all_urls.add(url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_event,
                    dont_filter=True,
                    meta=meta)

        pager = response.xpath(
            '//*[@id="pm-main-pdg"]/div\
            /div[contains(@class,"item-list")]\
            /li[contains(@class, "page-next")]')
        if pager:
            url = urlparse.urljoin(response.url, pager.xpath(
                ".//a/@href").extract()[0])
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True)

    def parse_event(self, response):

        # bullshit
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}

        # reqd fields
        item['thumb_urls'] = []
        item['image_urls'] = []
        item['json'] = {}
        # item['json']['caption_images'] = {}
        # item['json']['author'] = None

        # title
        item['json']['title'] = response.meta['title']

        # venue
        venue = response.xpath(
            "//div[@class='event-location clearfix']/strong/text()"
        ).extract()[0]

        address = response.xpath(
            "//div[@class='event-location clearfix']/text()"
        ).extract()
        # street 1
        try:
            street = self.get_text(address[-3])
        except:
            street = None

        # location and zip
        city_st_zip = self.get_text(address[-2])
        if city_st_zip[-1] in '0123456789':
            if '-' == city_st_zip[-5]:
                city_st_zip = city_st_zip[:-5]
                zipcode = city_st_zip[-5:]
                location = city_st_zip[:-6]
            else:
                zipcode = city_st_zip[-5:]
                location = city_st_zip[:-6]
        else:
            zipcode = None
            location = city_st_zip

        # country
        country = self.get_text(address[-1])

        # item['json']['event_location'] = {
        #     'venue': venue,
        #     'street1': street,
        #     'location': location,
        #     'zip': zipcode,
        #     'country': country}

        item['json']['venue'] = venue
        item['json']['street1'] = street
        item['json']['location'] = location
        item['json']['zipcode'] = zipcode
        item['json']['country'] = country

        # dates
        dates = [self.get_text(response.xpath(
            "//div[@class='time-and-location']"
        ).extract()[0]).split(u'\u2022')[0]]

        # process dates
        if '-' in dates[0]:
            dates = dates[0]
            start = dates.split('-')[0] + dates[-4:]
            end = ''.join(dates.split()[:1]) + dates.split('-')[1]
            dates = [start, end]

        # date_list = []
        # for date in dates:
        #     date_list.append(dateutil.parser.parse(date))

        item['json']['date'] = dates

        # content
        content = response.xpath("//div[@class='event-intro clearfix']")
        bulk_content = fromstring(content.extract()[0])
        for child in bulk_content.iterchildren():
            if child.tag != 'p':
                bulk_content.remove(child)
        item['json']['content'] = tostring(bulk_content, encoding="UTF-8")

        email = None
        website = None

        # get links
        links = bulk_content.xpath(".//a/@href")
        if len(links) > 0:
            for link in links:
                if 'mailto:' in link:
                    email = link.lstrip('mailto:').split('?')[0]
                    item['json']['email'] = email
                else:
                    website = link
                    item['json']['website'] = website

        yield item
