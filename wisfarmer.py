# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
import copy
from data_fetchers import utils


class Wisfarmer(Spider):

    name = 'wisfarmer_news'
    source_crawler = "wisfarmer"
    crawl_type = "news"
    version = 0
    allowed_domains = ['www.wisfarmer.com']
    start_urls = [
        "http://www.wisfarmer.com/news/headlines/",
        "http://www.wisfarmer.com/newsbriefs/state/",
        "http://www.wisfarmer.com/newsbriefs/midwest/",
        "http://www.wisfarmer.com/newsbriefs/national/",
    ]
    all_url = set()

    def parse(self, response):

        for element in response.xpath('//div[@class=\"stacked_headlines\"]/ul/li'):
            # title
            title = ''.join(element.xpath('.//text()').extract()).strip()

            # source url
            url = ''.join(element.xpath('./a/@href').extract()).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)

            meta = {
                'title': title,
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler='wisfarmer',
                                        sourceURL=source_url,
                                        items_scraped=self.items_scraped)\
                    and source_url not in self.all_url:
                self.all_url.add(source_url)

                yield scrapy.Request(
                    source_url,
                    callback=self.parse_article_content,
                    dont_filter=True,
                    meta=copy.deepcopy(meta)
                )

    def parse_article_content(self, response):
        # htmls path
        htmls_path = {}
        htmls_path[response.url] = response.body
        # item and json
        item = self.get_new_item()
        json = {}
        # title
        title = response.meta['title']
        json['title'] = title
        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        # date
        date = ''.join(response.xpath('//div[@class=\"article_header\"]/div[@class=\"authorinfo\"]/p[@class=\"pubdate\"]/text()').extract()).strip()
        if date:
            json['date'] = date
        # author
        authors = {}
        author_name = ''.join(response.xpath('//div[@class=\"article_header\"]/div[@class=\"authorinfo\"]/p[@class=\"byline\"]//text()').extract()).strip()
        if author_name:
            authors['author_name'] = author_name
        json['authors'] = authors

        # content
        content = ''.join(response.xpath('//div[@class=\"article_body\"]//text()').extract()).strip()
        if content:
            json['content'] = content
        item['json'] = json
        item['htmls_path'] = htmls_path
        item["html"] = response.body

        yield item
