import textwrap
from abc import ABC, abstractmethod

class AbstractConfluencePage(ABC):
    """ The abstract base class for creating a Confluence page.

        Provides the template method to generate the final HTML of
        a Confluence page with the layout information.
    """

    @abstractmethod
    def render_toc(self, has_toc):
        pass

    @abstractmethod
    def render_authors(self, authors):
        pass

    @abstractmethod
    def render_page(self, content, toc, authors):
        pass

    def render(self, content, authors, has_toc):
        """ Generates the final HTML of the layout of the Confluence page
            with the Content, Author(s) and the Table of Contents embedded in
            the page layout.

            Arguments:
                content {str}  -- The content of the document in xhtml format
                authors {list} -- The list of authors
                has_toc {bool} -- A flag to denote whether the page has a ToC (or not)

            Returns:
                {str} -- The final xhtml of the Confluence page
        """
        toc = self.render_toc(has_toc)
        contributors = self.render_authors(authors)
        return self.render_page(content, contributors, toc)


class LeftSidebarPage(AbstractConfluencePage):
    """
        A concretion of the AbstractPage class for a two-column Confluence
        page. This layout shows the ToC in the left sidebar, and the authors
        and the main content on the right.

        The layout looks like this:

        ------------------------------------------
        |             |         Authors          |
        |     ToC     |--------------------------|
        | (20% width) |                          |
        |             |         Content          |
        |             |      (900px width)       |
        |             |                          |
        ------------------------------------------
    """

    def __init__(self, sidebar_width='20%', content_width='900px'):

        self.__sidebar_width = sidebar_width
        self.__content_width = content_width

        self.__layout_template = textwrap.dedent('''
            <ac:layout>
                <ac:layout-section ac:type="two_left_sidebar">
                {sidebar}
                {main_content}
                </ac:layout-section>
            </ac:layout>
        ''')

    def render_toc(self, has_toc):

        if not has_toc:
            return '<ac:layout-cell></ac:layout-cell>'

        return textwrap.dedent('''
            <ac:layout-cell>
                <h1>Table of Contents</h1>
                <p><ac:structured-macro ac:name="toc" ac:schema-version="1">
                    <ac:parameter ac:name="exclude">^(Authors|Table of Contents)$</ac:parameter>
                </ac:structured-macro></p>
            </ac:layout-cell>
        ''')

    def render_authors(self, authors):
        author_template = textwrap.dedent('''
            <td rowspan="2">
                <div class="content-wrapper"><p>
                    <ac:link>
                        <ri:user ri:userkey="{user_key}" />
                    </ac:link>
                    <br />
                    <span>{designation}</span>
                </p></div>
            </td>
        ''')

        col_group_template = '<col style="width: 180px;" />'

        contributors = ''
        col_group = ''
        for i, auth_tuple in enumerate(authors):
            contributors += author_template.format(user_key=auth_tuple[0],
                                                   designation=auth_tuple[1])
            col_group += col_group_template

        return textwrap.dedent('''
            <table class="relative-table">
                <colgroup>
                    {col_group}
                </colgroup>
                <tbody>
                <tr>
                    <th colspan="{cols}">
                    <h2>Authors</h2></th>
                </tr>
                <tr>
                    {authors_list}
                </tr>
                </tbody>
            </table>
        ''').format(col_group=col_group,
                    cols = len(authors),
                    authors_list=contributors)

    def render_page(self, content, authors, toc):

        main_content = textwrap.dedent('''
            <ac:layout-cell>
                <p class="auto-cursor-target"><br /></p>
                <ac:structured-macro ac:name="column" ac:schema-version="1">
                    <ac:parameter ac:name="width">{width}</ac:parameter>
                    <ac:rich-text-body>
                        {authors}
                        <p class="auto-cursor-target"><br /></p>
                        <p class="auto-cursor-target"><br /></p>
                        {content}
                    </ac:rich-text-body>
                </ac:structured-macro>
            </ac:layout-cell>
        ''').format(width=self.__content_width,
                    authors=authors,
                    content=content)

        return self.__layout_template.format(sidebar=toc,
                                             main_content=main_content)
    
