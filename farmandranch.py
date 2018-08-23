# -*- coding: utf-8 -*-
import scrapy
import urlparse
import datetime
from data_fetchers import utils
from data_fetchers.spider import Spider
# from data_fetchers.items import DataFetchersItem
from lxml.html import fromstring, tostring


class FarmandRanch(Spider):
    name = 'farmandranch'
    source_crawler = 'farmandranch'
    crawl_type = 'news'
    item_parser="parse_article"
    version = 0
    allowed_domains = ['http://www.farmandranchguide.com/']
    start_urls = [
        'http://www.farmandranchguide.com/search/advanced/?&skin=/&t=article']
    all_urls = set()

    def parse_article(self, response):

        item = self.get_new_item(response)
        html = response.body
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item['html'] = html
        item["htmls_path"] = {source_url: html}
        item['json']['date'] = response.meta['date']

        # detail title
        if len(response.xpath("//div[@class='title-block']/h1/text()")) > 0:
            title = response.xpath("//div[@class='title-block']/h1/text()").extract()[0]
            item['json']['title'] = title
        else:
            item['json']['title'] = response.meta['title']

        if 'thumb_urls' in response.meta:
            item['thumb_urls'] = response.meta['thumb_urls']

        if response.xpath("//div[@class=\"entry-content\"]"):
            content = fromstring(response.xpath(
                "//div[@class=\"entry-content\"]").extract()[0])
        else:
            content = fromstring("This post has no text content.")

        caption_images = {}
        image_urls = []
        gallery = response.xpath("//div[@id=\"blox-gallery\"]")
        if gallery:
            viewport = gallery.xpath(".//div[@class='viewport']//li")
            if viewport is not None:
                count = 0
                for view in viewport:
                    image_url = view.xpath(".//a/@href")
                    if image_url:
                        image_url = image_url.extract()[0]
                        image_urls.append(image_url)
                        add = "<img src= '%s'/>" % image_url
                        content.insert(count, fromstring(add))
                        count += 1
                        image_cap = view.xpath(".//a/@rel/text()").extract()\
                            if view.xpath(".//a/@rel/text()") else None
                        if image_cap > 2:
                            image_cap = self.get_text(image_cap)
                        caption_images[image_url] = (image_cap, None)
            else:
                imgs = gallery.xpath(".//img/@src")
                for img in imgs:
                    image_url = img.extract().split('?')[0]\
                        if "?" in img.extract()\
                        else img.extract()[0].split['?'][0]
                    image_urls.append(image_url)
                    add = "<img src= '%s'/>" % image_url
                    content.insert(0, fromstring(add))
                    caption = response.xpath(
                        "//li[@class=\"box-shadow\"]/a/@rel").extract()[0]
                    caption_images[image_url] = (caption, None)
        item['json']['caption_images'] = caption_images
        item['image_urls'] = image_urls

        author = response.xpath("//span[@class=\"byline\"]")
        if author.xpath(".//a/text()"):
            item['json']['author'] = author.xpath(".//a/text()").extract()[0]

        if response.xpath(
                "//ul[@class='breadcrumb']/li[@class='active']/a/text()"):
            category = response.xpath(
                "//ul[@class='breadcrumb']/li[@class='active']/a/text()"
            ).extract()[0]
            if category:
                item['json']['category'] = [category]

        taglist = []
        if response.xpath("//div[@class='tag-list']/a/text()"):
            for tag in response.xpath("//div[@class='tag-list']/a/text()"):
                taglist.append(tag.extract())
        item['json']['tags'] = taglist

        item['json']['content'] = tostring(content, encoding="utf-8")

        yield item

    def parse(self, response):
        params = {}

        article_list = response.xpath("//div[@class=\"index-list-item\"]")
        if article_list:
            for article in article_list:
                heading = article.xpath(".//h1")
                if heading:
                    params['title'] = heading.xpath(".//a/text()").extract()[0]
                    article_url = urlparse.urljoin(response.url, heading.xpath(
                        ".//a/@href").extract()[0])
                    params['source_url'] = article_url
                date = article.xpath(".//span[@class=\"time-related\"]")
                if date:
                    if 'hours ago' in date.xpath(
                            ".//span/text()").extract()[0]:
                        date = datetime.datetime.now()
                        params['date'] = date
                    else:
                        params['date'] = date.xpath(
                            ".//span/text()").extract()[0]
                thumb = article.xpath(".//div[@class=\"image no_crop\"]")
                if thumb:
                    thumb_url = urlparse.urljoin(response.url, thumb.xpath(
                        ".//a/img/@src").extract()[0])
                    if '?' in thumb_url:
                        thumb_url = thumb_url.split('?')[0]
                    params['thumb_urls'] = [thumb_url]
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=article_url,
                                            items_scraped=self.items_scraped) and \
                        article_url not in self.all_urls:
                    self.all_urls.add(article_url)
                    yield scrapy.Request(
                        article_url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=params)

        next_page = response.xpath("//li[@class=\"next\"]")
        if next_page:
            next_page = response.xpath("//li[@class=\"next\"]")[0]
            next_url = urlparse.urljoin(response.url, next_page.xpath(
                ".//a/@href").extract()[0])
            yield scrapy.Request(next_url,
                                 callback=self.parse,
                                 dont_filter=True)
