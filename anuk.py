# -*- coding: utf-8 -*-
import scrapy
import urlparse
import re

from data_fetchers.items import DataFetchersItem
from scrapy.selector import Selector
from data_fetchers import utils
from data_fetchers.spider import get_text
from data_fetchers.spider import Spider


REGEX = re.compile(r'andnowuknow\.com/([^/]*)/')


class AnukNewsSpider(Spider):
    name = "anuknews"
    source_crawler = "anuknews"
    crawl_type = "news"
    version = 1
    allowed_domains = []
    start_urls = [
        'http://www.andnowuknow.com/all-news',
    ]
    all_urls = set()

    def parse_item(self, response):
        self.log('Hi, this is an item page! %s' % response.url)
        if "listitem" in response.meta:
            listitem = response.meta['listitem']
        else:
            listitem = {
                "url":response.url,
                "thumb_urls":[]
            }
        item = self.get_new_item(response)
        image_infos=[]
        image_urls = []
        caption_images = {}
        images=response.xpath("//div[@id='story-text']/descendant::img")
        if images:
            for image in images:
                image_src = urlparse.urljoin(response.url, image.xpath(".//@src").extract()[0].strip())
                if image.xpath(".//@alt"):
                    image_alt = image.xpath(".//@alt").extract()[0].strip()
                elif image.xpath(".//@title"):
                    image_alt = image.xpath(".//@title").extract()[0].strip()
                else:
                    image_alt = None
                image_infos.append((image_src,image_alt))
        for image_info in image_infos:
            image_url,image_alt = image_info
            caption_images[image_url] = (None,image_alt)
            image_urls.append(image_url)

        item['image_urls'] = image_urls
        item["json"]["caption_images"] = caption_images

        item['json']['content']=''.join(response.xpath("//div[@id='story-text']").extract())

        item['json']['title'] = get_text(''.join(response.css('.page-header').extract()).strip())
        item['json']['date'] = ''.join(response.css('time.timestamp').
                                       xpath('.//@datetime').extract())
        item['json']['author'] = ''.join(response.css('.authorLink i').
                                         xpath('.//text()').extract())

        item['json']['tags'] = response.css('.terms-on-page-block label')\
            .xpath('string(.)').extract()

        cat_res = REGEX.search(response.url)
        if cat_res:
            item['json']['category'] = cat_res.groups()

        companies = []
        for company in response.css('.media'):
            name = ''.join(company.css('.media-heading')
                           .xpath('string(.)').extract())
            companies.append(name)
        item['json']['companies'] = companies

        item['json']['listitem'] = listitem
        item['json']['item_url'] = response.url
        item['thumb_urls'] = [thumb_url for thumb_url in listitem['thumb_urls'] if not thumb_url.startswith("images")]

        item['html'] = response.body
        htmls_path = {
            listitem['url']:response.body
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = listitem['url']
        return item

    def parse(self, response):
        self.log('========= list is list page! %s' % response.url)

        items = []
        for listitem in response.css('a.thumbnail'):
            item = {}
            url = listitem.xpath('.//@href').extract()[0]
            full_url = urlparse.urljoin(response.url, url)

            item['url'] = full_url
            item['title'] = listitem.css('h4::text').extract()[0]
            item['thumb_urls'] = [
                urlparse.urljoin(response.url, image_url)
                for image_url in listitem.css('img::attr(src)').extract()
                if image_url]
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=item['url'],
                                        items_scraped=self.items_scraped) and \
                    item['url'] not in self.all_urls:
                self.all_urls.add(item['url'])
                items.append(item)
            else:
                self.log('the news has scraped already')

        for item in items:
            yield scrapy.Request(item['url'],
                                 callback=self.parse_item,
                                 meta={'listitem': item})
