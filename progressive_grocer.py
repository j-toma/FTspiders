# -*- coding: utf-8 -*-
import scrapy
import urlparse
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring


class ProgressiveGrocer(Spider):
    name = 'progressive_grocer'
    crawl_type = "news"
    version = 2
    allowed_domains = ['http://www.progressivegrocer.com/']
    source_crawler = "progressive_grocer"
    start_urls = [
        "http://www.progressivegrocer.com/research-data",
        "http://www.progressivegrocer.com/departments/produce-floral",
    ]
    #     "http://www.progressivegrocer.com/industry-news-trends",
    #     "http://www.progressivegrocer.com/viewpoints-blogs",
    #     "http://www.progressivegrocer.com/awards-events",
    # ]
    all_url = set()

    def parse(self, response):
        url = response.url
        for li in response.xpath(
            "//ul[contains(@class, 'featured-category-list')]/li"
        ):
            source_url = urlparse.urljoin(
                url,
                li.xpath("./header/h3/a/@href").extract()[0].strip()
            )
            title = ''.join(li.xpath("./header/h3/a/text()").extract()).strip()
            excerpt = ''.join(li.xpath("./text()").extract()).strip()
            thumb_url = urlparse.urljoin(
                url,
                li.xpath(
                    "./div[contains(@class, 'img-wrapper')]/a/img/@src"
                ).extract()[0].strip()
            )
            meta = {
                'source_url': unicode(source_url),
                'title': title,
                'excerpt': excerpt
            }
            if thumb_url and 'article-medium.jpg' not in thumb_url:
                meta["thumb_urls"] = [thumb_url]
            if not self.check_existance(sourceCrawler=self.source_crawler,
                                        sourceURL=source_url,
                                        items_scraped=self.items_scraped)\
                    and source_url not in self.all_url:
                self.all_url.add(source_url)
                yield scrapy.Request(
                    source_url,
                    # 'http://www.progressivegrocer.com/research-data/research-analysis/tabulating-retail-experience',
                    callback=self.parse_item,
                    dont_filter=True,
                    meta=meta
                )

        next_page_uri = response.xpath(
            "//li[contains(@class, 'pager-next')]/a/@href"
        )
        if next_page_uri:
            next_page_url = urlparse.urljoin(
                url,
                next_page_uri.extract()[0].strip()
            )
            yield scrapy.Request(
                next_page_url,
                callback=self.parse,
                dont_filter=True,
            )

    def parse_item(self, response):
        # shitty pages
        if 'http://www.progressivegrocer.com/research-data/shopper-behavior' == response.url:
            return
            
        # THIS SECTION IS FOR MULTI PAGE ITEMS
        # list of urls
        if 'url_list' not in response.meta:
            url_list = [response.url]
        else:
            url_list = response.meta['url_list']
            url_list.append(response.url)

        # list of htmls
        html = response.body
        if 'html_list' not in response.meta:
            html_list = [html]
        else:
            html_list = response.meta['html_list']
            html_list.append(html)

        # get content from previous pages
        if len(response.xpath("//div[@class='text-block']")) > 0:
            new_content = response.xpath("//div[@class='text-block']")
            if 'content' in response.meta:
                content = response.meta['content'] + new_content.extract()[0]
            else:
                content = new_content.extract()[0]
        # else:
        #     return

        # next pages 
        if len(response.xpath("//li[@class='pager-next']")) > 0:
            next_page_part = response.xpath("//li[@class='pager-next']//@href").extract()[0]
            next_page = urlparse.urljoin(response.url,next_page_part)
            meta = {'content': content,
                    'url_list': url_list,
                    'html_list': html_list}
            # print "THIS IS A MULTI PAGE BITCH"
            yield scrapy.Request(
                next_page,
                callback=self.parse_item,
                dont_filter=True,
                meta=meta)
        else:

            url = response.url
            item = self.get_new_item(response)
            json = item['json']
            item['source_url'] = url_list[0]
            item['html'] = html_list[0]
            item['htmls_path'] = dict(zip(url_list, html_list))
            json['excerpt'] = response.meta['excerpt'] if 'excerpt' in response.meta else None

            # detail title
            if len(response.xpath("//h1/text()")) > 0:
                title = response.xpath("//h1/text()").extract()[0]
                json['title'] = title
            else:
                json['title'] = response.meta['title']

            date = response.xpath("//article[contains(@id, 'main-article')]/header//time/@datetime")
            if date:
                json['date'] = date.extract()[0].strip()
            category = response.xpath("//div[@class=\"inline odd last\"]/a/span/text()")
            if category:
                json['category'] = category.extract()[0].strip()
            parent_category = response.xpath("//div[@class=\"inline even\"]/a/span/text()")
            if parent_category:
                json['parent_category'] = parent_category.extract()[0].strip()
            image_urls = []
            caption_images = {}
            figures = response.xpath("//article[contains(@id, 'main-article')]//figure[contains(@class, 'article-img')]")
            for figure in figures:
                figcaption_tag = figure.xpath(".//figcaption")
                if figcaption_tag:
                    desc = figcaption_tag.extract()[0].strip()
                else:
                    desc = None
                img_tag = figure.xpath(".//img")
                if not img_tag:
                    continue
                src = urlparse.urljoin(
                    url,
                    img_tag.xpath(".//@src").extract()[0].strip()
                )
                if img_tag.xpath(".//@alt"):
                    alt = img_tag.xpath(".//@alt").extract()[0].strip()
                elif img_tag.xpath(".//@title"):
                    alt = img_tag.xpath(".//@title").extract()[0].strip()
                else:
                    alt = None
                if alt == u'' or alt == None: 
                    alt = response.xpath("//h1/text()").extract()[0]
                image_urls.append(src)
                caption_images[src] = (desc, alt)

            if "thumb_urls" in response.meta:
                item["thumb_urls"] = response.meta["thumb_urls"]

            if content is not None:
                content_document = fromstring(content)
            else:
                content_document = None

            # add figures into lxml 
            for url in caption_images.keys():
                add_img = fromstring("<img src='%s'/>" % url)
                content_document.insert(0,add_img)

            # get article imgs
            if len(content_document.xpath(".//img")) > 0:
                imgs = content_document.xpath("//div[@class='text-block']//img")
                for img in imgs:
                    print "THIS IS A BIG KAHUNA BOONA BOMB OMB SLOMB DANK", response.url
                    url = urlparse.urljoin(response.url,img.xpath(".//@src")[0])
                    if len(img.xpath(".//@alt")) > 0:
                        cap = img.xpath(".//@alt")[0]
                    elif len(img.xpath(".//@title")) > 0:
                        cap = img.xpath(".//@title")[0]
                    else:
                        cap = None
                    kp_img = fromstring("<img src='%s'/>" % url)
                    img.addnext(kp_img)
                    img.getparent().remove(img)
                    caption_images[url] = (cap, response.xpath("//h1/text()").extract()[0])
            item["image_urls"] = caption_images.keys()
            json["caption_images"] = caption_images

            if len(content_document.xpath("//div[@class='smart-paging-pager']")) > 0:
                pagers = content_document.xpath(("//div[@class='smart-paging-pager']"))
                for pager in pagers:    
                    pager.getparent().remove(pager)

            # flag = False
            if len(content_document.xpath("//div[@class='special-box whitepaper-form']")) > 0:
                whitepapers = content_document.xpath("//div[@class='special-box whitepaper-form']")
                for whitepaper in whitepapers:
                    # flag = True
                    whitepaper.getparent().remove(whitepaper)
            # if len(content_document.xpath('./header/h1')) > 0:
            #     del_title = content_document.xpath('./header/h1')[0]
            #     del_title.getparent().remove(del_title)
            # if len(content_document.xpath('./header/h2')) > 0:
            #     del_sub_title = content_document.xpath('./header/h2')[0]
            #     del_sub_title.getparent().remove(del_sub_title)
            # if len(content_document.xpath('./header/address')) > 0:
            #     del_add = content_document.xpath('./header/address')[0]
            #     del_add.getparent().remove(del_add)
            # if len(content_document.xpath('./div[@class=\"inline-vcard\"]')) > 0:
            #     del_author_name = content_document.xpath('./div[@class=\"inline-vcard\"]')[0]
            #     del_author_name.getparent().remove(del_author_name)
            # if len(content_document.xpath('./ul[@class=\"authors\"]')) > 0:
            #     del_author_info = content_document.xpath('./ul[@class=\"authors\"]')[0]
            #     del_author_info.getparent().remove(del_author_info)

            # add the image as next node and then delete original
            figures_doc = content_document.xpath(".//figure[contains(@class, 'article-img')]")
            for figure_doc in figures_doc:
                if not figure_doc.xpath(".//img"):
                    continue
                keep_img = figure_doc.xpath(".//img")[0]
                figure_doc.addnext(keep_img)
                figure_doc.getparent().remove(figure_doc)

            json["content"] = tostring(content_document, encoding="UTF-8")

            # if flag:
            yield item
