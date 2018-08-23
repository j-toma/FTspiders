# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from data_fetchers import utils
from lxml.html import fromstring, tostring


class AgAlert(Spider):
    name = 'agalert'
    source_crawler = 'agalert'
    crawl_type = 'news'
    version = 0
    allowed_domains = ['http://www.agalert.com/']
    start_urls = ['http://www.agalert.com/']
    all_urls = set()

    def parse(self, response):
        articles = response.xpath("//span[@class='homepageheadline']")[:-1]
        for article in articles:
            part_url = article.xpath(".//@href")
            if part_url:
                url = urlparse.urljoin(response.url, part_url[0].extract())
                title = article.xpath(".//a/text()")[0].extract()
                if url and title:
                    meta = {'url': url, 'title': title}
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

    def parse_article(self, response):

        item = self.get_new_item(response)
        html = response.body
        item['html'] = html
        source_url = response.meta['url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}
        item['thumb_urls'] = []
        item['json'] = {}
        if response.xpath("//h1[contains(@class,'headline')]"):
            item['json']['title'] = response.xpath("//h1[contains(@class,'headline')]/text()").extract()[0].strip()
        else:
            item['json']['title'] = response.meta['title']

        # date
        if response.xpath("//div[@id='issuedate']/a"):
            date = response.xpath(
                "//div[@id='issuedate']/a/text()").extract()[0]
            item['json']['date'] = date
        # author
        if response.xpath("//div[@id='byline']") and response.xpath("//div[@id='byline']/text()"):
            author = response.xpath("//div[@id='byline']/text()").extract()[0]
            if author[:3] == 'By ':
                author = self.get_text(author.lstrip('By ').strip())
                item['json']['author'] = author

        # main text
        story = response.xpath("//div[@id='story']")
        text = story.xpath("./p")
        text_copy = text[:]
        if text:
            for p in text:
                if item['json']['author'] in p.extract():
                    text_copy.remove(p)
                elif 'Permission for use' in p.extract():
                    text_copy.remove(p)
            text = ''.join(text_copy.extract())
            bulk_content = fromstring(text)

        # main pictures
        caption_images = {}
        if story.xpath(".//div[@class='storyimage_image']"):
            for img in story.xpath(".//div[@class='storyimage_image']"):
                if img.xpath(".//@src"):
                    part_img_url = img.xpath(".//@src").extract()[0]
                    img_url = urlparse.urljoin(response.url, part_img_url)
                if img.xpath(".//div[@class='storyimage_caption']"):
                    img_cap = img.xpath(
                        ".//div[@class='storyimage_caption']/text()"
                    )[0].extract()
                else:
                    img_cap = None
                if img_url:
                    caption_images[img_url] = (img_cap, None)
                    add_img = "<img src= '%s' />" % img_url
                    bulk_content.insert(0, fromstring(add_img))
        item['json']['caption_images'] = caption_images
        if caption_images != {}:
            item['image_urls'] = caption_images.keys()
        else:
            item['image_urls'] = []

        # thumbs
        # thumb_locs = response.xpath("//*[contains(text(),'thumb')]")
        # thumbs = thumb_locs.xpath("//*[contains(@src,'/story/images/')]//@src")
        thumb_urls = []
        # for thumb in thumbs:
        #     thumb_urls.append(urlparse.urljoin(response.url, thumb.extract()))
        item['thumb_urls'] = thumb_urls

        item['json']['content'] = tostring(bulk_content, encoding='UTF-8')

        yield item
