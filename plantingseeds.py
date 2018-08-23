# -*- coding: utf-8 -*-
import scrapy
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class PlantingSeeds(Spider):
    download_delay = 3.6
    name = 'plantingseeds'
    source_crawler = 'plantingseedsblog'
    crawl_type = 'news'
    item_parser = "parse_post"
    version = 0
    allowed_domains = ['http://plantingseedsblog.cdfa.ca.gov/']
    start_urls = ['http://plantingseedsblog.cdfa.ca.gov/wordpress/']
    all_urls = set()

    def parse(self, response):
        month_urls = response.xpath(
            "//li[@id=\"archives-2\"]/ul/li/a/@href").extract()
        for month in month_urls:
            yield scrapy.Request(
                month,
                callback=self.parse_month,
                dont_filter=True)

    def parse_month(self, response):

        meta = {}
        posts = response.xpath("//div[contains(@id, 'post')]")
        for post in posts:
            title = post.xpath(".//h2/a")
            if title:
                post_url = ''.join(title.xpath(".//@href").extract()).strip()
                title = self.get_text(title.extract()[0])
            date = post.xpath(".//div[@class=\"entry-meta\"]")
            if date:
                date = ''.join(date.xpath(
                    ".//span[@class=\"entry-date\"]/text()").extract()).strip()
            meta = {'title': title, 'date': date, 'source_url': post_url}
            if not self.check_existance(sourceCrawler='plantingseedsblog',
                                        sourceURL=post_url,
                                        items_scraped=self.items_scraped) and\
                    post_url not in self.all_urls:
                self.all_urls.add(post_url)
                yield scrapy.Request(
                    post_url,
                    callback=self.parse_post,
                    dont_filter=True,
                    meta=meta)

        next_page = response.xpath("//div[@class=\"nav-previous\"]")
        if next_page:
            next_urls = next_page.xpath(".//a/@href").extract()
            if next_urls:
                next_url = next_urls[0]
                yield scrapy.Request(
                    next_url,
                    callback=self.parse_month,
                    dont_filter=True)

    def parse_post(self, response):
        item = self.get_new_item(response)
        item['htmls_path'] = {response.url: response.body}
        item['html'] = response.body
        item['source_url'] = response.meta['source_url']
        item['json']['date'] = response.meta['date']
        item['thumb_urls'] = []

        content = response.xpath("//div[@class=\"entry-content\"]")

        bulk_content = fromstring(content.extract()[0].strip())
        children = bulk_content.getchildren()

        # title
        if len(content.xpath("//h1[@class='entry-title']/text()")) > 0:
            title = content.xpath("//h1[@class='entry-title']/text()").extract()[0]
            item['json']['title'] = title
        else:
            item['json']['title'] = response.meta['title']

        # del_share
        del_share = bulk_content.xpath(
            "//div[contains(@class,\"sharedaddy\")]")
        if len(del_share) > 0:
            del_share = bulk_content.xpath(
                "//div[contains(@class,\"sharedaddy\")]")[0]
            del_share.getparent().remove(del_share)

        image_flag = True
        # gallery
        for child in children:
            if child.xpath(".//dl"):
                image_flag = False
                caption_images = {}
                gal_itms = child.xpath(".//dl")
                for gal_itm in gal_itms:
                    url = gal_itm.xpath(".//@src")
                    if url:
                        url = url[0]
                        cap = gal_itm.xpath(
                            ".//dd[contains(@class,'caption')]/text()")
                        if cap:
                            cap = self.get_text(cap[0])
                        else:
                            cap = None
                        alt_cap = None
                        caption_images[url] = (cap, alt_cap)

                child.getparent().remove(child)
                for img_url in caption_images.keys():
                    tag = "<img src= '%s' />" % img_url
                    bulk_content.insert(0, fromstring(tag + '/n'))
                item['json']['caption_images'] = caption_images
                item['image_urls'] = [key.encode("UTF-8") for key in caption_images.keys()]

        # images
        img_blocks = []
        for child in children:
            if child.xpath(".//img") != []:
                img_blocks.append(child)
            # meanwhile get author and take it out of text -- maybe there is a problem with h6 here
            if child.xpath(".//strong/text()|.//h6/text()") != []:
                if child.xpath(".//strong/text()")[0][:2] == 'By':
                    author = child.xpath(
                        ".//strong/text()")[0].lstrip('By ')
                    if child not in img_blocks:
                        child.getparent().remove(child)
                    break
                else:
                    author = None
            else:
                author = None

        item['json']['author'] = author if author else ''.join(response.xpath(
            "//span[@class=\"author vcard\"]/a/text()"
        ).extract()).strip()

        # back to images
        if image_flag:
            caption_images = {}
            for img_block in img_blocks:

                # get img url
                img_url = img_block.xpath(".//@src")
                if type(img_url) == list:
                    img_url = img_url[0]
                # skip gifs
                if img_url[-3:] == 'gif':
                    break

                # get caption tuple
                # real caption
                if img_block.xpath(
                        ".//p[contains(@class,'wp-caption-text')]/text()"):
                    cap = img_block.xpath(
                        ".//p[contains(@class,'wp-caption-text')]/text()")
                    if type(cap) == list:
                        cap = cap[0]
                    cap = self.get_text(cap)
                else:
                    cap = None
                # alternate caption
                if img_block.xpath(".//@alt"):
                    alt_cap = img_block.xpath(".//@alt")
                elif img_block.xpath(".//@title"):
                    alt_cap = img_block.xpath(".//@title")
                else:
                    alt_cap = None
                if type(alt_cap) == list:
                    alt_cap = alt_cap[0]
                if alt_cap == 'caption' or 'Caption':
                    alt_cap = None

                # put in captioned images dictionary
                caption_images[img_url] = (cap, alt_cap)

                # for old articles get text from img_block
                if img_block.xpath(".//text()") != []:
                    text = img_block.xpath(".//text()")[0]
                else:
                    text = None
                if text:
                    full_text = fromstring("<p>%s\n</p>" % text)
                    img_block.addnext(full_text)

                # del block and replace with plain tag ( and text)
                keep_img = "<img src='%s'/>" % img_url
                img_block.addnext(fromstring(keep_img))
                img_block.getparent().remove(img_block)

            item['json']['caption_images'] = caption_images
            item['image_urls'] = caption_images.keys()

        del_30 = bulk_content.xpath(".//p[text()='-30-']")
        if len(del_30) > 0:
            del_30 = del_30[0]
            del_30.getparent().remove(del_30)

        # for el in bulk_content:
        #     dont_clean_flag = True
        #     children = el.getchildren()
        #     for child in children:
        #         if child.tag == 'img':
        #             dont_clean_flag = False
        #     if dont_clean_flag:
        #         tag = el.tag
        #         clean_text = self.get_text(tostring(el, encoding="UTF-8"))
        #         keep_tag = fromstring("<%s> %s <%s/>" % (tag, clean_text, tag))
        #         el.addnext(keep_tag)
        #         bulk_content.remove(el)

        item["json"]["content"] = tostring(bulk_content, encoding="UTF-8")

        yield item
