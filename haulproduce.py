# -*- coding: utf-8 -*-
import scrapy
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class HaulProduce(Spider):
    name = 'haulproduce'
    source_crawler = 'haulproduce'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://haulproduce.com/']
    start_urls = ['http://haulproduce.com/archives/']
    all_urls = set()

    def parse_article(self, response):

        # bullshit
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = response.meta['thumb']
        item['json'] = {}
        if response.xpath("//h1[contains(@class,'title')]"):
            item['json']['title'] = response.xpath("//h1[contains(@class,'title')]/text()").extract()[0].strip()
        else:
            item['json']['title'] = response.meta['title']
        item['json']['date'] = response.meta['date']
        item['image_urls'] = []

        # content
        content = response.xpath("//div[@class='entry']").extract()[0]
        bulk_content = fromstring(content)

        # image
        capd_imgs = {}
        for child in bulk_content.iterdescendants():
            if child.tag == 'img':
                url = child.xpath(".//@src")[0]
                capd_imgs[url] = (None, None)
                keep_img = fromstring('<img src="%s"/>' % url)
                if child.getparent().tag == 'a':
                    rent = child.getparent()
                    rent.addnext(keep_img)
                    rent.getparent().remove(rent)
                else:
                    child.addnext(keep_img)
                    child.getparent().remove(child)

        item['json']['caption_images'] = capd_imgs
        item['image_urls'] = capd_imgs.keys()

        # update content
        item['json']['content'] = tostring(bulk_content, encoding='UTF-8')

        # author, tags are null
        item['json']['author'] = None
        item['json']['tags'] = []

        # category
        if response.xpath("//span[@class='categories']/a/text()"):
            category = response.xpath("//span[@class='categories']/a/text()")
            if category.extract()[0] == 'Zingers':
                return
            if category.extract()[0] == 'Health':
                return

        yield item

    def parse_month(self, response):
        articles = response.xpath(
            "//div[@id='main']/div[contains(@class,'post')]")
        for article in articles:
            url = article.xpath(".//h2/a/@href").extract()[0]
            title = article.xpath(".//h2/a/text()").extract()[0]
            date = article.xpath(
                ".//abbr[@class='date time published']/text()").extract()[0]
            if article.xpath(".//img/@src"):
                thumb = [article.xpath(".//img/@src").extract()[0]]
            else:
                thumb = []
            meta = {'url': url, 'title': title, 'date': date, 'thumb': thumb}

            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=url,
                                        items_scraped=self.items_scraped)\
                    and url not in self.all_urls:
                self.all_urls.add(url)
                yield scrapy.Request(
                    url,
                    callback=self.parse_article,
                    dont_filter=True,
                    meta=meta)

        if response.xpath("//a[@class='next page-numbers']"):
            next_page = response.xpath("//a[@class='next page-numbers']")
            url = next_page.xpath("./@href").extract()[0]
            if url:
                yield scrapy.Request(
                    url,
                    callback=self.parse_month,
                    dont_filter=True)

    def parse(self, response):
        archive = response.xpath(
            "//h3[text()='Monthly Archives']/following-sibling::ul")
        for month in archive.xpath("./li"):
            url = month.xpath(".//a/@href").extract()[0]
            yield scrapy.Request(
                url,
                callback=self.parse_month,
                dont_filter=True)
