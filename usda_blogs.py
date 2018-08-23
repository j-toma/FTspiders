# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring
import copy


class UsdaBlogs(Spider):
    name = 'usda_blogs'
    source_crawler = "usda_blogs"
    crawl_type = "news"
    item_parser="parse_article_content"
    version = 0
    allowed_domains = ['blogs.usda.gov']
    start_urls = [
        "http://blogs.usda.gov/"
    ]
    all_url = set()

    def parse(self, response):
        article = response.xpath('//div[@id=\"main\"]/div[@class=\"post\"]')
        for element in article:
            # source url
            source_url = ''.join(element.xpath('./h2/a/@href').extract()).strip()
            # article title
            title = ''.join(element.xpath('./h2/a/text()').extract()).strip()

            meta = {
                'title': title,
                'source_url': source_url
            }
            if not self.check_existance(sourceCrawler='usda_blogs',
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
        # turning pages:
        if '>' in ''.join(response.xpath('//div[@id=\"wp_page_numbers\"]/ul/li/a/text()').extract()[-1]).strip():
            next_page = ''.join(response.xpath('//div[@id=\"wp_page_numbers\"]/ul/li/a/@href').extract()[-1]).strip()
            yield scrapy.Request(
                next_page,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_article_content(self, response):
        # get item
        item = self.get_new_item(response)

        # source url
        source_url = response.meta['source_url']
        item['source_url'] = source_url

        # html path
        html = response.body
        item["html"] = html
        item['htmls_path'] = {source_url: html}

        # content
        article = response.xpath(
            './/div[@class=\"entry\"]'
        )
        if article:
            content_document = fromstring(article.extract()[0].strip())
        if not article:
            return

        # caption
        image_urls = []
        caption_images = {}
        # images = response.xpath('//div[@class=\"wp-caption aligncenter\"]')
        images = content_document.xpath('//div[@class=\"wp-caption aligncenter\"]')
        if images:
            for image in images:
                # desc
                description = image.xpath('./p//text()')
                if description:
                    desc = description[0]
                else:
                    desc = None

                # url
                partial_url = image.xpath('.//img/@src')
                if partial_url:
                    caption_url = urlparse.urljoin(
                        response.url, partial_url[0]
                    )
                else:
                    caption_url = None

                    # alt/title
                if image.xpath(".//@alt"):
                        image_alt = image.xpath(".//@alt")[0]
                elif image.xpath(".//@title"):
                    image_alt = image.xpath(".//@title")[0]
                else:
                    image_alt = None
                if caption_url:
                    caption_images[caption_url] = (desc, image_alt)
                    image_urls.append(caption_url)
                    keep_img = fromstring('<img src= "%s"/>' % caption_url)
                    image.addnext(keep_img)
                    image.getparent().remove(image)
            item['image_urls'] = image_urls
            item['json']['caption_images'] = caption_images
        else:
            pass

        # author
        # authors = {}
        # author_name = ''.join(response.xpath('//div[@class=\"authormetadata\"]/a/text()').extract()).strip()
        # author_url = ''.join(response.xpath('//div[@class=\"authormetadata\"]/a/@href').extract()).strip()
        # if author_name:
        #     authors['name'] = author_name
        # if author_url:
        #     authors['url'] = author_url
        item['json']['author'] = ''.join(response.xpath('//div[@class=\"authormetadata\"]/a/text()').extract()).strip()

        # title
        if len(response.xpath("//h2/a/@title")) > 0:
            title = response.xpath("//h2/a/@title").extract()[0]
            item['json']['title'] = title
        else:
            title = response.meta['title']
            if title:
                item['json']['title'] = title

        # date
        partial_date = ''.join(response.xpath('//div[@class=\"authormetadata\"]/text()').extract()).strip()
        date = partial_date.split(' by , ')[-1]
        if date:
            item['json']['date'] = date

        # delete image
        if len(content_document.xpath('.//div[@class=\"wp-caption aligncenter\"]')) > 0:
            del_image = content_document.xpath('.//div[@class=\"wp-caption aligncenter\"]')[0]
            del_image.getparent().remove(del_image)

        # delete related content
        if len(content_document.xpath('.//div[@class=\"SPOSTARBUST-Related-Posts\"]')) > 0:
            del_rela_cont = content_document.xpath(
                './/div[@class=\"SPOSTARBUST-Related-Posts\"]'
            )[0]
            del_rela_cont.getparent().remove(del_rela_cont)

        # delete social media info
        # fb
        if len(content_document.xpath('.//span[@class="st_facebook_buttons"]')) > 0:
            del_fb = content_document.xpath(
                './/span[@class="st_facebook_buttons"]'
            )[0]
            del_fb.getparent().remove(del_fb)
        # twitter
        if len(content_document.xpath('.//span[@class="st_twitter_buttons"]')) > 0:
            del_twitter = content_document.xpath(
                './/span[@class="st_twitter_buttons"]'
            )[0]
            del_twitter.getparent().remove(del_twitter)
        # email
        if len(content_document.xpath('.//span[@class="st_email_buttons"]')) > 0:
            del_email = content_document.xpath(
                './/span[@class="st_email_buttons"]'
            )[0]
            del_email.getparent().remove(del_email)
        # pinterest
        if len(content_document.xpath('.//span[@class="st_pinterest_buttons"]')) > 0:
            del_pinterest = content_document.xpath(
                './/span[@class="st_pinterest_buttons"]'
            )[0]
            del_pinterest.getparent().remove(del_pinterest)

        # image replacement

        captions = content_document.xpath('.//div[@class=\"wp-caption aligncenter\"]')
        if captions:
            for caption in captions:

                keep_img = caption.xpath(
                    './/img'
                )[0]
                caption.addnext(keep_img)
                caption.getparent().remove(caption)

        item['json']["content"] = tostring(content_document, encoding="UTF-8")

        yield item
