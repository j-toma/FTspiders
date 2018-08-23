# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class Agwired(Spider):
    name = 'agwired'
    source_crawler = "agwired"
    crawl_type = "news"
    version = 0
    allowed_domains = ['http://agwired.com/']
    start_urls = ['http://agwired.com/']
    all_urls = set()

    def parse(self, response):

        meta = {}
        articles = response.xpath('//div[@class=\"x-main left\"]/article')
        for article in articles:
            # url
            url = ''.join(article.xpath(
                './/h2[@class=\"entry-title\"]/a/@href').extract()).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)
                meta['source_url'] = source_url
            # title
            title = ''.join(article.xpath(
                './/h2[@class=\"entry-title\"]/a/text()').extract()).strip()
            if title:
                meta['title'] = title
            # author
            author_name = ''.join(article.xpath(
                './/p[@class=\"p-meta\"]//text()').extract()[0]).strip()
            if author_name:
                meta['author'] = author_name
            # date
            date = ''.join(article.xpath(
                './/p[@class=\"p-meta\"]//text()').extract()[1]).strip()
            if date:
                meta['date'] = date

            if 'source_url' in meta and 'title' in meta:
                if not self.check_existance(sourceCrawler='agwired',
                                            sourceURL=source_url,
                                            items_scraped=self.items_scraped) and\
                        source_url not in self.all_urls:
                    self.all_urls.add(source_url)
                    yield scrapy.Request(
                        source_url,
                        callback=self.parse_article,
                        dont_filter=True,
                        meta=meta)

        # turning pages:
        if u'\u2192' in response.xpath('//ul[@class=\"center-list center-text\"]/li//text()').extract():
            next_page = response.xpath('//ul[@class=\"center-list center-text\"]//li')
            next_page_url = next_page.xpath('.//@href').extract()[-1]
            yield scrapy.Request(
                next_page_url,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_article(self, response):

        # print response.url

        item = self.get_new_item(response)
        html, source_url = response.body, response.meta['source_url']
        item['source_url'] = source_url
        item['html'] = html
        item['htmls_path'] = {source_url: response.body}
        item['json'] = {}
        item['json']['author'] = response.meta['author']
        item['json']['date'] = response.meta['date']

        # detail title
        if len(response.xpath("//h1[@class='entry-title']/text()")) > 0:
            title = response.xpath("//h1[@class='entry-title']/text()").extract()[0]
            item['json']['title'] = title
        else:
            item['json']['title'] = response.meta['title']

        img_urls = []
        capd_imgs = {}
        if response.xpath("//div[@class='entry-content content']"):
            bulk_content = fromstring(response.xpath(
                "//div[@class='entry-content content']").extract()[0])
            if bulk_content.xpath(".//img"):
                for img in bulk_content.xpath(".//img"):
                    img_url = img.xpath(".//@src")[0]
                    img_urls.append(img_url)
                    # if img.xpath("../..")[0].xpath(".//p[@class='wp-caption-text']"):
                    #     cap = img.xpath("../..")[0].xpath(".//p[@class='wp-caption-text']/text()")[0]
                    # else:
                    #     cap = None
                    cap = None
                    if img.xpath("../..//@alt"):
                        alt_cap = img.xpath("../..//@alt")[0]
                    else:
                        alt_cap = None
                    capd_imgs[img_url] = (cap, alt_cap)
                    keep_img = fromstring("<img src='%s'/>" % img_url)
                    img.getparent().addnext(keep_img)
                    if img.xpath("../..")[0].xpath(".//p[@class='wp-caption-text']"):
                        bulk_content.remove(img.getparent())
                    else:
                        img.getparent().remove(img)

        item['json']['content'] = tostring(bulk_content, encoding="UTF-8")
        item['image_urls'] = img_urls
        item['thumb_urls'] = []
        item['json']['caption_images'] = capd_imgs

        tags = []
        if response.xpath("//article/span/a"):
            tg_lnks = response.xpath("//article/span/a")
            for tg_link in tg_lnks:
                if tg_link.xpath(".//text()"):
                    tags.append(tg_link.xpath(".//text()").extract()[0].strip())
        item['json']['tags'] = tags

        yield item
