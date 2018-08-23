# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers.spider import Spider
from data_fetchers import utils
from lxml.html import fromstring, tostring


class FloridaFarmBureau(Spider):
    name = 'floridafarmbureau'
    source_crawler = 'ffb'
    crawl_type = 'news'
    version = 2
    allowed_domains = ['http://www.floridafarmbureau.org']
    start_urls = ['http://www.floridafarmbureau.org/news/press_releases',
                  'http://www.floridafarmbureau.org/blog/from_the_president']

    all_urls = set()

    def parse(self,response):
        params = {}

        news_list = response.xpath("//ul/li[contains(@class, 'views-row')]")
        for li in news_list:
            date = li.xpath(".//div[@class=\"views-field-changed\"]")
            if date:
                params['date'] = ''.join(date.xpath(".//span[@class=\"field-content\"]/text()").extract()).strip()
            link = li.xpath(".//div[@class=\"views-field-link\"]/span[@class=\"field-content\"]")
            if link:
                news_link = urlparse.urljoin(response.url, ''.join(link.xpath(".//a/@href").extract()).strip())
                params['news_link'] = news_link
            if not self.check_existance(sourceCrawler='ffb',
                                        sourceURL=news_link,
                                        items_scraped=self.items_scraped) and news_link not in self.all_urls:
                self.all_urls.add(news_link)
                yield scrapy.Request(
                    news_link,
                    callback=self.parse_news,
                    dont_filter=True,
                    meta=params)
            else:
                self.log("the page has sraped already!!!!")

        next_page = response.xpath("//li[@class=\"pager-next\"]")
        if next_page:
            next_url = urlparse.urljoin(response.url, ''.join(next_page.xpath(".//a/@href").extract()).strip())
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                dont_filter=True)

    def parse_news(self,response):
        item = self.get_new_item()
        item['json']['date'] = response.meta['date']
        item['htmls_path'] = {response.url:response.body}
        item['html'] = response.body
        item['source_url'] = response.url

        item['image_urls'] = []
        item['images'] = []
        item['thumb_urls'] = []
        item['thumbs'] = []

        title = response.xpath("//div[@id=\"content-level2\"]")
        if title:
            item['json']['title'] = ''.join(title.xpath(".//h1/text()").extract()).strip()

        bulk_content = response.xpath("//div[@class=\"content clear-block\"]")
        if bulk_content:
            longest = 0
            for i in range(len(bulk_content)):
                if len(bulk_content[i].extract()) > len(bulk_content[longest].extract()):
                    longest = i
            content = fromstring(bulk_content.extract()[longest].strip())
            del_title = content.xpath(".//p/strong")
            if del_title:
                del_title = del_title[0]
                del_title.getparent().remove(del_title)
            item["json"]["content"] = tostring(content,encoding="UTF-8")

        item['created_time'] = datetime.datetime.now()

        yield item
