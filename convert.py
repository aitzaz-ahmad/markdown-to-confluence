import mistune
import os
import textwrap
import yaml

from urllib.parse import urlparse
from enum import IntEnum

from pagelayouts import LeftSidebarPage, AbstractConfluencePage

YAML_BOUNDARY = '---'


class InvalidArgumentException(Exception):
    def __init__(self, arg_name, value, expectation):
        self.message = '''{arg_name} has an invalid value/type of {val}.
        Expectation: {expects}.'''.format(arg_name=arg_name,
                                          val=value,
                                          expects=expectation)

class Link(IntEnum):
        UNKNOWN = 0
        HEADING = 1
        ATTACHMENT = 2
        MD_PAGE_REFERENCE = 3

def parse(post_path):
    """Parses the metadata and content from the provided post.

    Arguments:
        post_path {str} -- The absolute path to the Markdown post
    """
    raw_yaml = ''
    markdown = ''
    in_yaml = True

    with open(post_path, mode='r', encoding='utf8') as post:
        for line in post.readlines():
            # Check if this is the ending tag
            if line.strip() == YAML_BOUNDARY:
                if in_yaml and raw_yaml:
                    in_yaml = False
                    continue
            if in_yaml:
                raw_yaml += line
            else:
                markdown += line

    front_matter = yaml.load(raw_yaml, Loader=yaml.SafeLoader)
    markdown = markdown.strip()
    return front_matter, markdown

def convert_info_macros(html):
    """Converts html for info, tip, note or warning macros

       Arguments:
            html {str} -- html content to scan

       Return:
            {str} -- modified html with Confluence macros for alerts
    """

    info_tag = '<p><ac:structured-macro ac:name="info"><ac:rich-text-body><p>'
    tip_tag = info_tag.replace('info', 'tip')
    note_tag = info_tag.replace('info', 'note')
    warning_tag = info_tag.replace('info', 'warning')
    close_tag = '</p></ac:rich-text-body></ac:structured-macro></p>'

    ## todo: the current implementation for handling block alerts is ugly af!
    ##       find a better solution. - Aitzaz [20.05.2022]
    # convert custom block alert macros into Confluence supported format
    html = html.replace('<p>~:</p>', info_tag).replace('<p>:~</p>', close_tag)
    html = html.replace('<p>~%</p>', tip_tag).replace('<p>%~</p>', close_tag)
    html = html.replace('<p>~?</p>', note_tag).replace('<p>?~</p>', close_tag)
    html = html.replace('<p>~!</p>', warning_tag).replace('<p>!~</p>', close_tag)

    # convert custom inline alert macros into Confluence supported format
    html = html.replace('<p>~:', info_tag).replace(':~</p>', close_tag)
    html = html.replace('<p>~%', tip_tag).replace('%~</p>', close_tag)
    html = html.replace('<p>~?', note_tag).replace('?~</p>', close_tag)
    html = html.replace('<p>~!', warning_tag).replace('!~</p>', close_tag)

    # convert custom alert macros (nested in tables) into Confluence supported format
    html = html.replace('~:', info_tag).replace(':~', close_tag)
    html = html.replace('~%', tip_tag).replace('%~', close_tag)
    html = html.replace('~?', note_tag).replace('?~', close_tag)
    html = html.replace('~!', warning_tag).replace('!~', close_tag)

    return html


def convtoconf(markdown, get_title_callback, front_matter={}):
    if front_matter is None:
        front_matter = {}

    page_layout = LeftSidebarPage('20%', '900px')
    renderer = ConfluenceRenderer(page_layout=page_layout,
                                  get_title_func=get_title_callback)
    content_html = mistune.markdown(markdown, renderer=renderer)
    content_html = convert_info_macros(content_html)
    author_keys = front_matter.get('author_keys', [])
    page_html = renderer.layout(content_html, authors=author_keys)

    return page_html, renderer.attachments


class ConfluenceRenderer(mistune.Renderer):
    def __init__(self, page_layout, get_title_func):

        if not page_layout or not isinstance(page_layout, AbstractConfluencePage):
            raise InvalidArgumentException('page_layout',
                                           page_layout,
                                           type(AbstractConfluencePage).__name__)
        self.has_toc = False
        self.attachments = []
        self.page_layout = page_layout

        if callable(get_title_func):
            self.get_page_title = get_title_func
        else:
            self.get_page_title = None

        super().__init__()

    def layout(self, content, authors=[]):
        """Renders the final layout of the content.

        Arguments:
            content {str} -- The HTML of the content
            authors {list} -- The list of authors
        """
        if authors is None:
            authors = []

        return self.page_layout.render(content, authors, self.has_toc)


    def header(self, text, level, raw=None):
        """Processes a Markdown header.

        In our case, this just tells us that we need to render a TOC. We don't
        actually do any special rendering for headers.
        """
        self.has_toc = True
        return super().header(text, level, raw)

    def block_code(self, code, lang):
        return textwrap.dedent('''\
            <ac:structured-macro ac:name="code" ac:schema-version="1">
                <ac:parameter ac:name="language">{l}</ac:parameter>
                <ac:plain-text-body><![CDATA[{c}]]></ac:plain-text-body>
            </ac:structured-macro>
        ''').format(c=code, l=lang or 'text')

    def linebreak(self):
        """Renders line breaks into XHTML expected by Confluence."""
        return '<br />'

    def hrule(self):
        """Renders horizontal ruler into XHTML expected by Confluence."""
        return '<hr />'

    def image(self, src, title, alt_text):
        """Renders an image into XHTML expected by Confluence.

        Arguments:
            src {str} -- The path to the image
            title {str} -- The title attribute for the image
            alt_text {str} -- The alt text for the image

        Returns:
            str -- The constructed XHTML tag
        """
        # Check if the image is externally hosted, or hosted as a static
        # file within the repo
        is_external = bool(urlparse(src).netloc)
        tag_template = '<ac:image ac:align="center">{image_tag} <div style="text-align: center;"><em>{caption}</em></div></ac:image>'
        image_tag = '<ri:url ri:value="{}" />'.format(src)
        if not is_external:
            image_tag = '<ri:attachment ri:filename="{}" />'.format(
                os.path.basename(src))

            attachment = src.lstrip('/')
            if attachment.startswith('images'): #todo: replace 'images' with 'assets'
                attachment = attachment[len('images'):]

            self.attachments.append(attachment)

        return tag_template.format(image_tag=image_tag, caption=alt_text.strip('*_'))

    def link(self, src, title, text):
        """Renders a hyperlink into XHTML expected by Confluence.

        Arguments:
            src {str} -- The url to the target
            title {str} -- The title attribute for the link
            text {str} -- The text content for the link

        Returns:
            str -- The constructed XHTML tag
        """

        # Check if the url is an externally hosted webpage, or a
        # cross-referenceto to another documentation (.md) file
        is_external = bool(urlparse(src).netloc)
        if is_external:
            return super().link(src, title, text)

        #custom handling for internal links
        link_type = self.resolve_link(src)

        if link_type is Link.ATTACHMENT:
            self.attachments.append(src)

            # link to a file attachment
            return textwrap.dedent('''\
                    <ac:link>
                        <ri:attachment ri:filename="{file}" />
                        <ac:plain-text-link-body>
                            <![CDATA[{text}]]>
                        </ac:plain-text-link-body>
                    </ac:link>
                ''').format(file=os.path.basename(src), text=text)

        elif link_type is Link.MD_PAGE_REFERENCE:
            if callable(self.get_page_title):
                title = mistune.escape(self.get_page_title(src), quote=True)

            return textwrap.dedent('''\
                    <ac:link>
                        <ri:page ri:content-title="{title}" />
                        <ac:plain-text-link-body>
                            <![CDATA[{text}]]>
                        </ac:plain-text-link-body>
                    </ac:link>
                ''').format(title=title or '', text=text)

        elif link_type is Link.HEADING:
            return textwrap.dedent('''\
                <ac:link ac:anchor="{heading}">
                    <ac:plain-text-link-body>
                        <![CDATA[{text}]]>
                    </ac:plain-text-link-body>
                </ac:link>
            ''').format(heading=title or '', text=text)

        else: # corresponds to Link.UNKNOWN
            return super().link(src, title, text)

    def resolve_link(self, link):
        """Interprets and returns the type of the link.

            Arguments:
                link {str} -- The link to the target

            Returns:
                Link { Enum } -- HEADING for a markdown section heading,
                                 MD_PAGE_REFERENCE for a cross-referenced markdown doc,
                                 ATTACHMENT for file inside the assets directory,
                                 UKNOWN in all other cases
        """

        if link.startswith('#'):
            return Link.HEADING

        if os.path.dirname(link) == 'images': #todo: replace with 'assets'
            return Link.ATTACHMENT

        _, ext = os.path.splitext(link)
        if ext == '.md':
            return Link.MD_PAGE_REFERENCE
        else:
            return Link.UNKNOWN
