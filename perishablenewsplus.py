# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from lxml.html import fromstring, tostring
from data_fetchers.items import DataFetchersItem
from data_fetchers import utils
from data_fetchers.spider import Spider


class PerishableNewsPlus(Spider):
    name = "perishablenewsplus"
    source_crawler = 'perishablenews'
    crawl_type = 'news'
    version = 1
    allowed_domains = []
    start_urls = [
        # Perishable News the [produce] channel only
        'http://www.perishablenews.com/index.php?channel=8',
    ]
    all_urls = set()

    def parse_item(self, response):
        self.log('Hi, this is an item page! %s' % response.url)
        item = self.get_new_item(response)
        html = response.body_as_unicode().encode('utf-8')
        item['json']['title'] = response.xpath("//title/text()").extract()[0].replace("- PerishableNews","").strip()
        article = response.xpath("//div[contains(@id,'articleScroll')]").extract()[0].strip()
        article_document = fromstring(article)
        # get image urls
        image_urls = []
        caption_images = {}
        for img in article_document.xpath(".//img"):
            src = urlparse.urljoin(response.url,img.xpath(".//@src")[0].encode("UTF-8"))
            if img.xpath(".//@alt"):
                alt = img.xpath(".//@alt")[0].encode("UTF-8")
            elif img.xpath(".//@title"):
                alt = img.xpath(".//@title")[0].encode("UTF-8")
            else:
                alt = None
            image_urls.append(src)
            caption_images[src] = (None,alt)
        item['image_urls'] = image_urls
        item["json"]["caption_images"] = caption_images
        fonts = article_document.xpath('.//font')[:2]
        if len(fonts) == 2:
            # 'by Locus Traxx & Paramount Citrus'
            item['json']['author'] = fonts[0].text[3:]
            fonts[0].getparent().remove(fonts[0])
            # 'Posted: Monday, November 17, 2014 at 9:08AM EST'
            item['json']['date'] = fonts[1].text[8:]
            fonts[1].getparent().remove(fonts[1])
        if article_document.xpath(".//p[starts-with(.,'\r\n\tSource:')]"):
            del_source = article_document.xpath(".//p[starts-with(.,'\r\n\tSource:')]")[0]
            del_source.getparent().remove(del_source)

        summary = tostring(article_document, encoding="UTF-8")
        item['json']['content'] = summary
        item['json']['item_url'] = response.url

        item['html'] = html
        sourceurl = response.meta['source_url']
        htmls_path = {
            sourceurl:html
        }
        item["htmls_path"] = htmls_path
        item['source_url'] = sourceurl

        return item

    def parse(self, response):
        self.log('========= list is list page! %s' % response.url)
        items = response.css("a.reverse::attr(href)").extract()
        for full_url in items:
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=full_url,
                                        items_scraped=self.items_scraped) and \
                    full_url not in self.all_urls:
                self.all_urls.add(full_url)
                yield scrapy.Request(full_url,
                                     callback=self.parse_item,
                                     meta={'source_url': full_url})
            else:
                self.log('the news has scraped already')
