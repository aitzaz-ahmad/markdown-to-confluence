import os
from convert import parse

import logging
logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
log = logging.getLogger(__name__)

DOCS_ROOT = 'content'
ASSETS_DIR = 'images'

def normalize_path(file_path):
    #make directory separatores consistent
    path = file_path.replace('/', '\\')

    #strip all leading '..\\' sequences in relative paths
    while path.startswith('..\\'):
        path = path[len('..\\'):]

    return path

class MarkdownFile:

    def __init__(self, file_name, dir_name, abs_path):
        self.path = os.path.join(abs_path, file_name)
        self.slug = self.__get_slug__(dir_name, file_name)

        front_matter, markdown = parse(self.path)
        self.title = front_matter['title']

    def __get_slug__(self, file_name, parent_dir):
        name, _ = os.path.splitext(file_name)
        slug = '{}_{}'.format(parent_dir, file_name)
        slug = slug.replace('-', '_')
        return slug

class Directory:

    def __init__(self, abs_path):
        self.__path = abs_path
        self.__md_files = dict()

    def __bool__(self):
        return len(self.__md_files) > 0

    def find_file(self, file_name):
        for path in self.__md_files.keys():
            if file_name in path:
                return self.__md_files[path]

        return None

    def add_file(self, md_file):
        assert isinstance(md_file, MarkdownFile), 'Expects MarkdownFile type object as input'
        self.__md_files[md_file.path] = md_file

class MarkdownPages:

    __MARKDOWN_EXT__ = '.md'
    __MISSING_SUBDIR__ = '"{repo}" is missing the "{docs}" subdirectory'

    def __init__(self, repo_path):

        assert repo_path is not None, 'repo_path cannot be None'
        assert repo_path != '', 'repo_path must not be emptpy'
        assert os.path.exists(repo_path), '"{}" does not exist'.format(repo_path)

        docs_root = os.path.join(repo_path, DOCS_ROOT)
        assert os.path.exists(docs_root), __MISSING_SUBDIR__.format(
                                                            self.__repo_path__,
                                                            DOCS_ROOT)
        self.__md_docs_tree = {}
        self.__scan_repository__(os.path.abspath(docs_root))

    def __scan_repository__(self, docs_path):

        dir_tree = os.walk(docs_path)
        for dir_path, sub_dirs, files in dir_tree:
            #skip assets: they only contain attachments
            _, dir_name = os.path.split(dir_path)
            if dir_name == ASSETS_DIR:
                continue

            directory = Directory(dir_path)
            for file in files:
                #skip all files that aren't markdown docs
                _, ext = os.path.splitext(file)
                if ext != self.__MARKDOWN_EXT__:
                    continue

                try:
                    md_file = MarkdownFile(file, dir_name, dir_path)
                except Exception as e:
                    log.error(
                        'Unable to generate metadata for {}. Normally not a problem, but here\'s the error we received: {}'
                        .format(os.path.join(dir_path, file), e)
                        )
                else:
                    directory.add_file(md_file)

            #store non-empty directories only
            if directory:
                self.__md_docs_tree[dir_path] = directory

    def get_title(self, md_doc):

        doc_name = normalize_path(md_doc)
        for dir in self.__md_docs_tree.values():
            matched_file = dir.find_file(doc_name)
            if matched_file:
                log.info('found the title of {}'.format(md_doc))
                return matched_file.title;

        log.info('no metadata available for {}'.format(md_doc))
        return ''
