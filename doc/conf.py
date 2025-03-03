"""
:copyright: Copyright Sphinx Confluence Builder Contributors (AUTHORS)
:license: BSD-2-Clause (LICENSE)
"""

from docutils import nodes
from sphinx.transforms.post_transforms import SphinxPostTransform
import sphinxcontrib.confluencebuilder

project = 'Sphinx Confluence Builder'
copyright = '2023 Sphinx Confluence Builder Contributors'
author = 'Sphinx Confluence Builder Contributors'
version = sphinxcontrib.confluencebuilder.__version__
release = sphinxcontrib.confluencebuilder.__version__

supported_confluence_ver = '7.12+'
supported_python_ver = '3.7+'
supported_sphinx_ver = '5.0+'

root_doc = 'contents'

# reStructuredText string included at the end of every source
rst_epilog = """
.. |supported_confluence_ver| replace:: {}
.. |supported_python_ver| replace:: {}
.. |supported_sphinx_ver| replace:: {}
""".format(supported_confluence_ver, supported_python_ver, supported_sphinx_ver)

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = [
    '_build',
    '.DS_Store',
    'Thumbs.db',
]

# -- Options for HTML output ----------------------------------------------

html_theme = 'sphinx13b'
html_theme_path = ['_themes']
templates_path = ['_templates']

html_static_path = ['_static']

html_additional_pages = {
    'index': 'index.html',
}

html_sidebars = {
    'index': [
        'indexsidebar.html',
        'searchbox.html',
        'ethical-ads.html',
    ],
}

html_context = {
    'supported_confluence_ver': supported_confluence_ver,
    'supported_python_ver': supported_python_ver,
    'supported_sphinx_ver': supported_sphinx_ver,
}

# -- Options for Latex output --------------------------------------------

latex_elements = {
    # remove empty pages
    'extraclassoptions': 'openany,oneside',
    # custom title
    'maketitle': r'''
\begin{titlepage}
    \vspace*{\stretch{1.2}}
    \sphinxlogo
    \vspace*{\stretch{1.0}}
    \begin{center}
        \large Provided by Sphinx Confluence Builder Contributors
        \par
        \DTMsetdatestyle{iso}
        \DTMtoday
        \par
        ''' + release + r'''
    \end{center}
    \vspace*{\stretch{1.0}}
\end{titlepage}
    ''',
    # iso datetime support
    # disable hyphenatation
    # disable justified text
    'preamble': r'''
        \usepackage{datetime2}
        \usepackage[none]{hyphenat}
        \usepackage[document]{ragged2e}
    ''',
}

latex_logo = '_static/logo.png'

# -- Application hook -----------------------------------------------------


class DocumentationPostTransform(SphinxPostTransform):
    default_priority = 400

    def run(self, **kwargs):
        for node in self.document.traverse(nodes.reference):
            # tag references with `literal` child with a `literal-link` class
            # (to suppress hover styling)
            if isinstance(next(iter(node.children), None), nodes.literal):
                classes = node.get('classes', [])
                classes.append('literal-link')


def setup(app):
    app.require_sphinx('6.0')

    app.add_js_file('jquery-3.6.3.min.js')
    app.add_js_file('version-alert.js')

    # custom directives/roles for documentation
    app.add_object_type('builderval', 'builderval', objname='builders',
        indextemplate='pair: %s; builder')
    app.add_object_type('confval', 'confval', objname='configuration value',
        indextemplate='pair: %s; configuration value')

    # register post-transformation hook for additional tweaks
    app.add_post_transform(DocumentationPostTransform)
