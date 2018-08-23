# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class WesternGrowers(Spider):
    name = 'wga'
    source_crawler = 'wga'
    crawl_type = 'news'
    version = 3
    item_parser = "parse_article"
    allowed_domains = ['https://www.wga.com/']
    start_urls = [
        'https://www.wga.com/blog/news',
    ]
    all_urls = set()

    def parse(self, response):
        meta = {}
        nodes = response.xpath(
            "//div[@id='content']//div[@class='node-content']")
        for node in nodes:
            if node.xpath(".//div[@class='field-items']//h3"):
                basic = node.xpath(".//div[@class='field-items']//h3")
                if basic.xpath(".//text()"):
                    title = basic.xpath(".//text()").extract()[0]
                    meta['title'] = title
                if basic.xpath(".//@href"):
                    p_url = basic.xpath(".//@href").extract()[0]
                    url = urlparse.urljoin(response.url, p_url)
                    meta['source_url'] = url
            if node.xpath(".//@src"):
                thumb = node.xpath(".//@src").extract()[0]
                if thumb == "https://www.wga.com/sites/wga.com/files/styles/user_picture_mini/public/default_images/unknown.png?itok=6CsZf1zP":
                    pass
                else:
                    meta['thumb'] = thumb
            if len(title) > 0 and len(url) > 0:
                if not self.check_existance(sourceCrawler='wga',
                                            sourceURL=url,
                                            items_scraped=self.items_scraped) and\
                        url not in self.all_urls:
                    self.all_urls.add(url)
                    yield scrapy.Request(
                        url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=meta)
        if response.xpath("//a[@title='Go to next page']//@href"):
            p_url = response.xpath("//a[@title='Go to next page']//@href").extract()[0]
            url = urlparse.urljoin(response.url, p_url)
            yield scrapy.Request(
                url,
                callback=self.parse,
                dont_filter=True,)

    def parse_article(self, response):

        # basix
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = [response.meta['thumb']] if 'thumb' in response.meta else []
        item['image_urls'] = []
        item['json'] = {}
        title = response.meta['title']
        item['json']['title'] = title

        # detail title
        if len(response.xpath("//h1[@id='page-title']/text()")) > 0:
            title = response.xpath("//h1[@id='page-title']/text()").extract()[0]
            item['json']['title'] = title

        # isolate relevant branch
        region = response.xpath("//div[@class='region region-two-50-first']")[0]
        inner = region.xpath("./div[@class='region-inner clearfix']")[0]
        node = inner.xpath(".//div[@class='node-content']")
        divs = node.xpath("./div")
        b_content = None
        for div in divs:
            if len(div.xpath("../div[contains(@class,'name-body')]//div[@class='field-item even']")) > 0:
                content = div.xpath("../div[contains(@class,'name-body')]//div[@class='field-item even']")
                b_content = fromstring(content.extract()[0])

        # filter branch content (esp. for press release)
        if b_content is not None:
            for p in b_content.xpath("./p"):
                if len(p.xpath(".//*[text()[contains(.,'FOR IMMEDIATE RELEASE')]]")) > 0 or\
                        len(p.xpath(".//*[text()[contains(.,'About')]]")) > 0:
                    b_content.remove(p)
                if len(p.xpath("./text()")) > 0:
                    if 'For interviews, contact:' in p.xpath("./text()")[0]:
                        b_content.remove(p)
                    if '###' in p.xpath("./text()")[0]:
                        b_content.remove(p)
        else:
            return

        # remove contact info ((maybe needs to add addition criteria))
        if b_content.xpath("./p"):
            last_p = b_content.xpath("./p")[-1]
            if 'contact' in ''.join(last_p.xpath("./text()")):
                b_content.remove(last_p)

        # head image
        capd_imgs = {}
        if len(response.xpath("//div[contains(@class,'field-article-image')]")) > 0:
            div = response.xpath("//div[contains(@class,'field-article-image')]")
            img = div.xpath(".//@src").extract()[0]
            if div.xpath(".//@alt"):
                cap = div.xpath(".//@alt").extract()[0]
            else:
                cap = None
            capd_imgs[img] = (cap, title)
            b_content.insert(0, fromstring("<img src='%s'/>" % img))
        item['json']['caption_images'] = capd_imgs
        item['image_urls'] = capd_imgs.keys()

        # basic info
        if response.xpath("//div[@class='field-content']/a/text()"):
            tags = response.xpath("//div[@class='field-content']/a/text()").extract()
        else:
            tags = []
        if response.xpath("//span[@class='field-content']/text()"):
            date = response.xpath("//span[@class='field-content']/text()")[0].extract()
        else:
            date = None
        if response.xpath("//div[@class='user-name']/text()"):
            author = response.xpath("//div[@class='user-name']/text()").extract()[0].strip()
        else:
            author = None

        item['json']['tags'] = tags
        item['json']['date'] = date
        item['json']['author'] = author
        item['json']['content'] = tostring(b_content, encoding='utf-8')
        yield item
