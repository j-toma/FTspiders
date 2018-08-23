# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring
from data_fetchers import utils


class Agrilife(Spider):

    name = 'agrilifenews'
    source_crawler = "agrilife"
    crawl_type = "news"
    item_parser="parse_article_content"
    version = 0
    allowed_domains = ['today.agrilife.org']
    start_urls = [
        "http://today.agrilife.org/articles/"
    ]
    all_url = set()

    def parse(self, response):

        for element in response.xpath('//section[@id=\"content\"]/article'):

            # title
            title_1 = element.xpath('.//header/h1/a/text()')
            if title_1:
                title = ''.join(title_1.extract()).strip()

            # source url
            url = ''.join(element.xpath(
                './/header/h1/a/@href'
            ).extract()).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)

                meta = {
                    'title': title,
                    'source_url': source_url
                }
                if not self.check_existance(sourceCrawler='agrilife',
                                            sourceURL=source_url,
                                            items_scraped=self.items_scraped)\
                        and source_url not in self.all_url:
                    self.all_url.add(source_url)

                    yield scrapy.Request(
                        source_url,
                        callback=self.parse_article_content,
                        dont_filter=True,
                        meta=meta
                    )
        # turning pages:
        have_next = ''.join(response.xpath(
            '//div[@class=\"nav-previous\"]/a/text()'
        ).extract()).strip()
        if "Older posts" in have_next:

            next_page = ''.join(response.xpath('//div[@class=\"nav-previous\"]/a/@href').extract()).strip()

            if next_page:
                next_page_url = urlparse.urljoin(response.url, next_page)

                yield scrapy.Request(
                    next_page_url,
                    callback=self.parse,
                    dont_filter=True,
                )

    def parse_article_content(self, response):

        # get the content and remove unnecessary parts
        item = self.get_new_item(response)
        json = item["json"]
        # title
        if response.xpath("//h1[contains(@class,'entry-title')]"):
            title = response.xpath("//h1[contains(@class,'entry-title')]/text()").extract()[0].strip()
        else:
            title = response.meta['title']
        json['title'] = title
        # date
        date = ''.join(response.xpath('//p[@class=\"post-date\"]/a/time/text()').extract()).strip()
        if date:
            json['date'] = date
        # author
        author = {}
        if response.xpath('//div[@id=\"author-description\"]'):
            # author name
            if response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-title\"]'):
                author_name = ''.join(response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-title\"]/text()').extract()).strip()
                author['name'] = author_name
            else:
                author['name'] = None
            # author phone
            if response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-phone\"]'):
                author_phone = ''.join(response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-phone\"]//text()').extract()).strip()
                author['phone'] = author_phone
            else:
                author['phone'] = None
            # author email
            if response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-email\"]'):
                author_email = ''.join(response.xpath('//div[@id=\"author-description\"]/p[@class=\"post-author-email\"]//text()').extract()).strip()
                author['email'] = author_email
            else:
                author['email'] = None
            # author url
            if response.xpath('//div[@id=\"author-description\"]/p[@class=\"author-link\"]'):
                author_url = ''.join(response.xpath('//div[@id=\"author-description\"]/p[@class=\"author-link\"]//text()').extract()).strip()
                author['url'] = author_url
            else:
                author['url'] = None

            json['author'] = author

        # category
        if response.xpath('//p[@class=\"post-categories\"]'):
            category = ''.join(response.xpath('//p[@class=\"post-categories\"]//text()').extract()).strip()
            json['category'] = category

        # topics
        if response.xpath('//p[@class=\"post-tags\"]'):
            topics = ''.join(response.xpath('//p[@class=\"post-tags\"]//text()').extract()).strip()
            json['topics'] = topics
        # region
        if response.xpath('//p[@class=\"region-tax-terms\"]'):
            region = ''.join(response.xpath('//p[@class=\"region-tax-terms\"]//text()').extract()).strip()
            json['region'] = region
        # agency
        if response.xpath('//p[@class=\"agency-tax-terms\"]'):
            agency = ''.join(response.xpath('//p[@class=\"agency-tax-terms\"]//text()').extract()).strip()
            json['agency'] = agency

        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        htmls_path = {}
        htmls_path[response.url] = response.body

        # image section
        image_urls = []
        caption_images = {}

        images = response.xpath('//div[@class=\"pf-content\"]/div[@style=\"width: 310px\"]')
        for image in images:
            # caption_description
            caption_desc = ''.join(image.xpath(
                './p/text()'
            ).extract()).strip()
            # caption_url
            partial_caption_url = ''.join(image.xpath(
                './a/img/@src'
            ).extract()).strip()
            if partial_caption_url:
                url = urlparse.urljoin(
                    response.url, partial_caption_url
                )
                caption_url = url
            else:
                caption_url = None

            # caption alt
            caption_alt = image.xpath('./a//@alt')
            if caption_alt:
                alt = ''.join(image.xpath(
                    './a//@alt'
                ).extract()).strip()

            elif image.xpath('./a//@title'):
                alt = ''.join(image.xpath(
                    './a//@title'
                ).extract()).strip()
            else:
                alt = None
            if caption_url:
                caption_images[caption_url] = (caption_desc, alt)
                image_urls.append(caption_url)
        json['caption_images'] = caption_images
        item['image_urls'] = image_urls

        # content
        article = response.xpath(
            './/div[@class=\"pf-content\"]'
        )
        if article:
            content_document = fromstring(article.extract()[0].strip())
        if not article:
            return
        # image replacement
        captions = content_document.xpath('./div[@style=\"width: 310px\"]')
        if captions:
            for caption in captions:

                keep_img = caption.xpath(
                    './/img'
                )[0]
                caption.addnext(keep_img)
                caption.getparent().remove(caption)

        json["content"] = tostring(content_document, encoding="UTF-8")

        item['json'] = json
        item['image_urls'] = image_urls

        item['htmls_path'] = htmls_path
        item["html"] = response.body

        yield item
