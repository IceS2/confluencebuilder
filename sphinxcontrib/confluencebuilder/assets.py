# SPDX-License-Identifier: BSD-2-Clause
# Copyright Sphinx Confluence Builder Contributors (AUTHORS)

from docutils import nodes
from sphinx import addnodes
from sphinx.util.osutil import canon_path
from sphinx.util.images import guess_mimetype
from sphinxcontrib.confluencebuilder.compat import docutils_findall as findall
from sphinxcontrib.confluencebuilder.logger import ConfluenceLogger as logger
from sphinxcontrib.confluencebuilder.std.confluence import INVALID_CHARS
from sphinxcontrib.confluencebuilder.std.confluence import SUPPORTED_IMAGE_TYPES
from sphinxcontrib.confluencebuilder.util import ConfluenceUtil
from sphinxcontrib.confluencebuilder.util import find_env_abspath
import os

# default content type to use if a type cannot be detected for an asset
DEFAULT_CONTENT_TYPE = 'application/octet-stream'


class ConfluenceAsset:
    """
    a confluence asset

    Holds metadata for an asset (image or file).

    Args:
        key: the asset key
        path: the absolute path to the asset
        type_: the content type of the asset
        hash_: the hash of the asset
    """
    def __init__(self, key, path, type_, hash_):
        self.docnames = set()
        self.path = path
        self.hash = hash_
        self.key = key
        self.type = type_


class ConfluenceAssetManager:
    """
    a confluence assets tracker

    The asset manager is used to track detect assets to be referenced to and
    published (if configured) to a Confluence instance. The manager has the
    ability to track locations of assets, detect duplicate uses of assets (when
    references and/or duplicate physical files) and more. Typically, the buidler
    will scan the list of documents to be processed for assets. When the
    translator is running, it will refer to the asset manager to know where an
    asset will be published (so the translator knows how to reference the
    asset). Finally, during the publishing phase, the list of tracked assets can
    be published to the respective publish points.

    Args:
        config: the active configuration
        env: the build environment
        outdir: configured output directory (where assets may be stored)
    """
    def __init__(self, config, env, outdir):
        self.assets = []
        self.env = env
        self.force_standalone = config.confluence_asset_force_standalone
        self.hash2asset = {}
        self.keys = set()
        self.outdir = outdir
        self.path2asset = {}
        self.root_doc = config.root_doc

    def add(self, path, docname):
        """
        add a custom attachment

        This method can be used to register a custom attachment to be added to
        a provided page. This call is for special cases when registering a
        file to upload outside a document's actual content (e.g. an
        intersphinx database).

        Args:
            path: the path of the fiel
            docname: the document's name to attach to

        Returns:
            the key, document name and path
        """
        logger.verbose('adding manual attachment: %s' % path)
        abspath = find_env_abspath(self.env, self.outdir, path)
        return self._handle_entry(abspath, docname, standalone=True)

    def build(self):
        """
        build a list of all assets tracked by the manager

        Returns a list of tuples for all asset entries tracked by this manager.
        A tuple entry will contain the following:

         - The key (or name) of the asset.
         - The absolute path of the asset on the system.
         - The content-type value of the asset.
         - The hash value of the asset.
         - The name of the document this asset should be published to.

        Returns:
            the list of assets
        """
        data = []
        for asset in self.assets:
            if self.force_standalone:
                for docname in asset.docnames:
                    entry = (asset.key, asset.path, asset.type, asset.hash,
                        docname)
                    data.append(entry)
            else:
                if len(asset.docnames) > 1:
                    entry = (asset.key, asset.path, asset.type, asset.hash,
                        self.root_doc)
                else:
                    entry = (asset.key, asset.path, asset.type, asset.hash,
                        next(iter(asset.docnames)))
                data.append(entry)
        return data

    def fetch(self, node, docname=None):
        """
        return key and target document name for provided asset

        When given a asset, cached information will return the name of the
        target document this asset will be published to. In the event an asset
        exists on a single page, the name of that respective page will be
        returned; however, if the asset is found on multiple pages, the root
        document name will be returned instead.

        Args:
            node: the node to interpret
            docname (optional): force the document name for this asset

        Returns:
            the key, document name and path
        """
        key = None

        path = self._interpret_asset_path(node)
        if path:
            asset = self.path2asset.get(path, None)

            if asset:
                key = asset.key

                if not docname:
                    if self.force_standalone:
                        docname = canon_path(
                            self.env.path2doc(node.document['source']))
                        assert docname in asset.docnames
                    else:
                        if len(asset.docnames) > 1:
                            docname = self.root_doc
                        else:
                            docname = next(iter(asset.docnames))

        if not key:
            docname = None
            path = None

        return key, docname, path

    def process(self, docnames):
        """
        process a list of document for assets

        Given a list of document names, this method will search each document's
        doctree for supported assets which could be published. Asset information
        is tracked in this manager and other helper methods can be used to pull
        asset information when needed.

        Args:
            docnames: the document names to search
        """
        for docname in docnames:
            doctree = self.env.get_doctree(docname)
            self.process_document(doctree, docname)

    def process_document(self, doctree, docname, standalone=False):
        """
        process a document for assets

        This method will search each the provided document's doctree for
        supported assets which could be published. Asset information is tracked
        in this manager and other helper methods can be used to pull asset
        information when needed.

        Args:
            doctree: the document's tree
            docname: the document's name
            standalone (optional): ignore hash mappings (defaults to False)
        """
        image_nodes = findall(doctree, nodes.image)
        for node in image_nodes:
            self.process_image_node(node, docname, standalone)

        file_nodes = findall(doctree, addnodes.download_reference)
        for node in file_nodes:
            self.process_file_node(node, docname, standalone)

    def process_file_node(self, node, docname, standalone=False):
        """
        process an file node

        This method will process an file node for asset tracking. Asset
        information is tracked in this manager and other helper methods can be
        used to pull asset information when needed.

        Args:
            node: the file node
            docname: the document's name
            standalone (optional): ignore hash mappings (defaults to False)

        Returns:
            the key, document name and path
        """

        target = node['reftarget']
        if target.find('://') == -1:
            logger.verbose('process file node: %s' % target)
            path = self._interpret_asset_path(node)
            if path:
                return self._handle_entry(path, docname, standalone)

        return None, None, None

    def process_image_node(self, node, docname, standalone=False):
        """
        process an image node

        This method will process an image node for asset tracking. Asset
        information is tracked in this manager and other helper methods can be
        used to pull asset information when needed.

        Args:
            node: the image node
            docname: the document's name
            standalone (optional): ignore hash mappings (defaults to False)

        Returns:
            the key, document name and path
        """

        uri = str(node['uri'])
        if not uri.startswith('data:') and uri.find('://') == -1:
            logger.verbose('process image node: %s' % uri)
            path = self._interpret_asset_path(node)
            if path:
                return self._handle_entry(path, docname, standalone)

        return None, None, None

    def _handle_entry(self, path, docname, standalone=False):
        """
        handle an asset entry

        When an asset is detected in a document, the information about the asset
        is tracked in this manager. When an asset is detected, there are
        considerations to be made. If an asset path has already been registered
        (e.g. an asset used twice), only a single asset entry will be created.
        If an asset matches the hash of another asset, another entry is *not
        created (i.e. a documentation set has duplicate assets; *with the
        exception of when ``standalone`` is set to ``True``). In all cases where
        an asset is detected, the asset reference is updated to track which
        document the asset belongs to.

        Args:
            path: the absolute path to the asset
            docname: the document name this asset was found in
            standalone (optional): ignore hash mappings (defaults to False)
        """

        if path not in self.path2asset:
            hash_ = ConfluenceUtil.hash_asset(path)
            type_ = guess_mimetype(path, default=DEFAULT_CONTENT_TYPE)
        else:
            hash_ = self.path2asset[path].hash
            type_ = self.path2asset[path].type

        asset = self.path2asset.get(path, None)
        if not asset:
            hash_exists = hash_ in self.hash2asset
            if not hash_exists or standalone:
                # no asset entry and no hash entry (or standalone); new asset
                key = os.path.basename(path)

                # Confluence does not allow attachments with select characters.
                # Filter out the asset name to a compatible key value.
                for rep in INVALID_CHARS:
                    key = key.replace(rep, '_')

                filename, file_ext = os.path.splitext(key)
                idx = 1
                while key in self.keys:
                    idx += 1
                    key = f'{filename}_{idx}{file_ext}'
                self.keys.add(key)

                asset = ConfluenceAsset(key, path, type_, hash_)
                self.assets.append(asset)
                self.path2asset[path] = asset
                if not hash_exists:
                    self.hash2asset[hash_] = asset
            else:
                # duplicate asset detected; build an asset alias
                asset = self.hash2asset[hash_]
                self.path2asset[path] = asset
        else:
            assert (self.hash2asset[asset.hash] == asset)

        # track (if not already) that this document uses this asset
        asset.docnames.add(docname)

        return asset.key, docname, asset.path

    def _interpret_asset_path(self, node):
        """
        find an absolute path for a target assert

        Returns the absolute path to an assert. For unsupported asset types,
        this method will return ``None`` values. This method should not be
        invoked on external assets (i.e. URLs).

        Args:
            node: the node to parse

        Returns:
            the absolute path
        """
        path = None
        if isinstance(node, nodes.image):
            # uri's will be relative to documentation root.
            path = str(node['uri'])
        elif isinstance(node, addnodes.download_reference):
            # reftarget will be a reference to the asset with respect to the
            # document (refdoc) holding this reference. Use reftarget and refdoc
            # to find a proper path.
            docdir = os.path.dirname(node['refdoc'])
            path = os.path.join(docdir, node['reftarget'])

        abspath = find_env_abspath(self.env, self.outdir, path)

        if not abspath:
            logger.verbose('failed to find path: %s' % path)

        return abspath


class ConfluenceSupportedImages:
    def __init__(self):
        """
        confluence support images

        Defines an iterable instance of mime types of supported images types on
        a Confluence instance. While a typical list can suffice to bind to a
        builder's `supported_image_types` definition, this instance provides the
        ability to register additional mime types (via configuration) if
        supported by a Confluence instance. This provides flexibility for newer
        Confluence versions as well as custom instances which support their own
        custom image types.
        """
        self._mime_types = list(SUPPORTED_IMAGE_TYPES)

    def __getitem__(self, key):
        """
        iterable evaulation of self[key]

        Args:
            key: the key to evaluate

        Returns:
            the value for this key
        """
        return self._mime_types[key]

    def register(self, type_):
        """
        register a mime type to support

        Register an additional mime type to support over the internal list of
        supported types. This call has no effect if the type is already
        registered.

        Args:
            type_: the mime type to add
        """
        if type_ not in self._mime_types:
            self._mime_types.append(type_)
