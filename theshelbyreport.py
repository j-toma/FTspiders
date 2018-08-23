# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
import copy
from data_fetchers import utils


class Theshelbyreport(Spider):

    name = 'theshelbyreport_product_news'
    source_crawler = "theshelbyreport"
    crawl_type = "news"
    version = 0
    allowed_domains = ['www.theshelbyreport.com']
    start_urls = [
        "http://www.theshelbyreport.com/1-product-news/page/1/"

    ]
    all_url = set()

    def parse(self, response):
        # find the last page:
        first_element = response.xpath('//div[@class=\"pagination\"]//text()').extract()[0]
        if first_element == '1':

            last_page_link = response.xpath('//div[@class=\"cat-body\"]/div[@class=\"pagination\"]//a')
            last_page = last_page_link.xpath('.//@href').extract()[-1]
            last_page_number = last_page.split('page')[1]
            real_last_page_number = last_page_number.replace("/", "")
            best_last_page_number = int(real_last_page_number)
            meta = {
                'last_page': best_last_page_number
            }
            yield scrapy.Request(
                response.url,
                callback=self.parse_article_list,
                dont_filter=True,
                meta=copy.deepcopy(meta)
            )

    def parse_article_list(self, response):

        for element in response.xpath('//ul[@class=\"nb1 cat-grid grid-col-2 clearfix\"]/li'):
            # title
            title_1 = element.xpath('.//h2[@itemprop=\"name\"]/a')
            if title_1:
                title = ''.join(title_1.xpath('./text()').extract()[0]).strip()
            # source url
            url = ''.join(title_1.xpath('./@href').extract()[0]).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)

            # thumbnail
            thumb_1 = element.xpath('./figure/a/img/@src')
            thumb_urls = []
            if thumb_1:
                thumb_2 = ''.join(thumb_1.extract()).strip()
                thumb = urlparse.urljoin(response.url, thumb_2)
                thumb_urls.append(thumb)

            meta = {
                'title': title,
                'thumb_urls': thumb_urls,
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler='theshelbyreport',
                                        sourceURL=source_url,
                                        items_scraped=self.items_scraped)\
                    and source_url not in self.all_url:
                self.all_url.add(source_url)

                yield scrapy.Request(
                    source_url,
                    callback=self.parse_article_content,
                    dont_filter=True,
                    meta=copy.deepcopy(meta)
                )
        last_page = response.meta['last_page']
        for page in range(2, (last_page + 1)):
            next_page = "http://www.theshelbyreport.com/1-product-news/page/" + str(page)
            meta["last_page"] = last_page

            yield scrapy.Request(
                next_page,
                callback=self.parse_article_list,
                dont_filter=True,
                meta=copy.deepcopy(meta)
            )

    def parse_article_content(self, response):
        # item and json
        item = self.get_new_item(response)
        json = item["json"]
        # title
        if response.xpath("//h1[contains(@class,'entry-title')]"):
            title = response.xpath("//h1[contains(@class,'entry-title')]/text()").extract()[0].strip()
        else:
            title = response.meta['title']
        json['title'] = title
        # thumbnail url
        thumb_urls = response.meta['thumb_urls']
        item['thumb_urls'] = thumb_urls
        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url

        # author
        authors = {}
        element = response.xpath('//div[@class=\"author-bio-content\"]')

        # author name
        name = ''.join(element.xpath('./div/a[@itemprop=\"author\"]/text()').extract()).strip()
        if name:
            authors['name'] = name
        # author twitter
        twitter_link = element.xpath('./ul[@class=\"author-bio-social\"]/li[@class=\"twitter\"]')
        if twitter_link:
            twitter = ''.join(twitter_link.xpath('.//@href').extract()).strip()
            authors['twitter'] = twitter
        # author linkedin
        linkedin_link = element.xpath('./ul[@class=\"author-bio-social\"]/li[@class=\"linkedin\"]')
        if linkedin_link:
            linkedin = ''.join(linkedin_link.xpath('.//@href').extract()).strip()

            authors['linkedin'] = linkedin
        # author email
        email_section = response.xpath('//li/a[contains(@href,"mailto")]')
        email_part = ''.join(email_section.xpath('.//@href').extract()).strip()

        email = email_part.split("to:")[1]
        if email:
            authors['email'] = email
        # put'em in
        json['authors'] = authors

        # date
        date = ''.join(response.xpath('//article/header//div[@class=\"entry-post-meta\"]/div/time/text()').extract()).strip()
        if date:
            json['date'] = date

        htmls_path = {}
        htmls_path[response.url] = response.body
        image_urls = []
        caption_images = {}

        images = response.xpath('//div[@class=\"entry-content-data has_f_image\"]//figure')
        if images:
            for image in images:
                # caption_description
                caption_desc = None
                # caption_url
                image_url = ''.join(image.xpath('/img//@src').extract()).strip()
                # alt
                if image.xpath('/img//@alt'):
                    alt = ''.join(image.xpath('/img//@alt').extract()).strip()
                elif image.xpath('/img//@title'):
                    alt = ''.join(image.xpath('/img//@title').extract()).strip()
                else:
                    alt = None
                if image_url:
                    image_urls.append(image_url)
                    caption_images[image_url] = (caption_desc, alt)

        # content
        content = ''.join(response.xpath('//div[@class=\"entry-content clearfix\"]//p/text()').extract()).strip()
        if content:
            json['content'] = content
        item['image_urls'] = image_urls
        item['json'] = json
        item['htmls_path'] = htmls_path
        item["html"] = response.body

        yield item
