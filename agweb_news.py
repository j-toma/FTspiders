# -*- coding: utf-8 -*-
import scrapy
import urlparse
import lxml
from data_fetchers.spider import Spider
from lxml.html import fromstring, tostring
from lxml.html.clean import Cleaner


class AgWebNews(Spider):

    name = 'agwebnews'
    source_crawler = "agweb"
    crawl_type = "news"
    version = 3
    allowed_domains = ['www.agweb.com']
    start_urls = [
        "http://www.agweb.com/listing/?k=&b=1&t=19%2C18&pt=Latest%20News&pg=1"
    ]
    all_url = set()

    def parse(self, response):

        for element in response.xpath('//ul[@class=\"itemList\"]/li'):

            # title
            title_1 = element.xpath('./div/h2[@class=\"title\"]/a/text()')
            if title_1:
                title = ''.join(title_1.extract()).strip()

            # time
            time_1 = element.xpath('./div/span/text()')
            if time_1:
                time = ''.join(time_1.extract()).strip()
            if not time_1:
                time = None

            # thumbnail
            thumb_1 = element.xpath('./figure/a/img/@src')
            thumb_urls = []
            if thumb_1:
                thumb_2 = ''.join(thumb_1.extract()).strip()
                thumb = urlparse.urljoin(response.url, thumb_2.strip())
                thumb_urls.append(thumb)

            # excerpt
            excerpt_1 = element.xpath('./div/p/text()')
            if excerpt_1:
                excerpt = ''.join(excerpt_1.extract()).strip()
            # source url
            url = ''.join(element.xpath(
                './div[@class=\"content\"]/h2[@class=\"title\"]/a/@href'
            ).extract()).strip()
            if url:
                source_url = urlparse.urljoin(response.url, url)

                meta = {
                    'title': title,
                    'date': time,
                    'excerpt': excerpt,
                    'thumb_urls': thumb_urls,
                    'source_url': source_url
                }
                if not self.check_existance(sourceCrawler='agweb',
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
            '//div[@class=\"genericPager\"]//li//text()'
        ).extract()).strip()
        if "next" in have_next:
            next_page = response.xpath('//div[@class=\"genericPager\"]//li')[-1]

            next_url = ''.join(next_page.xpath('.//@href').extract()).strip()
            if next_url:
                next_page_url = urlparse.urljoin(response.url, next_url)

                yield scrapy.Request(
                    next_page_url,
                    callback=self.parse,
                    dont_filter=True,
                )

    # def parse_item(self, response):
    #     meta = response.meta
    #     source_url = meta['source_url']

    #     if "/blog" in source_url:
    #         yield scrapy.Request(
    #             source_url,
    #             callback=self.parse_blog_content,
    #             dont_filter=True,
    #             meta=copy.deepcopy(meta)
    #         )
    #     else:
    #         yield scrapy.Request(
    #             source_url,
    #             # 'http://www.agweb.com/article/ohio-farmers-see-quality-issues-in-wheat--NAA-betsy-jibben/',
    #             callback=self.parse_article_content,
    #             dont_filter=True,
    #             meta=meta
    #         )

    def parse_article_content(self, response):

        # basics 
        item = self.get_new_item(response)
        if 'reparse_from' in response.meta:
            item['json']['reparse_from'] = response.meta['reparse_from']
        if len(response.xpath("//h1[@class='title']/text()")) > 0:
            title = response.xpath("//h1[@class='title']/text()").extract()[0]
            item['json']['title'] = title
        else:
            title = response.meta['title']
        item['json']['date'] = response.meta['date'] if "date" in response.meta else response.meta['time']
        if 'excerpt' in response.meta:
            item['json']['excerpt'] = response.meta['excerpt']
        if 'thumb_urls' in response.meta:
            item['thumb_urls'] = response.meta['thumb_urls']
        if 'source_url' in response.meta:
            item['source_url'] = response.meta['source_url']
        html = response.body
        item['html'] = html
        source_url = response.meta['source_url']
        item['source_url'] = source_url
        item["htmls_path"] = {source_url: html}

        # debug_flag = False

        # if 'blog' in source_url:
        #     print "THIS IS A BLOG POST -- ))))))))))))))))))))))"
        #     print response.url
        #     print "THIS IS A BLOG POST -- ))))))))))))))))))))))"

        # this cleaner caused problems with the rest of the code -- but it did remove the twitter posts
        # cleaner = Cleaner()
        # cleaner.kill_tags = ['blockquote']
        # cleaned = cleaner.clean_html(lxml.html.parse(response.url))

        # get lxml 
        if len(response.xpath(".//div[@class='articleContent articleTruncate']")):
            document = response.xpath(".//div[@class='articleContent articleTruncate']")
            lxml_doc = fromstring(document.extract()[0])
            # lxml_doc = cleaned.xpath(".//div[@class='articleContent articleTruncate']")[0]
        else:
            return

        # bulk remove twitter items 
        # this may remove article that dont have twitter contents

        if "twitter" in tostring(lxml_doc):
            return

        # IMAGES
        capd_imgs = {}
        # in article images 
        if len(lxml_doc.xpath(".//img")) > 0:
            for img in lxml_doc.xpath(".//img"):
                if len(img.xpath("./@src")) > 0:
                    url = urlparse.urljoin(response.url,img.xpath("./@src")[0])
                    # removes power hour ads 
                    if (('Power' and 'Hour') or ('hour' and 'power')) in url:
                        img_str = tostring(img)
                        img_node_end = img_str.find('>')
                        img_ad = img_str[:img_node_end+1]
                        lxml_doc = fromstring(tostring(lxml_doc).replace(img_ad,""))
                        # debug_flag = True
                        continue
                    if img.xpath('.//@alt'):
                        cap = img.xpath('.//@alt')[0]
                    else:
                        cap = None
                    capd_imgs[url] = (cap, title)
                    kp_img = fromstring("<img src='%s'/>" % url)
                    img.addnext(kp_img)
                    img.getparent().remove(img)

        # figures
        figures = response.xpath("//figure")
        for figure in figures:
            # url
            if figure.xpath('.//img/@src'):
                p_url = figure.xpath('.//img/@src').extract()[0]
                url = urlparse.urljoin(response.url, p_url)
                # cap
                if len(figure.xpath(".//div[@class='news-caption']/text()")) > 0:
                    cap = figure.xpath(".//div[@class='news-caption']/text()").extract()[0]
                    # debug_flag = True
                else:
                    cap = None
                # alt
                if figure.xpath('.//img/@alt'):
                    alt = figure.xpath('.//img/@alt').extract()[0]
                else:
                    alt = title
                capd_imgs[url] = (cap, alt)
                kp_img = fromstring("<img src='%s'/>" % url)
                lxml_doc.insert(0,kp_img)

        item['image_urls'] = capd_imgs.keys()
        item['json']['caption_images'] = capd_imgs

        # this code gets removes the introductory paragraphs from videos/audio files
        # update sept 3 -- this code is faulty, deletes real content 
        # prev = None
        # for child in lxml_doc.getchildren():
        #     # bar and javascript
        #     if child.tag == 'hr' or child.tag == 'script':
        #         lxml_doc.remove(child)
        #         if prev.xpath("//*[text()[contains(.,'Listen')]]") or\
        #                 prev.xpath("//*[text()[contains(.,'watch')]]") or\
        #                 prev.xpath("//*[text()[contains(.,'video')]]") or\
        #                 prev.xpath("//*[text()[contains(.,'listen')]]") or\
        #                 prev.xpath("//*[text()[contains(.,'hear')]]") or\
        #                 prev.xpath("//*[text()[contains(.,'highlights')]]"):
        #             lxml_doc.remove(prev)
        #             debug_flag = True
        #     # market stories
        #     if child.xpath("./u[text()='Market Stories']"):
        #         lxml_doc.remove(child)
        #         # debug_flag = True
        #     prev = child

        # minor cleaning of strong, script, power hour links, author info: 
        for d in lxml_doc.iterdescendants():
            # if d.tag == 'script':
            #     d.getparent().remove(d)
            # if d.tag == 'strong':
            #     if d.xpath("//*[text()[contains(.,'hear') or contains(.,'listen') or contains(.,'Listen') or contains(.,'watch') or contains(.,'Watch')]]"):
            #         d.getparent().remove(d)
            #         continue
            if d.xpath("./span[@class='LimelightEmbeddedPlayer']"):
                # consider removing preceding <em>
                # also can consider inserting a message like "see original source"
                # debug_flag = True
                orig_source = "<a href='%s'>original source</a>" % source_url
                usr_msg = fromstring("The " + orig_source + " features a media item here.")
                d.addnext(usr_msg)
                d.getparent().remove(d)
            if d.tag == 'p':
                if d.xpath(".//*[contains(.,'Power Hour') and contains(.,'Click here')]"):
                    d.getparent().remove(d)

        # delete related content
        if len(lxml_doc.xpath('.//div[@class=\"articleContent articleTruncate\"]//div[@class=\"relatedContentWrpr\"]')) > 0:
            del_rela_cont = lxml_doc.xpath(
                './/div[@class=\"articleContent articleTruncate\"]//div[@class=\"relatedContentWrpr\"]'
            )[0]
            del_rela_cont.getparent().remove(del_rela_cont)
        # delete back to news icon
        if len(lxml_doc.xpath('.//a[@href=\"/news-listing/\"]')) > 0:
            del_back_to_news = lxml_doc.xpath(
                './/a[@href=\"/news-listing/\"]'
            )[0]
            del_back_to_news.getparent().remove(del_back_to_news)

        item['json']['content'] = tostring(lxml_doc, encoding="UTF-8")

        # if debug_flag:
        #     yield item
        yield item


        # # get the content and remove unnecessary parts
        # item = self.get_new_item(response)
        # json = item["json"]
        # if "reparse_from" in response.meta:
        #     json["reparse_from"] = response.meta["reparse_from"]
        # # title
        # title = response.meta['title']
        # json['title'] = title
        # # detail title 
        # if len(response.xpath("//h1[@class='title']/text()")) > 0:
        #     title = response.xpath("//h1[@class='title']/text()").extract()[0]
        #     json['title'] = title
        # # time
        # time = response.meta['date'] if "date" in response.meta else response.meta['time']
        # json['date'] = time
        # # excerpt
        # excerpt = response.meta['excerpt']
        # json['excerpt'] = excerpt
        # # thumbnail url
        # thumb_urls = response.meta['thumb_urls']
        # item['thumb_urls'] = thumb_urls
        # # source url
        # source_url = response.meta['source_url']
        # item['source_url'] = source_url

        # if response.xpath(".//article[@class='content article newsDetail mod clearfix']"):
        #     document = response.xpath(
        #         ".//article[@class='content article newsDetail mod clearfix']")
        # # else:
        # #     return

        # htmls_path = {}
        # htmls_path[response.url] = response.body

        # capd_imgs = {}

        # # in article images
        # images = document.xpath("//div[@class='articleContent articleTruncate']//img")
        # for image in images:
        #     if len(image.xpath('.//@src')) > 0:
        #         url = image.xpath('.//@src').extract()[0]
        #         if 'Power%20Hour%20Noon%20Logo.jpg' in url or\
        #                 'Power Hour Noon Logo.jpg' in url:
        #             document = document.extract()[0].replace(image.extract(),'')
        #             document = fromstring(document)
        #             continue
        #         else:
        #             url = urlparse.urljoin(response.url, url)
        #     else:
        #         url = None
        #     if image.xpath('.//@alt'):
        #         cap = image.xpath('.//@alt')[0]
        #     else:
        #         cap = None
        #     # elif element.xpath('.//@title'):
        #     #     alt_box = element.xpath('.//@title')
        #     #     alt = ''.join(alt_box.extract()).strip()
        #     if url:
        #         capd_imgs[url] = (None, title)
        #         kp_img = "<img src='%s'/>" % url
        #         document = document.extract()[0].replace(image.extract(),kp_img)
        #         document = 

        # if type(document) == str or type(document) == unicode:
        #     content_document = fromstring(document)
        # else:
        #     content_document = fromstring(document.extract()[0])

        # # minor cleaning of strong, script, power hour links: 
        # for d in content_document.iterdescendants():
        #     if d.tag == 'strong':
        #         if d.xpath("//*[text()[contains(.,'hear') or contains(.,'listen') or contains(.,'Listen') or contains(.,'watch') or contains(.,'Watch')]]"):
        #             d.getparent().remove(d)
        #             continue
        #     if d.xpath("./span[@class='LimelightEmbeddedPlayer']"):
        #         d.getparent().remove(d)
        #         continue
        #     if d.tag == 'p':
        #         if d.xpath(".//*[contains(.,'Power Hour') and contains(.,'Click here')]"):
        #             d.getparent().remove(d)

        # # image section
        # figures = response.xpath("//figure")
        # for figure in figures:
        #     # cap
        #     if len(figure.xpath(".//div[@class='news-caption']/text()")) > 0:
        #         cap = figure.xpath(".//div[@class='news-caption']/text()")[0]
        #     else:
        #         cap = None
        #     # url
        #     if figure.xpath('.//img/@src'):
        #         p_url = figure.xpath('.//img/@src')[0]
        #         url = urlparse.urljoin(response.url, p_url)
        #     else:
        #         url = None
        #     # alt
        #     if figure.xpath('.//img/@alt'):
        #         alt = figure.xpath('.//img/@alt')[0]
        #     else:
        #         alt = title
        #     capd_imgs[url] = (cap, alt)
        #     kp_img = fromstring("<img src='%s'/>" % url)
        #     content_document.insert(kp_img)

        # item['image_urls'] = capd_imgs.keys()
        # json['caption_images'] = capd_imgs

        # # delete title
        # if len(content_document.xpath('.//h1[@class=\"title\"]')) > 0:
        #     del_title = content_document.xpath('.//h1[@class=\"title\"]')[0]
        #     del_title.getparent().remove(del_title)
        # # delete social media info
        # if len(content_document.xpath('.//div[@class=\"news-socialWrpr\"]')) > 0:
        #     del_social = content_document.xpath(
        #         './/div[@class=\"news-socialWrpr\"]'
        #     )[0]
        #     del_social.getparent().remove(del_social)
        # # delete date
        # if len(content_document.xpath('.//div[@class=\"meta clearfix\"]')) > 0:
        #     del_date = content_document.xpath(
        #         './/div[@class=\"meta clearfix\"]')[0]
        #     del_date.getparent().remove(del_date)
        # # delete related content
        # if len(content_document.xpath('.//div[@class=\"articleContent articleTruncate\"]//div[@class=\"relatedContentWrpr\"]')) > 0:
        #     del_rela_cont = content_document.xpath(
        #         './/div[@class=\"articleContent articleTruncate\"]//div[@class=\"relatedContentWrpr\"]'
        #     )[0]
        #     del_rela_cont.getparent().remove(del_rela_cont)
        # # delete back to news icon
        # if len(content_document.xpath('.//a[@href=\"/news-listing/\"]')) > 0:
        #     del_back_to_news = content_document.xpath(
        #         './/a[@href=\"/news-listing/\"]'
        #     )[0]
        #     del_back_to_news.getparent().remove(del_back_to_news)

        # # delete other
        # prev = None
        # main = content_document.xpath(
        #     "//div[@class='articleContent articleTruncate']")[0]
        # for child in main.iterchildren():
        #     # bar and javascript
        #     if child.tag == 'hr' or child.tag == 'script':
        #         main.remove(child)
        #         if prev in main.getchildren():
        #             if prev.xpath("//*[text()[contains(.,'Listen')]]") or\
        #                     prev.xpath("//*[text()[contains(.,'watch')]]") or\
        #                     prev.xpath("//*[text()[contains(.,'video')]]") or\
        #                     prev.xpath("//*[text()[contains(.,'videos')]]") or\
        #                     prev.xpath("//*[text()[contains(.,'listen')]]") or\
        #                     prev.xpath("//*[text()[contains(.,'hear')]]"):
        #                 main.remove(prev)
        #     # market stories
        #     if child.xpath("./u[text()='Market Stories']"):
        #         main.remove(child)

        # # image replacement
        # captions = content_document.xpath('./figure')
        # if captions:
        #     for caption in captions:

        #         keep_img = caption.xpath(
        #             './/img'
        #         )[0]
        #         caption.addnext(keep_img)
        #         caption.getparent().remove(caption)

        # json["content"] = tostring(content_document, encoding="UTF-8")

        # item['json'] = json

        # item['htmls_path'] = htmls_path
        # item["html"] = response.body

        # yield item

    # def parse_blog_content(self, response):
    #     print "THIS IS A BLOG", response.url
    #     # get the content and remove unnecessary parts
    #     item = self.get_new_item(response)
    #     json = item["json"]
    #     if "reparse_from" in response.meta:
    #         json["reparse_from"] = response.meta["reparse_from"]
    #     # title
    #     title = response.meta['title']
    #     json['title'] = title
    #     # time
    #     time = response.meta['date'] if "date" in response.meta else response.meta['time']
    #     json['date'] = time
    #     # excerpt
    #     excerpt = response.meta['excerpt']
    #     json['excerpt'] = excerpt
    #     # thumbnail url
    #     thumb_urls = response.meta['thumb_urls']
    #     item['thumb_urls'] = thumb_urls
    #     # source url
    #     source_url = response.meta['source_url']
    #     item['source_url'] = source_url

    #     # get the content and remove unnecessary parts
    #     for element in response.xpath('//div[@class=\"siteBody\"]/div[@class=\"container\"]//div[@id=\"CT_ContentBlock_0_pnlModule\"]'):
    #         htmls_path = {}
    #         htmls_path[response.url] = response.body
    #         image_urls = []

    #         author = {}
    #         # caption_description
    #         author_description = ''.join(element.xpath(
    #             './/div[@class=\"blogIntroWrpr\"]/div[@class=\"mrg20b\"]//text()'
    #         ).extract()).strip()
    #         # author_url
    #         partial_author_url = ''.join(element.xpath(
    #             './/div[@class=\"blogIntroWrpr\"]/img/@src'
    #         ).extract()).strip()
    #         if partial_author_url:
    #             author_url = urlparse.urljoin(
    #                 response.url, partial_author_url
    #             )
    #             author['author_url'] = author_url
    #             image_urls.append(author_url)
    #         author['description'] = author_description

    #         # content
    #         article = response.xpath(
    #             './/div[@id=\"CT_ContentBlock_0_pnlModule\"]'
    #         )
    #         content_document = fromstring(article.extract()[0].strip())

    #         # delete intro
    #         if len(content_document.xpath('.//div[@class=\"blogIntroWrpr\"]')) > 0:
    #             del_intro = content_document.xpath('.//div[@class=\"blogIntroWrpr\"]')[0]
    #             del_intro.getparent().remove(del_intro)

    #         # delete title
    #         if len(content_document.xpath('.//div[@id=\"CT_ContentBlock_0_pnlPostDetails\"]/h2')) > 0:
    #             del_title = content_document.xpath('.//div[@id=\"CT_ContentBlock_0_pnlPostDetails\"]/h2')[0]
    #             del_title.getparent().remove(del_title)

    #         # delete other stuff and icons
    #         if len(content_document.xpath('.//div[@id=\"CT_ContentBlock_0_pnlPostDetails\"]//div')) > 0:
    #             del_date = content_document.xpath(
    #                 './/div[@id=\"CT_ContentBlock_0_pnlPostDetails\"]//div')[0]
    #             del_date.getparent().remove(del_date)

    #         # image replacement

    #         captions = content_document.xpath('.//div[@class=\"blogIntroWrpr\"]')
    #         if captions:
    #             for caption in captions:

    #                 keep_img = caption.xpath(
    #                     './/img'
    #                 )[0]
    #                 caption.addnext(keep_img)
    #                 caption.getparent().remove(caption)

    #         json["content"] = tostring(content_document, encoding="UTF-8")
    #         item['json'] = json
    #         item['htmls_path'] = htmls_path
    #         item["html"] = response.body
    #         item['image_urls'] = image_urls

    #         yield item
