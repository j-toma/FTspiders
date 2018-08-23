# -*- coding: utf-8 -*-
import scrapy
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class ProduceProcessing(Spider):
    name = 'proprocess'
    source_crawler = 'proprocess'
    crawl_type = 'news'
    item_parser="parse_article"
    version = 0
    allowed_domains = ['http://produceprocessing.net/']
    start_urls = ['http://produceprocessing.net/news/']
    all_urls = set()

    def parse(self, response):
        article_list = response.xpath("//div[@class='group']")
        for article in article_list:
            title = article.xpath(".//h3//text()").extract()[0]
            url = article.xpath(".//h3/a/@href").extract()[0]
            if url and title:
                meta = {'title': title, 'source_url': url}
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=url,
                                            items_scraped=self.items_scraped) and\
                        url not in self.all_urls:
                    self.all_urls.add(url)
                    yield scrapy.Request(
                        url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=meta)
        next_page = response.xpath("//a[@class='emm-next']/@href")
        if next_page:
            url = response.xpath("//a[@class='emm-next']/@href").extract()[0]
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True)

    def parse_article(self, response):

        # bullshit
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = []
        if response.xpath("//div[contains(@class,'sp-head-news')]/h1"):
            item['json']['title'] = response.xpath("//div[contains(@class,'sp-head-news')]/h1/text()").extract()[0].strip()
        else:
            item['json']['title'] = response.meta['title']

        # date
        date = response.xpath("//div[@class='date']/i/text()")
        if date:
            date = response.xpath("//div[@class='date']/i/text()").extract()[0]
        else:
            date = 'January 1, 2000'
        item['json']['date'] = date

        # content
        content = response.xpath("//div[@class='inside']")
        bulk_content = fromstring(content.extract()[0])
        for child in bulk_content.iterchildren():
            if child.tag == 'script':
                bulk_content.remove(child)
            if 'pager' in child.values():
                bulk_content.remove(child)
        # images
        capd_imgs = {}
        for d in bulk_content.iterdescendants():
            if d.tag == 'img':
                if d.xpath(".//@src"):
                    img_url = d.xpath(".//@src")[0]
                    cap = None
                    if d.xpath(".//@alt"):
                        alt_cap = d.xpath(".//@alt")[0]
                    else:
                        alt_cap = None
                    capd_imgs[img_url] = (cap, alt_cap)
                    keep_img = fromstring('<img src="%s"/>' % img_url)
                    d.addnext(keep_img)
                    d.getparent().remove(d)

        item['json']['caption_images'] = capd_imgs
        item['image_urls'] = capd_imgs.keys()
        item['json']['content'] = tostring(bulk_content, encoding='UTF-8')

        # tags
        tags = []
        tag_list = response.xpath("//div[@class='meta']/a")
        for tag in tag_list:
            tags.append(tag.xpath("./text()").extract()[0])
        item['json']['tags'] = tags

        # no thumbs
        item['thumb_urls'] = []

        # author
        item['json']['author'] = None

        yield item
