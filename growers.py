# -*- coding: utf-8 -*-
import scrapy
from lxml.html import fromstring, tostring
from data_fetchers.spider import Spider


class Growers(Spider):
    name = 'growers'
    source_crawler = 'growers'
    crawl_type = 'news'
    item_parser="parse_article"
    version = 0
    allowed_domains = [
        'http://vegetablegrowersnews.com/',
        'http://fruitgrowersnews.com/'
    ]
    start_urls = [
        'http://vegetablegrowersnews.com/index.php/news',
        'http://fruitgrowersnews.com/index.php/news'
    ]
    all_urls = set()

    def parse(self, response):
        meta = {}
        articles = response.xpath("//li[contains(@class,'entry')]")
        for article in articles:
            if len(article.xpath(".//h3/a/text()")) > 0:
                title = article.xpath(".//h3/a/text()").extract()[0]
                meta['title'] = title
            if len(article.xpath(".//h3/a/@href")) > 0:
                url = article.xpath(".//h3/a/@href").extract()[0]
                meta['source_url'] = url
            if len(article.xpath(".//h4/text()")) > 0:
                date = article.xpath(".//h4/text()").extract()[0]
                meta['date'] = date
            if len(meta.keys()) == 3:
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
        if len(response.xpath("//p[@class='body paginate']/a[text()='>']")) > 0:
            url = response.xpath("//p[@class='body paginate']/a[text()='>']/@href").extract()[0]
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_article(self, response):
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        if response.xpath("//h2[contains(@class,'serif')]"):
            title = response.xpath("//h2[contains(@class,'serif')]/text()").extract()[0].strip()
        else:
            title = response.meta['title']
        item['json']['title'] = title
        item['json']['date'] = response.meta['date']
        item['json']['author'] = None

        if len(response.xpath("//div[@class='body news'][2]")) > 0:
            content = fromstring(response.xpath("//div[@class='body news'][2]").extract()[0])

        # del timestamp
        if len(content.xpath("./p[@class='timestamp']")) > 0:
            content.remove(content.xpath("./p[@class='timestamp']")[0])

        # del empty content
        if len(tostring(content)) < 850:
            return

        # get images
        capd_imgs = {}
        imgs = content.xpath(".//img")
        for img in imgs:
            if len(img.xpath("./@src")) > 0:
                url = img.xpath("./@src")[0]
                # get cap from url
                period = url.rfind(".")
                slash = url.rfind("/") + 1
                r_cap = url[slash:period]
                if any(char.isdigit() for char in r_cap):
                    cap = None
                elif "_" in r_cap:
                    cap = r_cap.replace("_", " ")
                elif "-" in r_cap:
                    cap = r_cap.replace("-", " ")
                else:
                    cap = r_cap
                capd_imgs[url] = (cap, None)
                kp_img = fromstring("<img src='%s'/>" % url)
                img.addnext(kp_img)
                img.getparent().remove(img)
        item['image_urls'] = capd_imgs.keys()
        item['json']['caption_images'] = capd_imgs

        item['json']['content'] = tostring(content, encoding='utf-8')

        yield item
