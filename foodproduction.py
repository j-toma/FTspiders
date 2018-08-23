# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class FoodProduction(Spider):
    name = 'foodproduction'
    source_crawler = 'foodproduction'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://www.foodproductiondaily.com/']
    start_urls = ['http://www.foodproductiondaily.com/Sectors/Fresh-Produce']
    all_urls = set()

    def parse_article(self, response):

        # galleries
        if len(response.xpath("//div[@class='gallery']")) > 0:
            return

        # bullshit
        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = [response.meta['thm']] if\
            'thm' in response.meta else []
        item['image_urls'] = []
        item['json'] = {}
        if response.xpath("//h1[contains(@class,'headline')]"):
            title = response.xpath("//h1[contains(@class,'headline')]/text()").extract()[0].strip()
        else:
            title = response.meta['title'] if 'title' in response.meta else None
        item['json']['title'] = title
        item['json']['date'] = response.meta['date'] if\
            'date' in response.meta else None
        item['json']['author'] = response.meta['author'] if\
            'author' in response.meta else None

        # TAG -- take evens of span to get tags (xpath to <a> not working)
        tags = response.xpath("//div[@class='related_subjects']\
            //span[@itemprop='keywords']//text()").extract()[::2]
        item['json']['tags'] = tags

        # CONTENT
        if response.xpath("//div[@id='story']"):
            bc = fromstring(response.xpath(
                "//div[@id='story']"
            ).extract()[0])

        # remove skyscraper
        for d in bc.iter():
            if d.items() == [('id', 'Skyscraper1')]:
                d.getparent().remove(d)
        if len(bc.xpath("//div[@id='TextAd']")) > 0:
            ad = bc.xpath("//div[@id='TextAd']")[0]
            ad.getparent().remove(ad)

        # IMAGES
        capd_imgs = {}
        # from top
        if len(response.xpath("//div[@class='large_image']")) > 0:
            img = response.xpath("//div[@class='large_image']")
            img_url = img.xpath(".//@src").extract()[0]
            cap = img.xpath(".//@alt").extract()[0]
            capd_imgs[img_url] = (cap, None)
            bc.insert(0, fromstring("<img src='%s'/>" % img_url))
        # from content
        imgs = bc.xpath(".//img")
        for img in imgs:
            cap = None
            url = img.xpath("./@src")[0]
            for anc in img.iterancestors():
                if anc.items() == [('class', 'class-image')]:
                    if len(anc.xpath(".//p[@class='caption']/text()")) > 0:
                        cap = anc.xpath(".//p[@class='caption']/text()")[0]
                    elif len(anc.xpath(
                            ".//div[@class='attribute-caption']/p/text()")) > 0:
                        cap = anc.xpath(
                            ".//div[@class='attribute-caption']/p/text()")[0]
                    break
            capd_imgs[url] = (cap, None)
            kp_img = fromstring("<img src='%s'/>" % url)
            img.addnext(kp_img)
            img.getparent().remove(img)

        item['image_urls'] = capd_imgs.keys()
        item['json']['caption_images'] = capd_imgs

        item['json']['content'] = tostring(bc, encoding='utf-8')
        yield item

    def parse(self, response):
        meta = {}
        articles = response.xpath("//div[@class='news_line']")
        for article in articles:
            url = ""
            if len(article.xpath("./div[@class='thumb_img']/img/@src")) > 0:
                meta['thumb'] = article.xpath(
                    "./div[@class='thumb_img']/img/@src").extract()[0]
            if article.xpath("./div[@class='details indent']"):
                dtls = article.xpath("./div[@class='details indent']")
                if dtls.xpath("./h2/a/text()"):
                    meta['title'] = dtls.xpath("./h2/a/text()").extract()[0]
                if dtls.xpath("./h2/a/@href"):
                    url = urlparse.urljoin(response.url, dtls.xpath(
                        "./h2/a/@href").extract()[0])
                    meta['url'] = url
                if dtls.xpath("./div[@class='byline']"):
                    byln = dtls.xpath("./div[@class='byline']")
                    if len(byln.xpath("./a")) > 0:
                        date = byln.xpath(
                            "./text()").extract()[0].rstrip(' - By')
                        author = byln.xpath(
                            "./a/text()").extract()[0].rstrip('+')
                    elif len(byln.xpath("./text()")) > 0:
                        if ' - By ' in byln.xpath("./text()").extract()[0]:
                            date = byln.xpath(
                                "./text()").extract()[0].split(' - By ')[0]
                            author = byln.xpath(
                                "./text()").extract()[0].split(' - By ')[1]
                        else:
                            date = byln.xpath("./text()").extract()[0]
                            author = ''
                    if len(author) > 0:
                        meta['author'] = author
                    if len(date) > 0:
                        meta['date'] = date
            if len(url) > 0:
                if not self.check_existance(sourceCrawler=self.source_crawler,
                                            sourceURL=url,
                                            items_scraped=self.items_scraped) and\
                        url not in self.all_urls:
                    self.all_urls.add(url)
                    yield scrapy.Request(
                        url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=meta
                    )
        if response.xpath("//span[@class='next']"):
            nxt_pg = response.xpath(
                "//span[@class='next']/a/@href").extract()[0]
            nxt_url = urlparse.urljoin(response.url, nxt_pg)
            yield scrapy.Request(
                nxt_url,
                callback=self.parse,
                dont_filter=True
            )
